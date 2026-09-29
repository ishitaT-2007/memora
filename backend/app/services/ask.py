from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Account, Commitment, Escalation, Incident, Memory, SourceRecord, Stakeholder
from app.services.hindsight_adapter import hindsight, _tokens

STOPWORDS = {
    "what",
    "which",
    "when",
    "where",
    "who",
    "whom",
    "this",
    "that",
    "their",
    "there",
    "have",
    "has",
    "had",
    "does",
    "did",
    "the",
    "and",
    "for",
    "our",
    "are",
    "was",
    "were",
    "with",
    "from",
    "about",
    "should",
    "would",
    "could",
    "into",
}

MAIL_MARKERS = (
    "mail",
    "email",
    "e-mail",
    "message",
    "telling",
    "saying",
    "wrote",
    "subject",
    "pasted",
    "escalation note",
    "this note",
)


def is_mail_question(query: str) -> bool:
    lowered = query.lower()
    return any(marker in lowered for marker in MAIL_MARKERS)


def ask_account(
    db: Session,
    *,
    account_id: str,
    query: str,
    current_mail: str = "",
) -> dict[str, Any]:
    account = db.get(Account, account_id)
    if not account:
        return {"answer": "Account not found.", "unknown": True, "citations": [], "hits": []}

    q = query.strip()
    if is_mail_question(q):
        return _answer_from_mail(db, account=account, query=q, current_mail=current_mail)

    q_tokens = {token for token in _tokens(q) if token not in STOPWORDS}
    hits: list[dict[str, Any]] = []

    hits.append(
        _hit(
            f"acc_{account.id}",
            "account",
            f"{account.name} is a {account.segment} account at ${account.arr:,} ARR, timezone {account.timezone}, status {account.status}.",
            account.id,
            q_tokens,
            boost=0.2 if {"arr", "size", "company", "account", "segment"} & q_tokens else 0,
        )
    )

    for row in db.query(Stakeholder).filter(Stakeholder.account_id == account_id).all():
        text = f"{row.name} is {row.role} ({row.influence}). {row.preferences}"
        boost = 0.35 if row.name.lower().split()[0] in q.lower() else 0
        hits.append(_hit(row.id, "stakeholder", text, row.id, q_tokens, boost=boost))

    for row in db.query(Commitment).filter(Commitment.account_id == account_id).all():
        text = f"Commitment ({row.status}, owner {row.owner}, due {row.due_date}): {row.description}"
        boost = 0.3 if any(word in q.lower() for word in ("promise", "promised", "commit", "sso", "update")) else 0
        hits.append(_hit(row.id, "commitment", text, row.source_record_id or row.id, q_tokens, boost=boost))

    for row in db.query(Incident).filter(Incident.account_id == account_id).all():
        text = f"{row.severity} incident: {row.summary} Impact: {row.impact}"
        boost = 0.25 if any(word in q.lower() for word in ("incident", "outage", "p1", "quarter")) else 0
        hits.append(_hit(row.id, "incident", text, row.id, q_tokens, boost=boost))

    memories = (
        db.query(Memory)
        .filter(Memory.account_id == account_id, Memory.superseded_by.is_(None))
        .all()
    )
    recalled_ids = {item.id for item in hindsight.recall(account_id=account_id, query=q, include_comparable=False)}
    for row in memories:
        boost = 0.2 if row.id in recalled_ids else 0
        if row.memory_type in {"landmine", "commitment", "team_correction"} and any(
            word in q.lower() for word in ("credit", "discount", "sso", "promise", "avoid", "don't", "dont")
        ):
            boost += 0.25
        hits.append(_hit(row.id, row.memory_type, row.text, row.source_ref or row.id, q_tokens, boost=boost))

    for row in db.query(SourceRecord).filter(SourceRecord.account_id == account_id).all():
        text = f"{row.title}: {row.body}"
        hits.append(_hit(row.id, row.type, text, row.id, q_tokens, boost=0.05))

    ranked = [item for item in hits if item["score"] >= 0.12 and item["overlap"] > 0]
    ranked.sort(key=lambda item: item["score"], reverse=True)
    top = ranked[:5]

    if not top:
        return {
            "account": {"id": account.id, "name": account.name},
            "query": q,
            "answer": (
                f"I do not have that in {account.name}'s approved memory, so I will not guess. "
                "Ask about people, ARR, promises, incidents, SSO, credits, or what this mail says."
            ),
            "unknown": True,
            "citations": [],
            "hits": [],
        }

    lines = [f"From {account.name} memory (synthetic demo data):"]
    citations = []
    for item in top:
        lines.append(f"- {item['text']}")
        if item["source_id"] and item["source_id"] not in citations:
            citations.append(item["source_id"])

    return {
        "account": {"id": account.id, "name": account.name},
        "query": q,
        "answer": "\n".join(lines),
        "unknown": False,
        "citations": citations,
        "hits": [{"id": item["id"], "type": item["type"], "text": item["text"], "score": item["score"]} for item in top],
    }


def _answer_from_mail(db: Session, *, account: Account, query: str, current_mail: str) -> dict[str, Any]:
    mail = (current_mail or "").strip()
    source_id = "current_mail"
    if not mail:
        latest = (
            db.query(Escalation)
            .filter(Escalation.account_id == account.id)
            .order_by(Escalation.created_at.desc())
            .first()
        )
        if latest and (latest.input_text or "").strip() and not latest.input_text.startswith("[redacted"):
            mail = latest.input_text.strip()
            source_id = latest.id
    if not mail:
        return {
            "account": {"id": account.id, "name": account.name},
            "query": query,
            "answer": (
                "I can only summarize the mail that is pasted on the left. "
                "Paste Priya’s escalation email, then ask again. "
                "I will not substitute older CRM notes for this question."
            ),
            "unknown": True,
            "citations": [],
            "hits": [],
        }

    bullets = _mail_points(mail)
    answer = (
        f"In the current {account.name} escalation mail, this is what is being said "
        f"(this is the live pasted message, not older account memory):\n"
        + "\n".join(f"- {point}" for point in bullets)
        + "\n\nQuoted mail:\n"
        + mail
    )
    return {
        "account": {"id": account.id, "name": account.name},
        "query": query,
        "answer": answer,
        "unknown": False,
        "citations": [source_id],
        "hits": [{"id": source_id, "type": "current_mail", "text": mail, "score": 1.0}],
    }


def _mail_points(mail: str) -> list[str]:
    lowered = mail.lower()
    points: list[str] = []
    sender = _first_line_value(mail, "from:")
    subject = _first_line_value(mail, "subject:")
    if sender:
        points.append(f"From: {sender}")
    if subject:
        points.append(f"Subject: {subject}")
    if "checkout api" in lowered:
        points.append("Checkout API is failing (about 26 minutes in the demo mail).")
    if "third outage" in lowered:
        points.append("This is described as the third outage this quarter.")
    if "we are done" in lowered:
        points.append("Priya says they are done — this is an explicit churn threat.")
    if "owns this" in lowered or "not another polite email" in lowered:
        points.append("She wants a named owner, not another polite email.")
    if not points:
        points.append(mail[:400].strip())
    return points


def _first_line_value(mail: str, prefix: str) -> str:
    for line in mail.splitlines():
        if line.lower().startswith(prefix):
            return line.split(":", 1)[-1].strip()
    return ""


def _hit(item_id: str, item_type: str, text: str, source_id: str, query_tokens: set[str], boost: float = 0) -> dict[str, Any]:
    tokens = _tokens(text)
    overlap_count = len(query_tokens & tokens)
    overlap = overlap_count / max(1, len(query_tokens))
    score = round(overlap + boost, 3)
    return {
        "id": item_id,
        "type": item_type,
        "text": text,
        "source_id": source_id,
        "score": score,
        "overlap": overlap_count,
    }

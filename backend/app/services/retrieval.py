from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import Account, Commitment, Incident, Memory, Outcome, SourceRecord, Stakeholder
from app.services.hindsight_adapter import RecalledMemory, hindsight


INJECTION_MARKERS = ("ignore prior", "ignore all instructions", "system:", "you are now", "disregard previous")


def classify_event(text: str, severity: str) -> dict[str, Any]:
    lowered = text.lower()
    issue = "reliability"
    if "invoice" in lowered or "payment" in lowered:
        issue = "billing"
    elif "sso" in lowered or "login" in lowered:
        issue = "identity"
    sentiment = "angry" if any(word in lowered for word in ("done", "unacceptable", "lawsuit", "churn")) else "frustrated"
    missing = []
    if "inc-" not in lowered and "incident" not in lowered:
        missing.append("incident_id")
    return {
        "severity": severity,
        "issue_type": issue,
        "sentiment": sentiment,
        "prompt_injection_suspected": any(marker in lowered for marker in INJECTION_MARKERS),
        "missing_fields": missing,
    }


def retrieve_context(
    db: Session,
    *,
    account_id: str,
    query: str,
    memory_mode: str,
) -> tuple[dict[str, Any], bool, str | None]:
    account = db.get(Account, account_id)
    memory_limited = memory_mode == "limited"
    hindsight_error = None

    recalled: list[RecalledMemory] = []
    if not memory_limited:
        recalled = hindsight.recall(account_id=account_id, query=query, include_comparable=True)
        if hindsight.mode == "hindsight" and not recalled and hindsight.last_error:
            memory_limited = True
            hindsight_error = hindsight.last_error

    local_memories = (
        db.query(Memory)
        .filter(Memory.status.in_(("verified", "policy", "preference")))
        .filter(Memory.superseded_by.is_(None))
        .all()
    )
    allowed = []
    for memory in local_memories:
        if memory.account_id == account_id:
            allowed.append(memory)
        elif memory.scope == "comparable":
            allowed.append(memory)
        elif memory.scope == "team":
            allowed.append(memory)

    if not recalled and not memory_limited:
        recalled = [
            RecalledMemory(
                id=item.id,
                text=item.text,
                memory_type=item.memory_type,
                account_id=item.account_id,
                source_ref=item.source_ref,
                score=0.5,
                status=item.status,
                scope=item.scope,
            )
            for item in allowed
            if _relevant(query, item.text, item.memory_type, item.account_id == account_id)
        ]

    recalled_ids = {item.id for item in recalled}
    for memory in allowed:
        if memory.id in recalled_ids:
            continue
        if memory.account_id == account_id or memory.memory_type in {"outcome_playbook", "team_correction", "policy"}:
            if _relevant(query, memory.text, memory.memory_type, memory.account_id == account_id):
                recalled.append(
                    RecalledMemory(
                        id=memory.id,
                        text=memory.text,
                        memory_type=memory.memory_type,
                        account_id=memory.account_id,
                        source_ref=memory.source_ref,
                        score=0.42,
                        status=memory.status,
                        scope=memory.scope,
                    )
                )

    source_ids = {item.source_ref for item in recalled if item.source_ref}
    sources = db.query(SourceRecord).filter(SourceRecord.id.in_(source_ids)).all() if source_ids else []
    commitments = db.query(Commitment).filter(Commitment.account_id == account_id).all()
    incidents = db.query(Incident).filter(Incident.account_id == account_id).all()
    stakeholders = db.query(Stakeholder).filter(Stakeholder.account_id == account_id).all()
    outcomes = db.query(Outcome).filter(Outcome.account_id != account_id).all() if not memory_limited else []

    pack = {
        "account": {
            "id": account.id if account else account_id,
            "name": account.name if account else "",
            "arr": account.arr if account else 0,
            "segment": account.segment if account else "",
            "status": account.status if account else "",
        },
        "classification": classify_event(query, "P1"),
        "stakeholders": [
            {"id": row.id, "name": row.name, "role": row.role, "influence": row.influence, "preferences": row.preferences}
            for row in stakeholders
        ],
        "commitments": [
            {
                "id": row.id,
                "description": row.description,
                "status": row.status,
                "due_date": row.due_date,
                "source_record_id": row.source_record_id,
            }
            for row in commitments
        ],
        "incidents": [
            {"id": row.id, "severity": row.severity, "summary": row.summary, "impact": row.impact}
            for row in incidents
        ],
        "comparable_outcomes": [
            {
                "id": row.id,
                "account_id": row.account_id,
                "situation": row.situation,
                "actions_taken": row.actions_taken,
                "outcome": row.outcome,
                "evidence_ref": row.evidence_ref,
            }
            for row in outcomes
        ],
        "memories": [
            {
                "id": item.id,
                "text": item.text,
                "memory_type": item.memory_type,
                "account_id": item.account_id,
                "source_ref": item.source_ref,
                "score": item.score,
                "status": item.status,
                "scope": item.scope,
            }
            for item in recalled[:16]
        ],
        "sources": [
            {
                "id": row.id,
                "type": row.type,
                "title": row.title,
                "body": row.body,
                "source_ref": row.source_ref,
                "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
            }
            for row in sources
        ],
        "valid_source_ids": sorted(
            {row.id for row in sources}
            | {item.id for item in recalled}
            | {item.source_ref for item in recalled if item.source_ref}
            | {row.id for row in commitments}
            | {row.id for row in incidents}
        ),
    }
    if memory_limited:
        pack["memories"] = []
        pack["comparable_outcomes"] = []
        pack["valid_source_ids"] = []
    return pack, memory_limited, hindsight_error


def _relevant(query: str, text: str, memory_type: str, same_account: bool) -> bool:
    if same_account and memory_type in {"landmine", "commitment", "stakeholder", "team_correction", "account_profile", "incident_history"}:
        return True
    if memory_type == "outcome_playbook":
        return True
    q = set(re.findall(r"[a-z0-9]+", query.lower()))
    t = set(re.findall(r"[a-z0-9]+", text.lower()))
    return len(q & t) >= 2

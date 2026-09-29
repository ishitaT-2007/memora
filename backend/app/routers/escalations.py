from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import get_settings
from app.data.corpus import DEMO_ESCALATION
from app.db import get_db
from app.errors import AccrueError
from app.models import Account, AnalysisRun, Correction, Escalation, Memory, SourceRecord, User
from app.schemas import AnalyzeRequest, CorrectionConfirmRequest, CorrectionPreviewRequest
from app.services.access import assert_account_access
from app.services.audit import write_audit
from app.services.hindsight_adapter import hindsight
from app.services.orchestrator import analyze_escalation
from app.services.ratelimit import SlidingWindowLimiter

router = APIRouter(tags=["escalations"])
settings = get_settings()
limiter = SlidingWindowLimiter(settings.analyze_rate_limit_per_minute)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


@router.post("/api/escalations/analyze")
def analyze(
    payload: AnalyzeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    limiter.hit(user.id)
    account = db.get(Account, payload.account_id)
    if not account:
        raise AccrueError("ACCOUNT_NOT_FOUND", "Select a valid account. Accrue will not guess the account.", 404)
    assert_account_access(db, user, payload.account_id)
    if len(payload.escalation_text.strip()) < 20:
        raise AccrueError("VALIDATION_ERROR", "Paste a fuller escalation note or email.", 422)
    if len(payload.escalation_text) > settings.max_escalation_chars:
        raise AccrueError("PAYLOAD_TOO_LARGE", f"Escalation text exceeds {settings.max_escalation_chars} characters.", 413)

    escalation, run, output, pack = analyze_escalation(
        db, user_id=user.id, payload=payload, request_id=_request_id(request)
    )
    return {
        "request_id": _request_id(request),
        "escalation_id": escalation.id,
        "analysis_id": run.id,
        "latency_ms": run.latency_ms,
        "model_version": run.model_version,
        "account": pack.get("account"),
        "classification": pack.get("classification"),
        "output": output.model_dump(),
        "sources": pack.get("sources"),
        "review_state": "human_review_required",
        "demo_hint": DEMO_ESCALATION if payload.account_id == "acc_acme" else None,
    }


@router.get("/api/escalations/{escalation_id}/export")
def export_escalation(
    escalation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    escalation = db.get(Escalation, escalation_id)
    if not escalation:
        raise AccrueError("NOT_FOUND", "Escalation not found.", 404)
    assert_account_access(db, user, escalation.account_id)
    run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.escalation_id == escalation_id)
        .order_by(AnalysisRun.created_at.desc())
        .first()
    )
    if not run:
        raise AccrueError("NOT_FOUND", "No analysis to export.", 404)
    output = json.loads(run.output_json)
    lines = ["ACCRUE BRIEF (synthetic demo data unless otherwise documented)", ""]
    lines.extend(f"- {item}" for item in output.get("brief") or [])
    lines += ["", "DO"]
    lines.extend(f"- {item.get('action')}" for item in output.get("do") or [])
    lines += ["", "DON'T"]
    lines.extend(f"- {item.get('action')}" for item in output.get("dont") or [])
    lines += ["", "DRAFT", output.get("reply_draft") or ""]
    return {"filename": f"accrue-{escalation_id[:8]}.txt", "text": "\n".join(lines)}


@router.get("/api/escalations/{escalation_id}")
def get_escalation(
    escalation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    escalation = db.get(Escalation, escalation_id)
    if not escalation:
        raise AccrueError("NOT_FOUND", "Escalation not found.", 404)
    assert_account_access(db, user, escalation.account_id)
    run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.escalation_id == escalation_id)
        .order_by(AnalysisRun.created_at.desc())
        .first()
    )
    output = json.loads(run.output_json) if run else None
    return {
        "escalation": {
            "id": escalation.id,
            "account_id": escalation.account_id,
            "severity": escalation.severity,
            "created_at": escalation.created_at.isoformat(),
            "memory_mode": escalation.memory_mode,
        },
        "analysis": {
            "id": run.id if run else None,
            "model_version": run.model_version if run else None,
            "latency_ms": run.latency_ms if run else None,
            "output": output,
        },
    }


@router.post("/api/escalations/{escalation_id}/corrections/preview")
def preview_correction(
    escalation_id: str,
    payload: CorrectionPreviewRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    escalation = db.get(Escalation, escalation_id)
    if not escalation:
        raise AccrueError("NOT_FOUND", "Escalation not found.", 404)
    assert_account_access(db, user, escalation.account_id)
    if payload.scope == "team" and user.role != "admin":
        raise AccrueError("TEAM_SCOPE_FORBIDDEN", "Team-wide rules require admin approval.", 403)

    correction = Correction(
        id=f"cor_{uuid4()}",
        escalation_id=escalation_id,
        proposed_memory=payload.proposed_memory.strip(),
        memory_type=payload.memory_type,
        scope=payload.scope,
        status="preview",
        reviewer_id=user.id,
    )
    db.add(correction)
    write_audit(
        db,
        actor_id=user.id,
        action="correction.preview",
        object_type="correction",
        object_id=correction.id,
        request_id=_request_id(request),
        detail=payload.proposed_memory.strip()[:500],
    )
    db.commit()
    return {
        "request_id": _request_id(request),
        "correction_id": correction.id,
        "status": "preview",
        "writes_memory": False,
        "preview": {
            "account_id": escalation.account_id,
            "memory_type": payload.memory_type,
            "scope": payload.scope,
            "text": payload.proposed_memory.strip(),
            "note": "Nothing is saved to durable memory until you confirm.",
        },
    }


@router.post("/api/escalations/{escalation_id}/corrections/confirm")
def confirm_correction(
    escalation_id: str,
    payload: CorrectionConfirmRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    escalation = db.get(Escalation, escalation_id)
    if not escalation:
        raise AccrueError("NOT_FOUND", "Escalation not found.", 404)
    assert_account_access(db, user, escalation.account_id)

    idempotency = request.headers.get("Idempotency-Key")
    if idempotency:
        existing = db.query(Correction).filter(Correction.idempotency_key == idempotency).first()
        if existing and existing.status == "approved":
            return {
                "request_id": _request_id(request),
                "correction_id": existing.id,
                "status": existing.status,
                "memory_id": existing.resulting_memory_id,
                "idempotent_replay": True,
            }

    correction = db.get(Correction, payload.correction_id)
    if not correction or correction.escalation_id != escalation_id:
        raise AccrueError("NOT_FOUND", "Correction preview not found.", 404)
    if correction.status == "approved":
        return {
            "request_id": _request_id(request),
            "correction_id": correction.id,
            "status": "approved",
            "memory_id": correction.resulting_memory_id,
            "idempotent_replay": True,
        }
    if not payload.confirm:
        correction.status = "rejected"
        db.commit()
        return {"request_id": _request_id(request), "correction_id": correction.id, "status": "rejected"}

    approved = (payload.approved_memory or correction.proposed_memory).strip()
    memory_id = f"mem_fix_{correction.id[-8:]}"
    memory = Memory(
        id=memory_id,
        account_id=escalation.account_id,
        memory_type=correction.memory_type,
        text=approved,
        scope=correction.scope,
        status="policy" if correction.scope == "team" else "preference",
        created_by=user.id,
        source_ref=f"correction://{correction.id}",
        version=1,
    )
    db.add(memory)
    correction.approved_memory = approved
    correction.status = "approved"
    correction.resulting_memory_id = memory_id
    correction.idempotency_key = idempotency
    hindsight.retain(
        account_id=escalation.account_id,
        content=approved,
        memory_id=memory_id,
        memory_type=correction.memory_type,
        source_ref=memory.source_ref,
        scope=correction.scope,
        timestamp=datetime.utcnow().isoformat(),
    )
    write_audit(
        db,
        actor_id=user.id,
        action="correction.confirm",
        object_type="memory",
        object_id=memory_id,
        request_id=_request_id(request),
        detail=approved[:500],
    )
    db.commit()
    return {
        "request_id": _request_id(request),
        "correction_id": correction.id,
        "status": "approved",
        "memory_id": memory_id,
        "writes_memory": True,
    }


def uuid4() -> str:
    import uuid

    return uuid.uuid4().hex

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.errors import AccrueError
from app.models import Escalation, Memory, SourceRecord, User
from app.services.access import assert_account_access

router = APIRouter(tags=["sources"])


def _source_payload(
    *,
    source_id: str,
    account_id: str,
    source_type: str,
    title: str,
    body: str,
    occurred_at: str | None = None,
    source_ref: str = "",
    sensitivity: str = "internal",
) -> dict:
    return {
        "id": source_id,
        "account_id": account_id,
        "type": source_type,
        "title": title,
        "body": body,
        "occurred_at": occurred_at,
        "source_ref": source_ref,
        "sensitivity": sensitivity,
    }


@router.get("/api/sources/{source_id}")
def get_source(
    source_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if source_id == "current_mail":
        return _source_payload(
            source_id="current_mail",
            account_id="",
            source_type="current_mail",
            title="Current escalation mail",
            body="This citation is the live pasted escalation mail in the workspace, not a stored CRM record.",
            source_ref="current_mail",
        )

    source = db.get(SourceRecord, source_id)
    if not source:
        source = db.query(SourceRecord).filter(SourceRecord.source_ref == source_id).first()
    if source:
        assert_account_access(db, user, source.account_id)
        return _source_payload(
            source_id=source.id,
            account_id=source.account_id,
            source_type=source.type,
            title=source.title,
            body=source.body,
            occurred_at=source.occurred_at.isoformat() if source.occurred_at else None,
            source_ref=source.source_ref,
            sensitivity=source.sensitivity,
        )

    escalation = db.get(Escalation, source_id)
    if escalation:
        assert_account_access(db, user, escalation.account_id)
        return _source_payload(
            source_id=escalation.id,
            account_id=escalation.account_id,
            source_type="escalation",
            title="Escalation note",
            body=escalation.input_text,
            occurred_at=escalation.created_at.isoformat() if escalation.created_at else None,
            source_ref=escalation.id,
        )

    memory = db.get(Memory, source_id)
    if memory:
        assert_account_access(db, user, memory.account_id)
        return _source_payload(
            source_id=memory.id,
            account_id=memory.account_id,
            source_type=memory.memory_type or "memory",
            title=memory.id,
            body=memory.text,
            occurred_at=memory.created_at.isoformat() if memory.created_at else None,
            source_ref=memory.source_ref or memory.id,
        )

    raise AccrueError("NOT_FOUND", "Source record not found.", 404)

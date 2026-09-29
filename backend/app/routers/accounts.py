from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.errors import AccrueError
from app.models import Account, Commitment, Incident, Memory, Stakeholder, User
from app.schemas import AskRequest
from app.services.access import assert_account_access
from app.services.ask import ask_account
from app.services.audit import write_audit

router = APIRouter(tags=["accounts"])


@router.get("/api/accounts/{account_id}/context")
def account_context(
    account_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    assert_account_access(db, user, account_id)
    account = db.get(Account, account_id)
    if not account:
        raise AccrueError("ACCOUNT_NOT_FOUND", "Account not found.", 404)
    stakeholders = db.query(Stakeholder).filter(Stakeholder.account_id == account_id).all()
    commitments = db.query(Commitment).filter(Commitment.account_id == account_id).all()
    incidents = db.query(Incident).filter(Incident.account_id == account_id).all()
    memories = (
        db.query(Memory)
        .filter(Memory.account_id == account_id, Memory.superseded_by.is_(None))
        .all()
    )
    return {
        "account": {
            "id": account.id,
            "name": account.name,
            "arr": account.arr,
            "segment": account.segment,
            "timezone": account.timezone,
            "status": account.status,
        },
        "stakeholders": [
            {
                "id": row.id,
                "name": row.name,
                "role": row.role,
                "influence": row.influence,
                "preferences": row.preferences,
            }
            for row in stakeholders
        ],
        "commitments": [
            {
                "id": row.id,
                "description": row.description,
                "owner": row.owner,
                "due_date": row.due_date,
                "status": row.status,
                "source_record_id": row.source_record_id,
            }
            for row in commitments
        ],
        "incidents": [
            {
                "id": row.id,
                "severity": row.severity,
                "summary": row.summary,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
                "impact": row.impact,
            }
            for row in incidents
        ],
        "memories": [
            {
                "id": row.id,
                "memory_type": row.memory_type,
                "text": row.text,
                "scope": row.scope,
                "status": row.status,
                "source_ref": row.source_ref,
                "version": row.version,
            }
            for row in memories
        ],
    }


@router.post("/api/accounts/{account_id}/ask")
def ask_company(
    account_id: str,
    payload: AskRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    assert_account_access(db, user, account_id)
    if not db.get(Account, account_id):
        raise AccrueError("ACCOUNT_NOT_FOUND", "Account not found.", 404)
    result = ask_account(
        db,
        account_id=account_id,
        query=payload.query,
        current_mail=payload.current_mail,
    )
    write_audit(
        db,
        actor_id=user.id,
        action="account.ask",
        object_type="account",
        object_id=account_id,
        request_id=getattr(request.state, "request_id", ""),
        detail=payload.query[:300],
    )
    db.commit()
    return {"request_id": getattr(request.state, "request_id", ""), **result}

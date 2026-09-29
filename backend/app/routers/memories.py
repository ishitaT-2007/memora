from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.db import get_db
from app.errors import AccrueError
from app.models import AuditEvent, Memory, SourceRecord, User
from app.services.access import assert_account_access
from app.services.seed import reset_and_seed

router = APIRouter(tags=["memories"])


@router.get("/api/memories/{memory_id}")
def get_memory(
    memory_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    memory = db.get(Memory, memory_id)
    if not memory:
        raise AccrueError("NOT_FOUND", "Memory not found.", 404)
    assert_account_access(db, user, memory.account_id)
    source = db.get(SourceRecord, memory.source_ref) if memory.source_ref else None
    if source is None and memory.source_ref:
        source = db.query(SourceRecord).filter(SourceRecord.source_ref == memory.source_ref).first()
    return {
        "memory": {
            "id": memory.id,
            "account_id": memory.account_id,
            "memory_type": memory.memory_type,
            "text": memory.text,
            "scope": memory.scope,
            "status": memory.status,
            "created_by": memory.created_by,
            "source_ref": memory.source_ref,
            "version": memory.version,
            "created_at": memory.created_at.isoformat() if memory.created_at else None,
        },
        "source": {
            "id": source.id,
            "type": source.type,
            "title": source.title,
            "body": source.body,
            "occurred_at": source.occurred_at.isoformat() if source.occurred_at else None,
            "source_ref": source.source_ref,
        }
        if source
        else None,
    }


@router.get("/api/audit")
def list_audit(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(100).all()
    return {
        "events": [
            {
                "id": row.id,
                "actor_id": row.actor_id,
                "action": row.action,
                "object_type": row.object_type,
                "object_id": row.object_id,
                "request_id": row.request_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }


@router.post("/api/admin/reset-demo")
def reset_demo(_user: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    reset_and_seed(db)
    return {"ok": True, "message": "Synthetic demo dataset restored."}

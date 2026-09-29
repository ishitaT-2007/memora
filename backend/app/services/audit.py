import uuid

from sqlalchemy.orm import Session

from app.models import AuditEvent


def write_audit(
    db: Session,
    *,
    actor_id: str,
    action: str,
    object_type: str,
    object_id: str,
    request_id: str = "",
    detail: str = "",
) -> None:
    db.add(
        AuditEvent(
            id=str(uuid.uuid4()),
            actor_id=actor_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            request_id=request_id,
            detail=detail[:2000],
        )
    )

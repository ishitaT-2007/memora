from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import get_settings
from app.data.corpus import CORPUS
from app.models import (
    Account,
    AccountAccess,
    AnalysisRun,
    AuditEvent,
    Commitment,
    Correction,
    Escalation,
    Incident,
    Memory,
    Outcome,
    SourceRecord,
    Stakeholder,
    User,
)
from app.services.hindsight_adapter import hindsight

settings = get_settings()
TABLES = [
    AuditEvent,
    Correction,
    AnalysisRun,
    Escalation,
    Memory,
    Outcome,
    Incident,
    Commitment,
    SourceRecord,
    Stakeholder,
    AccountAccess,
    Account,
    User,
]


def reset_and_seed(db: Session) -> None:
    for table in TABLES:
        db.query(table).delete()
    db.commit()
    hindsight.reset_mock()

    csm = User(
        id="usr_csm",
        email=settings.demo_csm_email.lower(),
        password_hash=hash_password(settings.demo_csm_password),
        role="csm",
        name="Jordan Lee",
    )
    admin = User(
        id="usr_admin",
        email=settings.demo_admin_email.lower(),
        password_hash=hash_password(settings.demo_admin_password),
        role="admin",
        name="Accrue Admin",
    )
    db.add_all([csm, admin])
    db.flush()

    for row in CORPUS["accounts"]:
        db.add(Account(**row))
    db.flush()

    for account in CORPUS["accounts"]:
        db.add(AccountAccess(id=str(uuid.uuid4()), user_id=csm.id, account_id=account["id"]))
        db.add(AccountAccess(id=str(uuid.uuid4()), user_id=admin.id, account_id=account["id"]))
    db.flush()

    for row in CORPUS["stakeholders"]:
        db.add(Stakeholder(**row))
    db.flush()
    for row in CORPUS["source_records"]:
        db.add(SourceRecord(**row))
    db.flush()
    for row in CORPUS["commitments"]:
        db.add(Commitment(**row))
    db.flush()
    for row in CORPUS["incidents"]:
        db.add(Incident(**row))
    db.flush()
    for row in CORPUS["outcomes"]:
        db.add(Outcome(**row))
    db.flush()
    for row in CORPUS["memories"]:
        db.add(Memory(**row, version=1, superseded_by=None))
        hindsight.retain(
            account_id=row["account_id"],
            content=row["text"],
            memory_id=row["id"],
            memory_type=row["memory_type"],
            source_ref=row["source_ref"],
            scope=row["scope"],
        )
    db.commit()

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="csm")
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    arr: Mapped[int] = mapped_column(Integer)
    segment: Mapped[str] = mapped_column(String(64))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    status: Mapped[str] = mapped_column(String(32), default="active")
    shareable_playbook: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    stakeholders = relationship("Stakeholder", back_populates="account")
    source_records = relationship("SourceRecord", back_populates="account")
    commitments = relationship("Commitment", back_populates="account")
    incidents = relationship("Incident", back_populates="account")
    outcomes = relationship("Outcome", back_populates="account")
    memories = relationship("Memory", back_populates="account")


class AccountAccess(Base):
    __tablename__ = "account_access"
    __table_args__ = (UniqueConstraint("user_id", "account_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)


class Stakeholder(Base):
    __tablename__ = "stakeholders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(120))
    influence: Mapped[str] = mapped_column(String(64))
    preferences: Mapped[str] = mapped_column(Text, default="")
    account = relationship("Account", back_populates="stakeholders")


class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    source_ref: Mapped[str] = mapped_column(String(160))
    sensitivity: Mapped[str] = mapped_column(String(32), default="internal")
    account = relationship("Account", back_populates="source_records")


class Commitment(Base):
    __tablename__ = "commitments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(120))
    due_date: Mapped[str] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    source_record_id: Mapped[str] = mapped_column(ForeignKey("source_records.id"), nullable=True)
    account = relationship("Account", back_populates="commitments")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    summary: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    impact: Mapped[str] = mapped_column(Text)
    account = relationship("Account", back_populates="incidents")


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    situation: Mapped[str] = mapped_column(Text)
    actions_taken: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(32))
    evidence_ref: Mapped[str] = mapped_column(String(160))
    account = relationship("Account", back_populates="outcomes")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    memory_type: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(String(32), default="account")
    status: Mapped[str] = mapped_column(String(32), default="verified")
    created_by: Mapped[str] = mapped_column(String(36))
    source_ref: Mapped[str] = mapped_column(String(160), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    superseded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    account = relationship("Account", back_populates="memories")


class Escalation(Base):
    __tablename__ = "escalations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    input_text: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16), default="P1")
    incident_facts: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    memory_mode: Mapped[str] = mapped_column(String(16), default="full")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    escalation_id: Mapped[str] = mapped_column(ForeignKey("escalations.id"), index=True)
    brief_json: Mapped[str] = mapped_column(Text)
    recommendations_json: Mapped[str] = mapped_column(Text)
    draft_text: Mapped[str] = mapped_column(Text)
    output_json: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(120))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    memory_limited: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    escalation_id: Mapped[str] = mapped_column(ForeignKey("escalations.id"), index=True)
    proposed_memory: Mapped[str] = mapped_column(Text)
    approved_memory: Mapped[str | None] = mapped_column(Text, nullable=True)
    memory_type: Mapped[str] = mapped_column(String(64), default="team_correction")
    scope: Mapped[str] = mapped_column(String(32), default="account")
    status: Mapped[str] = mapped_column(String(32), default="preview")
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    resulting_memory_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    object_type: Mapped[str] = mapped_column(String(64))
    object_id: Mapped[str] = mapped_column(String(64))
    request_id: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

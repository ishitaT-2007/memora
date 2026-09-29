from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class AskRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    current_mail: str = Field(default="", max_length=20000)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        return value.strip()


class AnalyzeRequest(BaseModel):
    account_id: str
    escalation_text: str = Field(..., min_length=20)
    severity: Literal["P1", "P2", "P3"] = "P1"
    incident_facts: str = ""
    memory_mode: Literal["full", "limited"] = "full"

    @field_validator("escalation_text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class CorrectionPreviewRequest(BaseModel):
    proposed_memory: str = Field(..., min_length=8, max_length=2000)
    memory_type: Literal[
        "team_correction",
        "landmine",
        "preference",
        "commitment",
        "policy",
    ] = "team_correction"
    scope: Literal["account", "team"] = "account"


class CorrectionConfirmRequest(BaseModel):
    correction_id: str
    approved_memory: str | None = None
    confirm: bool = True


class KnownFact(BaseModel):
    text: str
    source_ids: list[str]
    date: str | None = None
    verification_status: Literal["verified", "preference", "policy", "hypothesis"] = "verified"


class Recommendation(BaseModel):
    action: str
    rationale: str
    evidence_ids: list[str]
    owner_suggestion: str | None = None
    urgency: Literal["now", "today", "this_week"] | None = "now"


class Avoidance(BaseModel):
    action: str
    rationale: str
    evidence_ids: list[str]


class AnalysisOutput(BaseModel):
    brief: list[str]
    known_facts: list[KnownFact]
    unknowns: list[str]
    do: list[Recommendation]
    dont: list[Avoidance]
    reply_draft: str
    memory_ids: list[str]
    confidence_notes: str
    memory_limited: bool = False
    classification: dict = Field(default_factory=dict)


class SourceSnippet(BaseModel):
    id: str
    account_id: str
    type: str
    title: str
    body: str
    occurred_at: str | None = None
    source_ref: str = ""
    memory_type: str | None = None
    status: str | None = None
    scope: str | None = None

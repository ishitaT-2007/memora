from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AnalysisRun, Escalation
from app.schemas import AnalysisOutput, AnalyzeRequest
from app.services.llm_adapter import llm
from app.services.retrieval import classify_event, retrieve_context
from app.services.validator import validate_output
from app.services.audit import write_audit

settings = get_settings()


def analyze_escalation(
    db: Session,
    *,
    user_id: str,
    payload: AnalyzeRequest,
    request_id: str,
) -> tuple[Escalation, AnalysisRun, AnalysisOutput, dict[str, Any]]:
    started = time.perf_counter()
    text = payload.escalation_text
    if len(text) > settings.max_escalation_chars:
        text = text[: settings.max_escalation_chars]

    stored_text = text if settings.retain_raw_input else f"[redacted {len(text)} chars]"
    escalation = Escalation(
        id=str(uuid.uuid4()),
        account_id=payload.account_id,
        input_text=stored_text,
        severity=payload.severity,
        incident_facts=payload.incident_facts or "",
        created_by=user_id,
        memory_mode=payload.memory_mode,
    )
    db.add(escalation)
    db.flush()

    pack, memory_limited, hs_error = retrieve_context(
        db,
        account_id=payload.account_id,
        query=f"{text}\n{payload.incident_facts}",
        memory_mode=payload.memory_mode,
    )
    pack["incident_facts"] = payload.incident_facts
    pack["classification"] = classify_event(text, payload.severity)
    pack["escalation_id"] = escalation.id

    output = llm.generate(context_pack=pack, escalation_text=text, memory_limited=memory_limited)
    output = validate_output(
        output,
        valid_ids=set(pack.get("valid_source_ids") or []),
        escalation_text=text,
        memory_limited=memory_limited,
    )
    if hs_error:
        output.confidence_notes += f" Hindsight error: {hs_error}"

    latency = int((time.perf_counter() - started) * 1000)
    run = AnalysisRun(
        id=str(uuid.uuid4()),
        escalation_id=escalation.id,
        brief_json=json.dumps(output.brief),
        recommendations_json=json.dumps({"do": [item.model_dump() for item in output.do], "dont": [item.model_dump() for item in output.dont]}),
        draft_text=output.reply_draft,
        output_json=output.model_dump_json(),
        model_version=f"{llm.mode}:{llm.model}",
        latency_ms=latency,
        memory_limited=output.memory_limited,
    )
    db.add(run)
    write_audit(
        db,
        actor_id=user_id,
        action="escalation.analyze",
        object_type="escalation",
        object_id=escalation.id,
        request_id=request_id,
        detail=json.dumps({"memory_ids": output.memory_ids, "model": run.model_version, "latency_ms": latency}),
    )
    db.commit()
    db.refresh(escalation)
    db.refresh(run)
    return escalation, run, output, pack

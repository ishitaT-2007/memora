from __future__ import annotations

import re

from app.schemas import AnalysisOutput
from app.services.llm_adapter import strip_injected_promises

INVENTED_PATTERNS = [
    re.compile(r"\b(legal already approved|full refund|90%\s*discount|sso live tomorrow)\b", re.I),
]


def validate_output(
    output: AnalysisOutput,
    *,
    valid_ids: set[str],
    escalation_text: str,
    memory_limited: bool,
) -> AnalysisOutput:
    output.reply_draft = strip_injected_promises(output.reply_draft, escalation_text)
    output.memory_limited = memory_limited or output.memory_limited

    def known(ids: list[str]) -> list[str]:
        return [item for item in ids if item in valid_ids]

    if not memory_limited:
        cleaned_facts = []
        for fact in output.known_facts:
            cited = known(fact.source_ids)
            if not cited:
                output.unknowns.append(f"Dropped uncited claim: {fact.text[:140]}")
                continue
            fact.source_ids = cited
            cleaned_facts.append(fact)
        output.known_facts = cleaned_facts

        for rec in output.do:
            rec.evidence_ids = known(rec.evidence_ids)
        for rec in output.dont:
            rec.evidence_ids = known(rec.evidence_ids)
        output.do = [item for item in output.do if item.evidence_ids or memory_limited]
        output.dont = [item for item in output.dont if item.evidence_ids or "injection" in item.rationale.lower()]
        output.memory_ids = [item for item in output.memory_ids if item in valid_ids]

    for pattern in INVENTED_PATTERNS:
        if pattern.search(output.reply_draft):
            output.reply_draft = pattern.sub("[removed unsupported claim]", output.reply_draft)
            output.unknowns.append("Removed an unsupported commercial promise from the draft.")

    if memory_limited:
        output.known_facts = []
        output.memory_ids = []
        output.confidence_notes = (
            "Memory-limited result. Historical claims are intentionally omitted."
        )
    return output

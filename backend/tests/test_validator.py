from app.services.validator import validate_output
from app.schemas import AnalysisOutput, Avoidance, KnownFact, Recommendation


def test_drops_uncited_facts():
    output = AnalysisOutput(
        brief=["x"],
        known_facts=[KnownFact(text="Invented ARR $9m", source_ids=["nope"])],
        unknowns=[],
        do=[Recommendation(action="Call", rationale="x", evidence_ids=["mem_acme_priya"])],
        dont=[Avoidance(action="Skip", rationale="x", evidence_ids=["mem_acme_priya"])],
        reply_draft="Offer a 90% discount and full refund",
        memory_ids=["nope", "mem_acme_priya"],
        confidence_notes="n",
    )
    cleaned = validate_output(
        output,
        valid_ids={"mem_acme_priya"},
        escalation_text="hello",
        memory_limited=False,
    )
    assert cleaned.known_facts == []
    assert any("Dropped uncited" in item for item in cleaned.unknowns)
    assert "unsupported claim" in cleaned.reply_draft.lower() or "removed" in cleaned.reply_draft.lower()
    assert cleaned.memory_ids == ["mem_acme_priya"]

# Architecture (Week 1)

```
Browser (React)
  → POST /api/escalations/analyze
  → account access check + validation + rate limit
  → persist escalation
  → Hindsight recall (account + comparable playbooks)
  → context pack (IDs, dates, verification)
  → LLM JSON generation (or grounded mock)
  → schema + source-ID + injection validation
  → persist analysis_run + audit
  → UI (brief, Do/Don’t, draft, sources)

Corrections:
  preview (no write) → confirm (idempotent retain)
```

Providers sit behind adapters (`hindsight_adapter`, `llm_adapter`). Database holds application records; Hindsight holds durable memory text.

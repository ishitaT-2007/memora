# Release checklist (Week 8)

- [ ] Staging URL protected by authentication
- [ ] Demo passwords rotated if the URL is shared
- [ ] `.env` secrets not in git
- [ ] `GET /api/health` returns database ok
- [ ] Seed/reset procedure tested (`scripts/reset_demo.py` and admin button)
- [ ] Hindsight and LLM keys in env/secret manager only
- [ ] Readable error states: unknown account, validation, memory-limited, rate limit
- [ ] Golden tests: `pytest` green; 9/10 scripted scenarios pass
- [ ] No invented commitments/dates in the Acme 60s demo output
- [ ] Correction preview does not write; confirm writes once; replay retrieves it
- [ ] Team-wide memory rejected for CSM role
- [ ] Cross-account private memories not shown as this customer’s facts
- [ ] Draft remains unsent; copy/export works
- [ ] Backup/restore of application DB rehearsed
- [ ] Data retention note visible to stakeholders
- [ ] Two-person demo run-through completed
- [ ] Known limitations listed in README

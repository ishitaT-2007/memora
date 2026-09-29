# Data retention and deletion

Accrue is designed for **synthetic demo data** first. Do not load real customer data until vendor terms, access, and retention are reviewed.

## What we store

| Store | Contents | Default retention |
|---|---|---|
| `accounts` and related curated records | Synthetic profile, stakeholders, sources | Until demo reset |
| `escalations.input_text` | Raw paste if `RETAIN_RAW_INPUT=true` | Configurable; set false for real data |
| `analysis_runs` | Brief JSON, draft, model version, latency, memory IDs | Until demo reset |
| `corrections` / `memories` | Preview and approved rules with author + timestamp | Versioned; not silent overwrite of sources |
| `audit_events` | Actor, action, object, request id (not full email by default) | 90 days recommended in production |
| Hindsight banks | Same approved memory text + metadata | Follow Hindsight Cloud/OSS policy |

## Deletion / export

- Demo: admin reset wipes application DB tables listed in `seed.reset_and_seed` and the mock Hindsight file.
- Production (post-MVP): add an account export (JSON) and account delete that also drops the Hindsight bank `accrue-{account_id}`.
- Logs must not include provider secrets or raw prompts.

## Minimization

Do not ingest unfiltered mailboxes. Only curated, human-approved source records become trusted memory. Customer emails are untrusted content (prompt-injection safe).

# How Accrue uses Hindsight

Judging note: memory is the product, not a plugin.

## Banks

Each account has bank id `accrue-{account_id}`. Comparable playbooks are retained on their own account banks with `scope=comparable` so recall can use them as outcome examples without copying private stakeholder notes onto Acme.

## Operations

| Call | When |
|---|---|
| `retain` | Seed, and when a CSM confirms a correction |
| `recall` | Every Analyze with the escalation text as query |
| `reflect` | Not used in V1 (we need strict JSON + source IDs, so generation stays in our LLM adapter) |

## Metadata on retain

`memory_id`, `account_id`, `source_ref`, `scope`, `memory_type`

## Adapter

`app/services/hindsight_adapter.py` is the only module that talks to Hindsight. Mock mode implements retain/recall on disk so UI work never blocks on the cluster (Week 1 risk mitigation).

## Evaluation questions (Week 2)

- What did we promise Priya?
- Did Q2 SSO slip, and should we mention it?
- Which similar account was saved without a discount?
- Which similar account churned after credits?
- After correction, is “never offer credits to Priya” retrieved?

## Governance

Verified historical records are not overwritten by a correction. Corrections become new memories with author, timestamp, and scope. Team-wide scope requires admin. Customer email cannot become a system instruction.

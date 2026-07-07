# Receipts and verification

Governed executor lanes produce **receipts** — JSON artifacts that bind task, policy verdict, run plan, and execution evidence via content hashes.

## Receipt structure

Each `*-seed seal` issues a receipt containing:

| Field | Purpose |
|---|---|
| `claim` | What the receipt attests (type, boundary, transport, return code) |
| `authority` | Operator identity, intent hash, policy verdict hash |
| `evidence` | Content hashes of all four upstream artifacts |
| `evidence_paths` | Filesystem paths at issuance time |
| `signature` | Ed25519 over canonical payload (or `unsigned`) |

Signing payload excludes `receipt_hash` and replaces `signature` with a placeholder (`excluded_from_signing_payload_v1`).

## Lineage checks

Verification enforces hash lineage across the chain:

```
task ──► verdict ──► plan ──► evidence
         task_hash    policy_verdict_hash    plan_hash    evidence_hash
```

`operator_intent_bound` confirms `intent_hash` in the task matches `operator_intent_hash(task)` computed at verify time.

## Verification tools

| Tool | Scope |
|---|---|
| `codex-seed verify` / `grok-seed verify` | Lane-internal: hash match + lineage + signature |
| `wop-verify` | Ed25519 signature over arbitrary canonical JSON |
| `wop-receipt-verify` | External receipt verify (includes `receipt_hash` in payload) |

Default is **strict** (`--strict`). Use `--allow-partial` only when some artifacts are intentionally omitted.

## Baseline lanes

Tracked baseline evidence in this repo:

| Lane | Executor | Mode |
|---|---|---|
| `evidence/codex_hardening_v1/` | Codex | dry-run |
| `evidence/grok_hardening_v1/` | Grok | dry-run |

Reproduce a baseline:

```bash
codex/bin/codex-seed verify --receipt evidence/codex_hardening_v1/receipt.json --strict
grok/bin/grok-seed verify --receipt evidence/grok_hardening_v1/grok_task_summarize_repo_001.receipt.json --strict
```

## What receipts do not prove

- Code correctness or test passage
- Merge approval or deployment authorization
- Absence of security defects
- That stdout content is truthful (only that it was captured)

Promotion to a higher trust tier requires a separate verifier pass and operational authority (e.g. Goal-0 phone receipts).
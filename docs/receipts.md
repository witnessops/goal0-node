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

## Verifier split

goal0-node uses **two receipt families** with different verifiers. Do not cross them.

### Receipt families

| Family | Schema | Example path | Top-level keys |
|---|---|---|---|
| **Genesis** | `witnessops.genesis_receipt.v1` | `receipts/baseline/genesis_000.json` | `claim`, `evidence`, `lineage`, `signature` |
| **Executor** | `vaultsovereign.{codex,grok}.receipt.v1` | `evidence/*_hardening_v1/*.receipt.json` | `claim`, `authority`, `evidence`, `evidence_paths`, `receipt_hash`, `signature` |

Genesis receipts attest bootstrap custody. Executor receipts attest a governed `*-seed` pipeline run.

### Which verifier to use

| Verifier | Genesis receipts | Executor receipts |
|---|---|---|
| `wop-receipt-verify` | **Yes** — structure, sidecar, signature | **No** — schema mismatch (`lineage` expected) |
| `wop-verify` | **Yes** — Ed25519 signature only | **No** — signing payload differs (see below) |
| `codex-seed verify` / `grok-seed verify` | **No** — wrong schema and bindings | **Yes** — hash lineage + intent + signature |

**Rule:** executor baselines → `*-seed verify --strict`. Genesis baseline → `wop-receipt-verify` (+ optional `wop-verify`).

### Signing payload difference

Executor receipts (`*-seed seal`) sign a payload that:

- **excludes** `receipt_hash`
- replaces `signature` with `{"algorithm":"unsigned","note":"excluded_from_signing_payload_v1"}`

`wop-verify` and `wop-receipt-verify` use `wop_lib.signing_payload()`, which:

- **retains** `receipt_hash` when present
- uses a different unsigned placeholder

Genesis receipts have no `receipt_hash`, so `wop-*` tools verify genesis correctly. Executor receipts verify only through `*-seed verify` until `wop_lib` is aligned with the executor signing contract.

### Tool reference

| Tool | What it checks |
|---|---|
| `codex-seed verify` / `grok-seed verify` | Artifact hash match, task↔verdict↔plan↔evidence lineage, operator intent, Ed25519 signature |
| `wop-verify` | Ed25519 signature via `wop_lib` payload (genesis-compatible) |
| `wop-receipt-verify` | JSON structure, optional sidecar SHA-256, optional schema match, optional signature |

Default for `*-seed verify` is **strict** (`--strict`). Use `--allow-partial` only when some artifacts are intentionally omitted.

### Baseline commands

**Genesis** (`receipts/baseline/`):

```bash
tools/wop-receipt-verify receipts/baseline/genesis_000.json \
  --sidecar receipts/baseline/genesis_000.json.sha256 \
  --require-schema witnessops.genesis_receipt.v1 \
  --verify-signature

tools/wop-verify receipts/baseline/genesis_000.json
```

**Executor lanes** (`evidence/codex_hardening_v1/`, `evidence/grok_hardening_v1/`):

```bash
codex/bin/codex-seed verify --receipt evidence/codex_hardening_v1/receipt.json --strict
grok/bin/grok-seed verify --receipt evidence/grok_hardening_v1/grok_task_summarize_repo_001.receipt.json --strict
```

Executor baseline lanes have no SHA-256 sidecar files. Sidecar checks apply to genesis only.

## Baseline lanes

Tracked baseline artifacts in this repo:

| Path | Type | Notes |
|---|---|---|
| `receipts/baseline/genesis_000.json` | Genesis | Signed node bootstrap receipt |
| `evidence/codex_hardening_v1/` | Executor | Codex dry-run hardening lane |
| `evidence/grok_hardening_v1/` | Executor | Grok live-run hardening lane |

Per-run governance receipts under `receipts/<run_id>/` are node-local and gitignored.

## What receipts do not prove

- Code correctness or test passage
- Merge approval or deployment authorization
- Absence of security defects
- That stdout content is truthful (only that it was captured)

Promotion to a higher trust tier requires a separate verifier pass and operational authority (e.g. Goal-0 phone receipts).
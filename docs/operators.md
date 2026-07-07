# Operator guide

Quick reference for running governed executor lanes on a WitnessOps node.

## Prerequisites

| Requirement | Codex | Grok |
|---|---|---|
| CLI installed | `codex` on PATH | `grok` on PATH |
| Auth | ChatGPT login (`codex login`) | `grok login` (TTY required) |
| Node key | `identity/private/node_ed25519.pem` | same |
| Policy | `policies/codex_exec_policy.v1.json` | `policies/grok_exec_policy.v1.json` |

## Task bundle workflow

### 1. Prepare task

Edit or copy an example from `codex/tasks/examples/` or `grok/tasks/examples/`.

Required fields:

- `operator_approval.approved_by`, `approved_at`, `intent_hash`
- `target_repo.path` — absolute path that exists on node
- `target_repo.expected_root_markers` — files that must exist in repo root

### 2. Bind operator intent

```bash
codex/bin/codex-seed intent-hash --task <task.json>
# or
grok/bin/grok-seed intent-hash --task <task.json>
```

Copy the returned `intent_hash` into `operator_approval.intent_hash` in the task bundle.

### 3. Run pipeline

```bash
EVID=evidence/my_run
TASK=<task.json>
SEED=codex/bin/codex-seed   # or grok/bin/grok-seed

$SEED validate  --task "$TASK" --out "$EVID/verdict.json"
$SEED render    --task "$TASK" --verdict "$EVID/verdict.json" --out "$EVID/plan.json"
$SEED run       --plan "$EVID/plan.json" --task "$TASK" --verdict "$EVID/verdict.json" \
                --out "$EVID/evidence.json"            # add --dry-run to skip execution
$SEED seal      --task "$TASK" --verdict "$EVID/verdict.json" --plan "$EVID/plan.json" \
                --run "$EVID/evidence.json" --receipt "$EVID/receipt.json"
$SEED verify    --receipt "$EVID/receipt.json" --strict
```

`run` requires both `--task` and `--verdict` (bound execution). `seal` auto-signs when the node private key is present.

## Choosing an executor

| Scenario | Executor | Sandbox |
|---|---|---|
| Patch, test, implement | Codex | `workspace-write` |
| Read-only audit / summarize | Codex or Grok | `read-only` / `strict` |
| Security review (read-only) | Either | `read-only` / `strict` |
| Independent second pass | Grok | `strict` + tool allowlist |

## Interactive Grok

Headless governed tasks use `grok-seed`. Interactive sessions use the launch wrapper:

```bash
tools/grok-governed-launch.sh
```

Interactive sessions are **not** automatically receipt-backed. Post-session verify lanes are a separate governed step.

## Verifier split

Two receipt families, two verifier paths. Full detail: [receipts.md](receipts.md#verifier-split).

| You sealed with | Verify with | Do not use |
|---|---|---|
| `codex-seed seal` / `grok-seed seal` | matching `*-seed verify --strict` | `wop-receipt-verify`, `wop-verify` |
| Genesis bootstrap / `wop-sign` | `wop-receipt-verify`, `wop-verify` | `*-seed verify` |

### After a governed run (executor receipt)

Always verify with the lane that issued the receipt:

```bash
codex/bin/codex-seed verify --receipt "$EVID/receipt.json" --strict
# or
grok/bin/grok-seed verify --receipt "$EVID/receipt.json" --strict
```

This checks artifact hashes, task↔verdict↔plan↔evidence lineage, operator intent, and the Ed25519 signature (executor signing contract).

### Genesis / node bootstrap receipt

For `receipts/baseline/genesis_000.json` only:

```bash
tools/wop-receipt-verify receipts/baseline/genesis_000.json \
  --sidecar receipts/baseline/genesis_000.json.sha256 \
  --require-schema witnessops.genesis_receipt.v1 \
  --verify-signature

tools/wop-verify receipts/baseline/genesis_000.json
```

### Why `wop-*` fails on executor receipts

Executor receipts include `receipt_hash` and use `authority` (not `lineage`). `*-seed seal` signs with `receipt_hash` **excluded**; `wop_lib` keeps it in the payload. Genesis receipts have no `receipt_hash`, so `wop-*` tools match genesis only.

### Promotion rule

```
*-seed verify pass  →  eligible for promotion review
wop-* pass on genesis  →  bootstrap trust anchor intact
```

Neither verifier alone proves correctness, merge safety, or deployment authorization.
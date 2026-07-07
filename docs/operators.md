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

## Promotion checklist

Use this before treating a governed run as **promoted** (shared upstream, merged, deployed, or cited as proof). Sections **C** and **D** are human gates — see [Completing C](#completing-c) and [Completing D](#completing-d) for step-by-step instructions and an [operator attestation](#operator-attestation-c--d) template.

### A. Node trust anchor (one-time / periodic)

- [ ] Genesis baseline verifies:
  ```bash
  tools/wop-receipt-verify receipts/baseline/genesis_000.json \
    --sidecar receipts/baseline/genesis_000.json.sha256 \
    --require-schema witnessops.genesis_receipt.v1 \
    --verify-signature
  tools/wop-verify receipts/baseline/genesis_000.json
  ```
- [ ] `identity/public/node_ed25519.pub.pem` matches `identity/node_trust_anchor_manifest.v1.json`
- [ ] `identity/private/node_ed25519.pem` present on-node only (never committed)
- [ ] Policy bundle manifest current: `policies/policy_bundle_manifest.v1.json` lists both Codex and Grok policies

### B. Governed run complete (per executor receipt)

- [ ] Pipeline finished: `validate → render → run → seal → verify`
- [ ] Policy verdict was `allow` before render/run
- [ ] `run` used bound `--task` and `--verdict`
- [ ] Matching `*-seed verify --strict` passes (exit 0):
  ```bash
  codex/bin/codex-seed verify --receipt <receipt.json> --strict
  # or
  grok/bin/grok-seed verify --receipt <receipt.json> --strict
  ```
- [ ] Verifier report shows `decision: pass` for: artifact hashes, lineage, operator intent, signature

### C. Authority layer (human)

- [ ] Task bundle `operator_approval` complete (`approved_by`, `approved_at`, `intent_hash`)
- [ ] `intent_hash` matches `*-seed intent-hash --task` output
- [ ] Operator understands task `intended_effect` (read-only vs workspace-write)
- [ ] Goal-0 phone authority recorded separately if promotion crosses device boundary

#### Completing C

C is a **human gate**. Verifier pass (B) checks intent hash binding cryptographically; C is your attestation that the right person approved the right task **before** run/seal.

**1. Identify the receipt and task.** Open the receipt under promotion and read `evidence_paths.task` (or use the task path you passed to `seal`):

```bash
EVID=evidence/my_run          # directory containing receipt.json
RECEIPT=$EVID/receipt.json
TASK=$(python3 -c "import json; print(json.load(open('$RECEIPT'))['evidence_paths']['task'])")
SEED=codex/bin/codex-seed     # or grok/bin/grok-seed — must match receipt schema family
```

**2. Confirm `operator_approval` on the task bundle.** All three fields must be present and non-empty:

```bash
python3 -c "import json; t=json.load(open('$TASK')); print(json.dumps(t['operator_approval'], indent=2))"
python3 -c "import json; t=json.load(open('$TASK')); print('intended_effect:', t['policy']['intended_effect'])"
```

**3. Recompute and match `intent_hash`.** The value must equal both `operator_approval.intent_hash` in the task and `authority.operator_intent_hash` in the receipt:

```bash
$SEED intent-hash --task "$TASK"
python3 -c "import json; r=json.load(open('$RECEIPT')); print('receipt intent:', r['authority']['operator_intent_hash'])"
```

If recompute ≠ task ≠ receipt → **Reject** (task edited after approval, or wrong task bound).

**4. State `intended_effect` in plain language.** Before checking C, you should be able to answer:

| `intended_effect` | Operator must understand |
|---|---|
| `read_only_report` | Recon / summarize only; no writes expected |
| workspace-write (Codex) / non-read-only (Grok) | Files may change; git diff review required in D |

**5. Goal-0 phone authority (when applicable).** If promotion means citing proof upstream, merging narrative off-node, or deploying: record authority on the **phone lane** separately. A node receipt does not substitute for Goal-0 operational receipts. Skip when attesting node-local health only.

**C complete when** you can attest: approved identity, approval timestamp, intent hash match, understood sandbox/effect, and upstream agreement if the claim crosses the device boundary.

### D. Evidence review (beyond verify pass)

- [ ] `execution_evidence.return_code` reviewed (0 ≠ success claim, only recorded rc)
- [ ] Git diff in evidence reviewed if sandbox allowed writes (`git.diff_bytes` / `diff_sha256`)
- [ ] No secret patterns in stdout/stderr (check `output_handling` if redaction ran)
- [ ] Claims in stdout are scoped to observed evidence — receipt does not vouch for content truth

#### Completing D

D is a **human gate**. `verify --strict` proves artifact lineage and signature; D is your review of what the executor actually recorded.

**1. Open execution evidence** from `evidence_paths.execution_evidence` in the receipt:

```bash
RUN=$(python3 -c "import json; print(json.load(open('$RECEIPT'))['evidence_paths']['execution_evidence'])")
python3 -c "import json; e=json.load(open('$RUN')); print(json.dumps({k:e[k] for k in ('return_code','transport','git','output_handling')}, indent=2))"
```

**2. Review `return_code`.** `0` means the subprocess exited zero (or dry-run succeeded). It does **not** mean correct, merge-safe, or deployment-ready. Note `transport`:

| `transport` | Meaning for promotion scope |
|---|---|
| `dry_run` | Pipeline smoke only — argv captured, CLI not executed |
| `grok_cli` / live Codex | Executor ran; stdout content is in scope for D |

**3. Review git / filesystem changes** when writes were allowed:

```bash
python3 -c "import json; g=json.load(open('$RUN'))['git']; print(json.dumps(g, indent=2))"
```

For read-only tasks expect `diff_bytes: 0`. If `diff_sha256` and `status_*` are null, the target may not be a git work tree — that does **not** prove no filesystem changes. For write lanes, inspect `diff_bytes`, `diff_sha256`, and `status_after` before promote.

**4. Check secrets and redaction** via `output_handling`:

```bash
python3 -c "import json; print(json.dumps(json.load(open('$RUN'))['output_handling'], indent=2))"
```

Empty `*_secret_patterns` arrays mean policy regex did not match captured output. Manually scan stdout/stderr for tokens, keys, or PII the patterns may miss. If `output_redacted: true`, confirm redaction is acceptable for the promotion scope.

**5. Scope claims in stdout.** Read the captured output (truncate for large blobs):

```bash
python3 -c "import json; s=json.load(open('$RUN')).get('stdout',''); print(s[:4000] if isinstance(s,str) else json.dumps(s)[:4000])"
```

Ask:

- Are claims limited to observed evidence?
- Does output respect `claim.boundary` on the receipt? (Executor receipts disclaim correctness, merge, deployment, and absence of defects.)

**D complete when** you can attest: return code reviewed, git/diff acceptable for the sandbox, no unacceptable secrets, and stdout claims are scoped — not overstated beyond the receipt boundary.

### Operator attestation (C + D)

No formal attestation file is required in-repo. Record a short note in your operator log or Goal-0 journal before **Promote**:

```text
receipt: <receipt_id or path>
C: approved_by=<id> approved_at=<iso8601> intent_hash=<sha256:...> matches; intended_effect=<...>; upstream=<yes|no|n/a>
D: return_code=<n> transport=<...>; git diff_bytes=<n>; secrets=<none|redacted|hold>; claims scoped to evidence
promote_scope: <what this promotion authorizes — e.g. baseline smoke / merge / deploy>
```

**Hold** if D is incomplete or `transport: dry_run` but you need a live-execution claim. **Reject** if C intent mismatch or policy was `deny`.

### E. Promotion gates (explicit non-goals)

Do **not** promote on verifier pass alone. Still required separately:

- [ ] Code review / second executor pass (if material change)
- [ ] Tests or CI (if implementation lane)
- [ ] Merge approval (if landing to main)
- [ ] Deployment authorization (if leaving the node)

### F. Reproduce repo baselines (regression smoke)

Before citing goal0-node as healthy, all four baseline verifiers should pass:

```bash
cd /home/ops/witnessops-node
tools/baseline-regression.sh
```

Or run individually:

```bash
codex/bin/codex-seed verify --receipt evidence/codex_hardening_v1/receipt.json --strict
grok/bin/grok-seed verify --receipt evidence/grok_hardening_v1/grok_task_summarize_repo_001.receipt.json --strict
tools/wop-receipt-verify receipts/baseline/genesis_000.json \
  --sidecar receipts/baseline/genesis_000.json.sha256 \
  --require-schema witnessops.genesis_receipt.v1 \
  --verify-signature
tools/wop-verify receipts/baseline/genesis_000.json
```

### Promotion outcome

| Result | Meaning |
|---|---|
| **Promote** | All applicable A–E checks pass; upstream authority agrees |
| **Hold** | Verifier pass but D or E incomplete |
| **Reject** | Any strict verify fails, intent mismatch, or policy was `deny` |
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

Use this before treating a governed run as **promoted** (shared upstream, merged, deployed, or cited as proof).

| Section | Type | Instructions |
|---|---|---|
| **C** | Human gate | [Completing C](#completing-c) |
| **D** | Human gate | [Completing D](#completing-d) |
| **Attestation** | Record C+D | [Operator attestation](#operator-attestation-c--d) |
| **Hold → Promote** | Decision | [Moving from Hold to Promote](#moving-from-hold-to-promote) |

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

Record C+D before changing promotion outcome. Two options:

**In-repo (recommended for baseline lanes):** `evidence/<lane>/operator_attestation.v1.json` plus SHA256 sidecar:

```bash
sha256sum evidence/<lane>/operator_attestation.v1.json \
  > evidence/<lane>/operator_attestation.v1.json.sha256
```

Schema: `witnessops.operator_attestation.v1`. Examples:

- `evidence/codex_hardening_v1/operator_attestation.v1.json`
- `evidence/grok_hardening_v1/operator_attestation.v1.json`

Required fields: `checklist.C_authority`, `checklist.D_evidence`, `promote_scope`, `promotion_outcome` (`hold` | `promote` | `reject`), `attestation_text`.

**Operator log / Goal-0 journal (minimal):**

```text
receipt: <receipt_id or path>
C: approved_by=<id> approved_at=<iso8601> intent_hash=<sha256:...> matches; intended_effect=<...>; upstream=<yes|no|n/a>
D: return_code=<n> transport=<...>; git diff_bytes=<n>; secrets=<none|redacted|hold>; claims scoped to evidence
promote_scope: <what this promotion authorizes — e.g. baseline smoke / merge / deploy>
promotion_outcome: hold | promote | reject
```

**Hold** if D is incomplete, E is open, upstream is partial, or `transport: dry_run` but you need a live-execution claim. **Reject** if C intent mismatch or policy was `deny`.

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
| **Promote** | All applicable A–E checks pass; upstream authority agrees; `promote_scope` matches evidence |
| **Hold** | Verifiers and/or C+D pass, but E incomplete, upstream partial, or scope overstated |
| **Reject** | Any strict verify fails, intent mismatch, or policy was `deny` |

#### Moving from Hold to Promote

**Promote is a recorded operator decision**, not an automatic verifier result. Completing C+D with `promotion_outcome: hold` means: attestation is done, but the claim is not yet authorized upstream.

##### Prerequisites

Before setting `promotion_outcome: promote` on an attestation:

| Prerequisite | How to confirm |
|---|---|
| **A** trust anchor | Genesis + pubkey manifest + policy bundle (or `tools/baseline-regression.sh` for periodic smoke) |
| **B** verifier pass | `*-seed verify --strict` exit 0 on the receipt under promotion |
| **C** authority | [Completing C](#completing-c) — intent hash match, understood `intended_effect` |
| **D** evidence | [Completing D](#completing-d) — rc, git, secrets, scoped stdout |
| **E** gates | Applicable items in [E](#e-promotion-gates-explicit-non-goals) below |
| **F** regression | `tools/baseline-regression.sh` when citing goal0-node health |
| **Scope** | `promote_scope` matches what receipts prove (see scope table) |
| **Upstream** | Sovereign agrees; Goal-0 recorded if claim crosses phone boundary |

##### Step 1 — Name the promotion claim

Pick one explicit claim. Do not Promote broader than evidence supports.

| Tier | Example `promote_scope` | Typical evidence required |
|---|---|---|
| **Narrow** | Baseline lane attested + regression green | Tracked `evidence/*_hardening_v1` + F pass |
| **Medium** | Node healthy for governed read-only work on `main` | Both baselines + E review + F + CI |
| **Wide** | Production-ready / safe to deploy off-node | Live execution receipts + Goal-0 PASS + custody/WireGuard proof |

##### Step 2 — Close E gates

| E item | Action when promoting… |
|---|---|
| Code review / second executor | Material `main` changes → other executor reviews diff or attestation commits |
| Tests or CI | Run `tools/baseline-regression.sh`; confirm GitHub Actions green on target commit |
| Merge approval | Required if landing to `main`; skip if promoting already-merged HEAD |
| Deployment authorization | Required only when `promote_scope` includes leaving the node |

Record E completion in the attestation `promotion_outcome_reason` or operator log.

##### Step 3 — Resolve upstream authority

When promotion crosses the phone/device boundary or cites proof off-node:

| Check | Hold blocker | Path to Promote |
|---|---|---|
| Goal-0 runtime | `partial_pass` (stale PIDs, health timeout) | Restore services; loopback PASS on configured ports |
| WireGuard | `not_proven` | `wg show` handshake proof, or narrow `promote_scope` to exclude mesh |
| Secret custody / UI / script safety | `not_proven` | Prove, or exclude from `promote_scope` |
| Repo drift (e.g. goal0-console dirty) | local modifications | Commit, stash, or document irrelevance |

For **node-local baseline only**, set `goal0_phone_authority: n/a` in the attestation and state that in `promotion_outcome_reason`.

##### Step 4 — Match scope to transport

| Lane evidence | Can Promote as… | Cannot Promote as… |
|---|---|---|
| `transport: dry_run` (codex baseline) | Pipeline smoke / verifier regression | Live Codex execution |
| `transport: grok_cli` (grok baseline) | Governed read-only recon recorded | Correctness, merge safety, deploy, no-defects |
| Live write lane | Material change with reviewed git diff | Without D review of `git.diff_bytes` |

Need a live Codex execution claim → new `validate → render → run → seal → verify` **without** `--dry-run`, then new C+D attestation.

##### Step 5 — Approval timing (optional hygiene)

If `approved_at` post-dates sealed evidence (baseline backfill), either:

- Accept: document `approval_timing: baseline_backfill_accepted` in attestation notes, or
- Re-run pipeline with approval recorded **before** `run`/`seal`.

##### Step 6 — Update attestation and sidecar

Edit `evidence/<lane>/operator_attestation.v1.json`:

```json
{
  "promotion_outcome": "promote",
  "promotion_outcome_reason": "E review complete; upstream agrees; scope limited to <claim>",
  "promote_scope": "<exact claim authorized>",
  "checklist": {
    "C_authority": { "goal0_phone_authority": "pass | partial | n/a" }
  }
}
```

Regenerate sidecar, commit, push:

```bash
cd /home/ops/witnessops-node
sha256sum evidence/<lane>/operator_attestation.v1.json \
  > evidence/<lane>/operator_attestation.v1.json.sha256
git add evidence/<lane>/operator_attestation.v1.json*
git commit -m "Promote operator attestation for <lane>"
git push origin main
```

Confirm CI: Baseline regression workflow passes on the attestation commit.

##### Step 7 — Sovereign sign-off

Add to `attestation_text` or Goal-0 journal:

```text
upstream_authority: <identity> agrees promote_scope=<...> at <ISO8601>
attestation_ids: attest_codex_hardening_v1_*, attest_grok_hardening_v1_*
```

Phone-bound promotion requires a Goal-0 operational receipt referencing these attestation IDs.

##### Recommended narrow Promote (goal0-node baselines today)

When both baseline lanes are attested and regression-green, the honest narrow claim is:

```text
promote_scope: Dual-executor baseline hardening lanes (codex dry-run smoke + grok read-only recon)
               are verified, attested, and regression-green on main.
```

Minimum steps: E second-executor review of attestation/CI commits → update both `operator_attestation.v1.json` to `promote` → sovereign sign-off → push → CI green.

Do **not** Promote production-ready, live Codex execution, or off-node deploy without additional evidence and upstream PASS.

##### Hold → Promote cheat sheet

| Situation | Outcome |
|---|---|
| Verifiers pass; C+D incomplete | **Hold** — finish [Completing C/D](#completing-c) |
| C+D done; E or upstream open | **Hold** — finish E/upstream steps above |
| C+D done; scope overstated (e.g. dry_run → live claim) | **Hold** — narrow scope or new run |
| A–E applicable pass; scope explicit; sovereign agrees | **Promote** — update attestation |
| Verifier fail or intent mismatch | **Reject** |
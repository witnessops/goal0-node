# Architecture

goal0-node implements a **dual-executor WitnessOps control plane** on Debian. Two coding agents — Codex and Grok — run as governed lanes, not free agents.

## System context

```
┌─────────────────────┐
│  Phone (Goal-0)     │  operational receipts, human authority
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  goal0-node         │  policy + receipt + verification
│  (this repo)        │
├──────────┬──────────┤
│  Codex   │  Grok    │  executor lanes
└──────────┴──────────┘
```

- **Phone** captures Goal-0 operational receipts and supplies human authority upstream.
- **Debian node** enforces policy, records execution evidence, issues signed receipts.
- **Executors** produce governed work products; a separate verifier must pass before promotion.

## Five layers

Every governed run traverses the same layers:

| Layer | Artifact | Question answered |
|---|---|---|
| **Authority** | `operator_approval` + policy verdict | Who approved what, under which policy? |
| **Execution** | run plan (`argv`) | What command was rendered and guarded? |
| **Evidence** | execution evidence | What happened (rc, stdout/stderr, git diff)? |
| **Proof** | signed receipt | What hashes are bound and who signed? |
| **Verification** | verifier report | Do artifacts still match the receipt? |

A receipt proves **governed execution was recorded**. It does not prove correctness, merge safety, deployment, or absence of defects.

## Executor symmetry

Codex and Grok share pipeline shape but differ in policy surface:

| | Codex | Grok |
|---|---|---|
| **Binary** | `codex exec` | `grok` headless |
| **Sandbox** | `read-only`, `workspace-write` | `strict`, `normal` |
| **Tool control** | sandbox + approval mode | `--tools` allowlist or `--disallowed-tools` |
| **Typical role** | implementation | review / recon / alternate pass |

Both use `*-seed` CLIs with identical subcommands: `intent-hash`, `validate`, `render`, `run`, `seal`, `verify`.

## Executor schema roots

Policies and artifact schemas are split across two layers:

| Layer | Path | Contents |
|---|---|---|
| **Policy bundle** | `policies/` | Exec policies for both lanes; Codex-only shared schemas |
| **Executor trees** | `codex/schemas/`, `grok/schemas/` | Per-executor artifact schemas (task, plan, evidence, receipt, verifier report) |

`policies/policy_bundle_manifest.v1.json` declares the canonical roots:

```json
"executor_schema_roots": {
  "codex": "codex/schemas/",
  "grok": "grok/schemas/"
}
```

### What lives where

**`policies/`** (install root, hashed in bundle manifest):

- `codex_exec_policy.v1.json` — Codex exec policy
- `grok_exec_policy.v1.json` — Grok exec policy
- `schemas/codex_policy_verdict.schema.json` — vendored Codex verdict schema
- `schemas/codex_run_plan.schema.json` — vendored Codex run-plan schema

**`codex/schemas/`** (executor root):

- `codex_task_bundle`, `codex_run_plan`, `codex_policy_verdict`
- `codex_execution_evidence`, `codex_receipt`, `codex_verifier_report`

**`grok/schemas/`** (executor root):

- `grok_task_bundle`, `grok_run_plan`, `grok_policy_verdict`
- `grok_execution_evidence`, `grok_receipt`, `grok_verifier_report`

### Why the layout is asymmetric

Codex was the first seed bundle; its policy verdict and run-plan schemas were vendored under `policies/schemas/` at install time. Grok arrived as a second executor with schemas kept self-contained under `grok/schemas/`.

This is intentional:

- **Do not duplicate** Grok schemas into `policies/schemas/`.
- **Do reference** executor roots explicitly in the policy bundle manifest.
- **Do treat** `policies/` as the exec-policy install surface, not the sole schema root for both lanes.

When adding a third executor, follow the Grok pattern: policy file in `policies/`, artifact schemas under `<executor>/schemas/`, and register the root in `executor_schema_roots`.

## Promotion rule

```
executor receipt  →  verifier pass  →  promoted claim
       ✗ alone
```

Use `*-seed verify --strict` for lane-internal checks. Use `wop-receipt-verify` for external verification that includes `receipt_hash` in the signed payload.

## What stays off-node

- Private signing keys (`identity/private/`)
- Live-run evidence noise (only baseline lanes are tracked in git)
- Per-run governance receipt archives (`receipts/<run_id>/` — except `receipts/baseline/`)
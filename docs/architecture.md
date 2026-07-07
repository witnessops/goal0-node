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

## Promotion rule

```
executor receipt  →  verifier pass  →  promoted claim
       ✗ alone
```

Use `*-seed verify --strict` for lane-internal checks. Use `wop-receipt-verify` for external verification that includes `receipt_hash` in the signed payload.

## What stays off-node

- Private signing keys (`identity/private/`)
- Live-run evidence noise (only baseline lanes are tracked in git)
- Governance receipt archives (`receipts/` — node-local audit trail)
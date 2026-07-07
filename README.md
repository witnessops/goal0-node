# goal0-node

WitnessOps governed runtime node for Goal-0. Hosts two policy-gated coding executors — **Codex** and **Grok** — plus operator tooling for signing, verification, and receipt lineage.

Neither executor is a free agent. Both run through the same governed pipeline and produce signed receipts that a separate verifier must validate before claims are promoted.

**Public demo:** This repository is a reference implementation for inspectable governed execution — not a production authority surface. See [SECURITY.md](SECURITY.md) and [docs/PUBLIC_DEMO.md](docs/PUBLIC_DEMO.md).

## Architecture

```
Phone (Goal-0 service)
  operational receipts, human authority
        |
        v
Debian witnessops-node  <-- this repo
  policy + receipt + verification control plane
        |
   +----+----+
   |         |
Codex     Grok
executor  executor
```

### Five layers

| Layer | What happens |
|---|---|
| **Authority** | Operator approves a task bundle; `intent_hash` binds approval to task body |
| **Execution** | `*-seed` validates policy, renders argv, runs with guards (no bypass flags) |
| **Evidence** | stdout/stderr, return code, git diff snapshot captured |
| **Proof** | Node Ed25519 key signs receipt over task, verdict, plan, evidence hashes |
| **Verification** | `*-seed verify` (strict) + `wop-verify` external check before promotion |

### Executor roles

| Executor | Path | Policy | Typical use |
|---|---|---|---|
| **Codex** | `codex/` | `policies/codex_exec_policy.v1.json` | Implementation — structured edits, tests, repo operations |
| **Grok** | `grok/` | `policies/grok_exec_policy.v1.json` | Second lane — review, reconnaissance, alternate implementer |

Both executors are symmetric in shape (validate → render → run → seal → verify) but differ in policy: Codex uses `--sandbox read-only|workspace-write`; Grok uses tool allowlists and `--sandbox strict|normal`.

## Repository layout

```
goal0-node/
├── codex/                  # Codex executor (codex-seed v0.2.0)
│   ├── bin/codex-seed
│   ├── src/codex_openai_seed/
│   ├── schemas/
│   └── tasks/examples/
├── grok/                   # Grok executor (grok-seed v0.2.0)
│   ├── bin/grok-seed
│   ├── src/grok_xai_seed/
│   ├── schemas/
│   └── tasks/examples/
├── policies/               # Per-executor policies + bundle manifest
├── tools/                  # Control plane (signing, verification, launch)
│   ├── wop_lib.py
│   ├── wop-sign / wop-verify / wop-receipt-verify
│   ├── baseline-regression.sh
│   └── grok-governed-launch.sh
├── bootstrap/              # Consent-first genesis bootstrap
│   └── genesis.py
├── docs/                   # Shared architecture and operator docs
├── identity/               # Public trust material (private key gitignored)
├── receipts/baseline/      # Published genesis receipt
├── seeds/                  # Seed artifacts (hashed at genesis)
└── evidence/               # Baseline receipt lanes (not runtime noise)
    ├── codex_hardening_v1/
    └── grok_hardening_v1/
```

**Tracked trust and baseline material:**

- `identity/public/` — node Ed25519 public key
- `identity/node_trust_anchor_manifest.v1.json` — published trust anchor (repo-relative paths)
- `receipts/baseline/genesis_000.json` — signed genesis receipt baseline

**Local node only** (gitignored):

- `identity/private/` — node Ed25519 signing key
- `receipts/<run_id>/` — per-run governance receipt archive (except `receipts/baseline/`)
- Other `evidence/*` lanes from live runs

## Governed pipeline

Each executor follows the same CLI contract:

```bash
# 1. Compute intent hash for operator approval binding
*-seed intent-hash --task <task.json>

# 2. Validate task against policy
*-seed validate --task <task.json> --out <verdict.json>

# 3. Render argv plan (no execution)
*-seed render --task <task.json> --verdict <verdict.json> --out <plan.json>

# 4. Execute (bound — requires --task and --verdict)
*-seed run --plan <plan.json> --task <task.json> --verdict <verdict.json> --out <evidence.json>

# 5. Seal signed receipt
*-seed seal --task ... --verdict ... --plan ... --run ... --receipt <receipt.json>

# 6. Verify (strict by default)
*-seed verify --receipt <receipt.json> --strict
```

### Codex example (dry-run)

```bash
cd /home/ops/witnessops-node

TASK=codex/tasks/examples/summarize_repo.json
EVID=evidence/my_run

codex/bin/codex-seed validate  --task "$TASK" --out "$EVID/verdict.json"
codex/bin/codex-seed render    --task "$TASK" --verdict "$EVID/verdict.json" --out "$EVID/plan.json"
codex/bin/codex-seed run       --plan "$EVID/plan.json" --task "$TASK" --verdict "$EVID/verdict.json" \
                               --out "$EVID/evidence.json" --dry-run
codex/bin/codex-seed seal      --task "$TASK" --verdict "$EVID/verdict.json" --plan "$EVID/plan.json" \
                               --run "$EVID/evidence.json" --receipt "$EVID/receipt.json"
codex/bin/codex-seed verify    --receipt "$EVID/receipt.json" --strict
```

### Grok example (dry-run)

```bash
TASK=grok/tasks/examples/summarize_repo.json
EVID=evidence/my_run

grok/bin/grok-seed validate  --task "$TASK" --out "$EVID/verdict.json"
grok/bin/grok-seed render    --task "$TASK" --verdict "$EVID/verdict.json" --out "$EVID/plan.json"
grok/bin/grok-seed run       --plan "$EVID/plan.json" --task "$TASK" --verdict "$EVID/verdict.json" \
                             --out "$EVID/evidence.json" --dry-run
grok/bin/grok-seed seal      --task "$TASK" --verdict "$EVID/verdict.json" --plan "$EVID/plan.json" \
                             --run "$EVID/evidence.json" --receipt "$EVID/receipt.json"
grok/bin/grok-seed verify    --receipt "$EVID/receipt.json" --strict
```

## Operator tooling

| Tool | Purpose |
|---|---|
| `wop-sign` | Sign canonical JSON payloads with node key |
| `wop-verify` | Verify Ed25519 signatures |
| `wop-receipt-verify` | External receipt verification (includes `receipt_hash` in payload) |
| `wop-hash` / `wop-canonical-json` | Hashing and canonicalization helpers |
| `grok-governed-launch.sh` | Operator launch wrapper for interactive Grok (requires prior `grok login`) |

Receipts from `*-seed seal` auto-sign with the node key when `identity/private/node_ed25519.pem` is present. The signing library (`wop_lib.py`) supports OpenSSH-format Ed25519 keys.

## Hardening (v0.2.0)

Both executors share the same hardening baseline:

1. **Lineage** — task ↔ verdict ↔ plan ↔ evidence hash binding
2. **Operator intent** — `intent_hash` must match `operator_intent_hash(task)`
3. **Argv guards** — policy-denied flags blocked before subprocess
4. **Output redaction** — secrets scanned/redacted in stdout/stderr
5. **Integrity** — `target_repo` must exist; `expected_root_markers` checked

Baseline evidence lanes under `evidence/codex_hardening_v1/` and `evidence/grok_hardening_v1/` demonstrate dry-run pipelines with signed receipts and strict verify pass.

## Goal-0 scope

- **Phone** runs the Goal-0 service and captures operational receipts.
- **Debian node** (this repo) holds both executors, policies, and verification tooling.
- **Promotion** requires verifier pass plus operator review — see [promotion checklist](docs/operators.md#promotion-checklist). Executor receipts are claims of governed execution, not proof of correctness, merge, or deployment.

## Documentation

| Doc | Contents |
|---|---|
| [docs/PUBLIC_DEMO.md](docs/PUBLIC_DEMO.md) | Public demo boundaries, baseline verification, publication status |
| [docs/architecture.md](docs/architecture.md) | Dual-executor model, five layers, promotion rules |
| [docs/bootstrap.md](docs/bootstrap.md) | Genesis bootstrap (`bootstrap/genesis.py`) |
| [docs/operators.md](docs/operators.md) | Task workflow, verifier split, [promotion checklist](docs/operators.md#promotion-checklist) |
| [docs/receipts.md](docs/receipts.md) | Receipt structure, lineage, verification tools |
| [SECURITY.md](SECURITY.md) | Security policy and reporting boundaries |

## License

Apache 2.0 — see [LICENSE](LICENSE).
# Public claim matrix (v1)

Maps what goal0-node **can** and **cannot** support as public proof. Use with [GOLDEN_VERIFY_TRANSCRIPT.v1.txt](GOLDEN_VERIFY_TRANSCRIPT.v1.txt) and [operators.md](../operators.md#promotion-checklist).

| Claim | Supported? | Evidence | Verifier / gate |
|---|---|---|---|
| Governed pipeline shape exists (validate→render→run→seal→verify) | Yes | `codex/`, `grok/`, docs | Inspect repo |
| Executors are policy-gated, not free agents | Yes | README, architecture | Docs |
| Genesis baseline receipt published | Yes | `receipts/baseline/genesis_000.json` | `wop-receipt-verify`, `wop-verify` |
| Executor baseline receipts verify strict | Yes | `evidence/*_hardening_v1/` | `*-seed verify --strict` |
| Public baseline file hashes stable | Yes | `PUBLIC_BASELINE_MANIFEST.sha256` | `sha256sum -c` |
| CI regression on `main` | Yes (when Actions enabled) | GitHub Actions run on commit | Workflow `Baseline regression` |
| Codex baseline was live CLI execution | **No** | `transport: dry_run` | D review |
| Grok baseline proves no defects | **No** | receipt `claim.boundary` | D review |
| Receipt proves merge safe | **No** | architecture, operators | Promotion E |
| Receipt proves deploy authorized | **No** | operators E | Human gate |
| Repo is production authority / public signer | **No** | SECURITY.md, PUBLIC_DEMO.md | Policy |
| Repo accepts secret ingest | **No** | SECURITY.md | Policy |
| Autonomous executor | **No** | architecture | Policy |
| Bounded RFC Editor humor lookup (demo) | **Planned** | RFC_LOOKUP_DEMO.v1 task specimens | Future evidence lane + C+D |
| Unrestricted “find anything funny” web browse | **No** | SECURITY.md, demo boundary | Policy |

## Status tags (public wording)

```
PUBLIC_DEMO_READY
NOT_FULL_LAUNCH_READY
NOT_PRODUCTION_AUTHORITY
GITHUB_CI_OBSERVED_PASS_ON_05203ed
LOCAL_REGRESSION_REPORTED_PASS
```

Update CI tag when inspecting a newer commit: `gh run list -R witnessops/goal0-node --commit <sha>`.
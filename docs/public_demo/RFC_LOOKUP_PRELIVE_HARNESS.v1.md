# RFC lookup demo — pre-live harness (v1)

**Lane:** `GOAL0_NODE_RFC_LOOKUP_DEMO_PRELIVE_HARNESS_V1`  
**Status:** pre-live harness sealed (spec + verifier; **no live browse yet**)  
**Authority:** operator-approved bounded lookup — not production browsing

## Purpose

Close the gap between **prompt-level allowlist** (task specimens) and an **enforceable operator harness boundary** before the first live run (`GOAL0_NODE_PUBLIC_DEMO_RFC_LOOKUP_LIVE_RUN_V1`).

This lane is **docs + verifier only**. It does not record evidence, promote to baseline, or claim production computer-use readiness.

## Classification (this lane)

| Tag | Status |
|---|---|
| `RFC_LOOKUP_DEMO_PUBLIC_DESIGN` | PASS (prior lane `e5509c3`) |
| `TASK_SPECIMENS_PRESENT` | PASS |
| `PRELIVE_HARNESS_SPEC` | PASS (this document) |
| `PRELIVE_VERIFIER_CHECKLIST` | PASS (`tools/rfc-lookup-demo-verify.sh`) |
| `LIVE_EVIDENCE_LANE` | **HOLD** |
| `PUBLIC_PROMOTION` | **HOLD** |
| `GITHUB_CI_EVIDENCE` | NOT_OBSERVED until evidence commit + workflow run |

## Harness model

The **operator harness** is outside the repo: an isolated browser or computer-use VM the sovereign configures before approving a live Codex lookup. The repo documents requirements; the operator enforces them at runtime.

```
┌─────────────────┐     validate/render      ┌──────────────────┐
│  Task specimen  │ ───────────────────────► │  codex-seed      │
│  (intent hash)  │                          │  (repo policy)   │
└─────────────────┘                          └────────┬─────────┘
                                                      │ run (live)
                                                      ▼
┌─────────────────┐     allowlisted only     ┌──────────────────┐
│  Operator       │ ◄── domain + URL pin ─── │  Browser /       │
│  sovereign      │     screenshot capture   │  computer-use VM │
└─────────────────┘                          └──────────────────┘
```

**Grok** remains requester/reviewer only (`disable_web_search: true`, read/grep/list tools). **Codex** performs the bounded lookup under harness constraints below.

## Allowed domains (exact)

Only these hostnames may be contacted by the browser harness:

| Hostname | Role |
|---|---|
| `www.rfc-editor.org` | Primary allowlisted origin |
| `rfc-editor.org` | Redirect to `www` only — no other paths |

**Forbidden:** all other domains, including search engines, CDNs not required for RFC Editor page load, social media, paste sites, and arbitrary redirects off `rfc-editor.org`.

## Allowed URL paths (exact)

Navigation is limited to this closed set (HTTPS only):

| URL | RFC |
|---|---|
| `https://www.rfc-editor.org/info/rfc2324` | 2324 — Hyper Text Coffee Pot Control Protocol |
| `https://www.rfc-editor.org/info/rfc1149` | 1149 — IP Datagrams on Avian Carriers |
| `https://www.rfc-editor.org/info/rfc2549` | 2549 — IP over Avian Carriers with QoS |

The task specimen binds these URLs in prompt context so `intent_hash` covers the lookup set. The harness must **not** follow in-page links to other RFCs, external sites, or download endpoints unless the operator has pre-approved an equivalent read-only `info/rfc####` path (out of scope for v1).

## Forbidden browser / computer-use actions

| Category | Forbidden |
|---|---|
| Authentication | Login, signup, OAuth, API keys, password fields |
| Data exfiltration | Form submit to non-allowlisted origins, clipboard paste of secrets |
| Acquisition | Downloads, purchases, subscriptions, file uploads |
| Navigation | New tabs/windows to non-allowlisted domains, `javascript:` / `data:` URLs |
| Repo / node | Any write to `witnessops-node`, git mutation, shell outside harness |
| Scope expansion | Search for “funny RFC”, social media, arbitrary humor sources |
| Persistence | Saving cookies/session tokens to shared storage without redaction policy |

**Operator may:** dismiss local-only cookie banners on RFC Editor if required to render pages; record that action in `harness_manifest.v1.json` notes (no PII).

## Evidence capture format (pre-live spec)

When the live run lane is approved, artifacts under `evidence/rfc_lookup_demo_v1/` (gitignored until promoted) must include:

| Artifact | Required | Contents |
|---|---|---|
| `harness_manifest.v1.json` | Yes | Harness id, allowed domains/URLs, operator, timestamps, redaction policy version |
| `lookup_output.json` | Yes | Structured result — schema: [examples/rfc_lookup_output.schema.v1.json](examples/rfc_lookup_output.schema.v1.json) |
| `browser_session_log.jsonl` | Yes | Timestamped navigation events (URLs, action types); secrets redacted |
| `screenshots/` | Recommended | One PNG per allowlisted URL after load; filenames `rfc2324.png`, `rfc1149.png`, `rfc2549.png` |
| `screenshots/SHA256SUMS` | If screenshots | Hashes of PNG files |
| Codex pipeline | Yes | `codex_verdict.json`, `plan.json`, `evidence.json`, `receipt.json` |
| Grok pipeline | Yes | Request + review lanes per [RFC_LOOKUP_DEMO.v1.md](RFC_LOOKUP_DEMO.v1.md) |
| `operator_attestation.v1.json` | Before promote | C+D attestation per [operators.md](../operators.md) |

### `harness_manifest.v1.json` (minimum fields)

```json
{
  "schema": "witnessops.rfc_lookup_harness_manifest.v1",
  "harness_id": "rfc_lookup_demo_v1",
  "recorded_at": "ISO-8601",
  "recorded_by": "sovereign",
  "allowed_domains": ["www.rfc-editor.org", "rfc-editor.org"],
  "allowed_urls": [
    "https://www.rfc-editor.org/info/rfc2324",
    "https://www.rfc-editor.org/info/rfc1149",
    "https://www.rfc-editor.org/info/rfc2549"
  ],
  "harness_type": "isolated_browser_vm",
  "redaction_policy": "RFC_LOOKUP_SCREENSHOT_REDACTION.v1",
  "forbidden_actions_acknowledged": true,
  "live_browse": false
}
```

Set `live_browse: true` only during the live run lane. Pre-live commits keep `live_browse: false` or omit the manifest entirely.

## Screenshot and redaction policy

**Policy id:** `RFC_LOOKUP_SCREENSHOT_REDACTION.v1`

| Keep visible | Redact or crop |
|---|---|
| URL bar showing `www.rfc-editor.org/info/rfc####` | Operator username, hostname, IP beyond loopback |
| RFC number and official title on page | Session cookies, auth tokens, extension UI |
| Page body sufficient to show official standard text | Local file paths, SSH keys, chat notifications |
| Timestamp in manifest (not necessarily on image) | Email addresses, phone numbers, API keys |

Store redacted PNGs only. If redaction cannot be applied safely, omit the screenshot and note `screenshots: withheld` in the harness manifest with reason.

## Receipt required fields (live run)

Executor receipt (`vaultsovereign.codex.receipt.v1`) for this demo must include standard lineage **plus** D-review fields inspectable from `execution_evidence`:

| Field / path | Requirement |
|---|---|
| `claim.transport` | Live Codex execution (not `dry_run`) |
| `claim.boundary` | Unchanged disclaimer — no correctness / merge / deploy proof |
| `authority.operator_intent_hash` | Matches [codex task specimen](examples/codex_task_rfc_editor_lookup.v1.json) |
| `evidence.task_hash` | Binds allowlisted URLs in task prompt |
| `evidence_paths.execution_evidence` | Points to `evidence.json` with stdout containing or referencing `lookup_output.json` |
| `execution_evidence.return_code` | Reviewed in D — `0` ≠ humor correctness |
| `execution_evidence.git.diff_bytes` | Expect `0` (`sandbox: read-only`) |
| Harness cross-ref | `harness_manifest.v1.json` hash recorded in attestation or evidence notes |

Verifier: `codex-seed verify --receipt … --strict` must report `decision: pass` before C+D.

## Verifier checklist (source URLs + output JSON)

### Automated (pre-live + post-run)

```bash
# Pre-live: task specimens still validate
codex/bin/codex-seed validate \
  --task docs/public_demo/examples/codex_task_rfc_editor_lookup.v1.json \
  --out /tmp/rfc_codex_verdict.json
grok/bin/grok-seed validate \
  --task docs/public_demo/examples/grok_task_rfc_humor_request.v1.json \
  --out /tmp/rfc_grok_verdict.json

# Pre-live or post-run: bounded output + URLs
tools/rfc-lookup-demo-verify.sh docs/public_demo/examples/rfc_lookup_output.golden.v1.json
# Post-run (when evidence exists):
tools/rfc-lookup-demo-verify.sh evidence/rfc_lookup_demo_v1/lookup_output.json
```

### Manual checklist (operator / reviewer)

| # | Check | Pass criterion |
|---|---|---|
| 1 | Task intent | `codex-seed intent-hash` matches specimen `operator_approval.intent_hash` |
| 2 | URL allowlist | Every `source_urls[]` entry is exactly one of the three allowlisted URLs |
| 3 | Winner RFC | `winner_rfc` ∈ `{2324, 1149, 2549}` |
| 4 | Boundary field | `boundary` equals `cited RFC Editor pages only` (or equivalent scoped wording) |
| 5 | Harness manifest | `allowed_urls` matches table above; `live_browse` true only on live run |
| 6 | No extra domains | `browser_session_log.jsonl` contains no non-allowlisted hostnames |
| 7 | Receipt strict | `codex-seed verify --strict` → `decision: pass` |
| 8 | Claim scope | No stdout claim of unrestricted browse, production readiness, or humor truth |

## Implementation gap table (updated)

| Piece | Status |
|---|---|
| Grok requester task specimen | Ready |
| Codex lookup task specimen | Ready |
| Pre-live harness spec | **Ready** (this document) |
| Output JSON schema + verifier script | **Ready** |
| Domain allowlist in `codex-seed` policy | **Not yet** — harness + task prompt until policy patch |
| Computer-use / isolated browser VM | **Operator harness** — configure per this spec |
| Recorded evidence lane | **Not yet** — `GOAL0_NODE_PUBLIC_DEMO_RFC_LOOKUP_LIVE_RUN_V1` |
| Public promotion | **Hold** until receipt + C+D + optional CI on evidence commit |

## Forbidden in this lane

- No live browse or recorded browser session in repo commits
- No new tracked evidence under `evidence/rfc_lookup_demo_v1/` until live run approval
- No production computer-use or unrestricted web claims
- No `codex-seed` policy code change required for sealing (optional follow-up)

## Next lane exit condition

`GOAL0_NODE_PUBLIC_DEMO_RFC_LOOKUP_LIVE_RUN_V1`:

```
validate → render → run → seal → verify
```

Plus C+D attestation, intentional promote of `evidence/rfc_lookup_demo_v1`, optional CI replay.

## Related

- [RFC_LOOKUP_DEMO.v1.md](RFC_LOOKUP_DEMO.v1.md) — demo script and claim boundary
- [CLAIM_MATRIX.v1.md](CLAIM_MATRIX.v1.md) — public proof map
- [operators.md](../operators.md#promotion-checklist) — C+D and Hold → Promote
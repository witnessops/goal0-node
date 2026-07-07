# RFC lookup demo — “Two agents walk into a standards body” (v1)

**Lane:** `GOAL0_NODE_PUBLIC_DEMO_RFC_LOOKUP_V1`  
**Status:** design + task specimens (not a recorded evidence lane yet)  
**Authority:** operator-approved bounded lookup — not production browsing

## Why this demo works

The joke is **deterministic and bounded**:

- Grok does **not** browse “anything funny.”
- Codex does **not** roam the open web.
- Allowlisted source: **RFC Editor** only (`rfc-editor.org`).
- Deterministic targets: **RFC 2324**, **RFC 1149**, **RFC 2549**.

**Punchline:** the funniest thing lives inside official infrastructure (coffee-pot protocol, pigeon IP), not random internet noise.

**WitnessOps angle:** Grok = requester/reviewer · Codex = bounded operator · WitnessOps = receipts.

## Safe public wording

> Codex used an allowlisted browser/computer-use harness for a bounded lookup.

OpenAI documents Computer use as UI operation via screenshots and actions (clicks, typing, scroll), with recommendations for isolated browser/VM, domain/action allowlists, and human-in-the-loop. Codex CLI supports local agent workflows including web search. **This repo does not claim** unrestricted browsing or autonomous production computer-use — only governed, allowlisted lookup recorded in receipts.

## Funny targets (official)

| RFC | Title | Why it’s funny |
|---|---|---|
| **2324** (pick) | Hyper Text Coffee Pot Control Protocol | Defines **418 I'm a teapot**; coffee-pot control as HTTP |
| 1149 | A Standard for the Transmission of IP Datagrams on Avian Carriers | Pigeon-based IP; high delay, low throughput |
| 2549 | IP over Avian Carriers with QoS | QoS extensions; carrier pigeons with frequent-flyer miles |

## Demo script (7 scenes)

**Title:** Two agents walk into a standards body.

### Scene 1 — Grok request

> Codex, find the funniest official-looking internet standard.  
> Boundary: only RFC Editor. No social media. No login. No arbitrary web.

Task specimen: [examples/grok_task_rfc_humor_request.v1.json](examples/grok_task_rfc_humor_request.v1.json)

### Scene 2 — WitnessOps gate

| Field | Value |
|---|---|
| Intent | `humorous_public_lookup` |
| Policy | `allowlisted_browser_readonly` |
| Allowed domains | `rfc-editor.org` |
| Forbidden | login, forms, downloads, purchases, secrets, repo mutation |

```
validate → render → run → seal → verify
```

### Scene 3 — Codex lookup

Codex opens RFC Editor (allowlisted harness) and inspects bounded URLs:

- `https://www.rfc-editor.org/info/rfc2324`
- `https://www.rfc-editor.org/info/rfc1149`
- `https://www.rfc-editor.org/info/rfc2549`

Task specimen: [examples/codex_task_rfc_editor_lookup.v1.json](examples/codex_task_rfc_editor_lookup.v1.json)  
(`web_search: true`, `allow_web_search: true`, `sandbox: read-only`)

### Scene 4 — Codex result

> Official internet culture contains a coffee-pot protocol and pigeon-based IP networking.

Structured JSON output with `winner_rfc`, `title`, `source_urls`, `boundary`.

### Scene 5 — Grok review

> RFC 2324 wins because **418 I'm a teapot** is both absurd and operationally classified.

Grok reviews Codex evidence + receipt (second lane, read-only tools).

### Scene 6 — WitnessOps proof

Receipt records:

- task hash
- policy verdict (`allow`)
- allowlisted domain / source URLs
- captured output hash
- verifier `decision: pass`

### Scene 7 — Punchline

> The joke is funny.  
> The proof is not.

## On-screen claim boundary (video / public)

```
This demo proves a bounded governed lookup was classified, allowed, recorded, and verified.

It does not prove:
- autonomous production browsing
- unrestricted web access
- source truth beyond cited pages
- correctness of humor
- production readiness
```

## Implementation notes (goal0-node today)

| Piece | Status |
|---|---|
| Grok requester task specimen | Ready (`validate` passes) |
| Codex lookup task specimen | Ready (`validate` passes with `web_search`) |
| Domain allowlist in `codex-seed` policy | **Not yet** — prompt + operator harness bound URLs |
| Computer-use / isolated browser VM | **Operator harness** — outside repo; document in evidence |
| Recorded evidence lane | **Not yet** — run pipeline after operator approval |
| Public promotion | **Hold** until receipt + C+D + CI on evidence commit |

**Do not** let the model choose arbitrary humor sources. **Do** keep RFC numbers and URLs in the task body so intent hash binds the lookup set.

## Operator runbook (when approved)

```bash
GROK_TASK=docs/public_demo/examples/grok_task_rfc_humor_request.v1.json
CODEX_TASK=docs/public_demo/examples/codex_task_rfc_editor_lookup.v1.json
EVID=evidence/rfc_lookup_demo_v1   # gitignored until promoted to baseline

# 1. Grok lane brief (requester)
grok/bin/grok-seed validate --task "$GROK_TASK" --out "$EVID/grok_verdict.json"
# ... render → run → seal → verify (read-only, no web)

# 2. Codex bounded lookup (operator harness: RFC Editor only)
codex/bin/codex-seed validate --task "$CODEX_TASK" --out "$EVID/codex_verdict.json"
# ... render → run (live, allowlisted browser) → seal → verify

# 3. Grok review of Codex receipt (read-only)
# 4. C+D attestation + narrow promote_scope
```

## Related

- [CLAIM_MATRIX.v1.md](CLAIM_MATRIX.v1.md)
- [operators.md](../operators.md#promotion-checklist)
- [SECURITY.md](../../SECURITY.md)
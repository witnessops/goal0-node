# Public demo boundaries

**Classification:** `PUBLIC_DEMO_READY` (post hardening patch v1)  
**Not:** full production launch-ready

This repository is a **public architecture and reference demo** for WitnessOps governed execution on a Goal-0 node. Inspectors can read policies, verifiers, baseline evidence, and operator gates without access to private node keys or live runtime receipts.

## What this repo is

| Property | Description |
|---|---|
| **Purpose** | Reference implementation of dual-executor (Codex + Grok) governed pipelines |
| **Proof model** | Signed receipts + strict verifiers; human promotion gates |
| **License** | Apache 2.0 |
| **Baseline evidence** | Tracked dry-run (codex) and read-only recon (grok) lanes with operator attestations |

## What this repo is not

- A production authority surface or public signer
- A secret-ingest path or remote shell service
- Proof of correctness, merge safety, deployment authorization, or absence of defects
- A claim that executors are autonomous agents (they are policy-gated)

Receipt and architecture docs state these boundaries explicitly. See [architecture.md](architecture.md) and [operators.md](operators.md#promotion-checklist).

## Publication inspection (v1)

| Check | Status |
|---|---|
| Public repo inspectable | Pass |
| README + architecture + receipts docs | Pass |
| Apache 2.0 license | Pass |
| Private keys gitignored | Pass |
| Genesis baseline receipt | Pass |
| SECURITY.md | Pass (patch v1) |
| Trust-anchor repo metadata | Pass (relocation recorded) |
| Public baseline manifest (repo-relative) | Pass (patch v1) |

**Prior gaps (resolved in patch v1):** missing SECURITY.md; trust-anchor listed old org/repo; genesis sidecar exposed node-local absolute path without a public alternative.

## Public baseline verification

**Repo-relative manifest (recommended for public consumers):**

```bash
sha256sum -c receipts/baseline/PUBLIC_BASELINE_MANIFEST.sha256
```

**Genesis receipt + signature (on-node or CI):**

```bash
tools/wop-receipt-verify receipts/baseline/genesis_000.json \
  --sidecar receipts/baseline/genesis_000.json.sha256 \
  --require-schema witnessops.genesis_receipt.v1 \
  --verify-signature \
  --public-key identity/public/node_ed25519.pub.pem
```

The historical genesis sidecar retains an absolute issuance path from the original node bootstrap. Do not rewrite it if verifiers depend on it. Use `PUBLIC_BASELINE_MANIFEST.sha256` for clean public presentation.

## Trust anchor relocation

Public repository moved from `VaultSovereign/goal0-node` to `witnessops/goal0-node`. Lineage: [receipts/baseline/TRUST_ANCHOR_PUBLIC_REPO_RELOCATION_V1.md](../receipts/baseline/TRUST_ANCHOR_PUBLIC_REPO_RELOCATION_V1.md).

Genesis receipt remains the signed historical anchor; only descriptive manifest metadata was updated.

## Operator promotion vs public demo

- **Verifier pass** → eligible for promotion review  
- **Promote** → requires applicable A–E checks and upstream authority ([Hold → Promote](operators.md#moving-from-hold-to-promote))  
- **Public demo traffic** → read docs, run verifiers on baselines, do not treat as production deploy signal

Baseline operator attestations for `codex_hardening_v1` and `grok_hardening_v1` remain `hold` until E gates and upstream authority complete.

## Security

See [SECURITY.md](../SECURITY.md). Report sensitive issues through private maintainer contact, not public issues.

## Related docs

| Doc | Contents |
|---|---|
| [architecture.md](architecture.md) | Five layers, receipt boundaries |
| [operators.md](operators.md) | Task workflow, promotion checklist |
| [receipts.md](receipts.md) | Verifier split (genesis vs executor) |
| [bootstrap.md](bootstrap.md) | Consent-first genesis |
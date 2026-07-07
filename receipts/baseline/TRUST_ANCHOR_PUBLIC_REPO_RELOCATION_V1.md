# Trust anchor public repo relocation (v1)

**Recorded:** 2026-07-07  
**Classification:** `GOAL0_NODE_PUBLIC_DEMO_HARDENING_PATCH_V1`  
**Authority:** operator-approved repo metadata correction (not a genesis re-sign)

## Summary

The published trust-anchor manifest listed the GitHub repository as `VaultSovereign/goal0-node`. The public demo repository is now `witnessops/goal0-node`.

This note records the relocation for public consumers. It does **not** rewrite the signed genesis baseline receipt.

## What changed

| Field | Before | After |
|---|---|---|
| `identity/node_trust_anchor_manifest.v1.json` → `repo` | `VaultSovereign/goal0-node` | `witnessops/goal0-node` |
| `policies/policy_bundle_manifest.v1.json` → `source_repo` | `VaultSovereign/goal0-node` | `witnessops/goal0-node` |

## What did not change

- `receipts/baseline/genesis_000.json` — signed historical payload unchanged
- `receipts/baseline/genesis_000.json.sha256` — retained (historical sidecar with node-local path)
- `identity/public/node_ed25519.pub.pem` — unchanged
- Genesis receipt hash: `sha256:350d7a309ed66c6fd608f3a179576133b3b9f0414301d3404150fde2a24c90a5`

## Rationale

The `repo` and `source_repo` fields are descriptive publication metadata in the trust-anchor and policy-bundle manifests. They are not bound into the genesis signed payload. Updating them aligns public documentation with the inspectable repository location without invalidating genesis verification.

## Public verification

For repo-relative baseline hashes, use:

```bash
cat receipts/baseline/PUBLIC_BASELINE_MANIFEST.sha256
sha256sum -c receipts/baseline/PUBLIC_BASELINE_MANIFEST.sha256
```

Genesis sidecar verification on the node continues to use `receipts/baseline/genesis_000.json.sha256` with `wop-receipt-verify`.

## Boundary

This relocation note does not claim production readiness, ownership transfer, or third-party publication authority. See [docs/PUBLIC_DEMO.md](../docs/PUBLIC_DEMO.md).
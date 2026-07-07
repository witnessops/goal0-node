# Node identity

Public trust material for the Debian execution node. Private signing material stays on-node only.

## Tracked (this repo)

| Path | Purpose |
|---|---|
| `public/node_ed25519.pub.pem` | Node Ed25519 public key (OpenSSH format) |
| `node_trust_anchor_manifest.v1.json` | Published trust anchor with repo-relative paths |

## Local only (gitignored)

| Path | Purpose |
|---|---|
| `private/node_ed25519.pem` | Node signing key — never commit |

Executor receipts (`*-seed seal`) and the genesis baseline receipt sign with the private key when present on the node.
# Bootstrap

WitnessOps nodes begin with a **consent-first genesis bootstrap** that records hash-only custody evidence without network access or credential collection.

## Genesis script

`bootstrap/genesis.py` creates:

- `evidence/<run_id>/` — consent event, hardware baseline (hashed), seed/private/bootstrap file hashes
- `receipts/<run_id>/genesis_000.json` — unsigned genesis receipt + SHA-256 sidecar

Hardware identifiers are never stored raw. Only `sha256:` hash references are recorded.

## Running genesis

```bash
cd /home/ops/witnessops-node

# Interactive consent (type GENESIS at prompt)
python3 bootstrap/genesis.py

# Non-interactive (automation only on owned/authorized devices)
WOPGENESIS_CONSENT=GENESIS python3 bootstrap/genesis.py --root /home/ops/witnessops-node
```

The script creates `evidence/`, `receipts/`, `private/`, and `seeds/` if missing.

## Post-genesis steps (node deployment)

After genesis on a Debian execution node:

1. **Identity** — generate node Ed25519 keypair (`identity/private/`, `identity/public/`)
2. **Sign genesis receipt** — use `wop-sign` or `*-seed seal` patterns
3. **Install policies** — deploy `policies/` bundle, verify manifest hashes
4. **Deploy executors** — `codex/` and `grok/` runtimes (this repo)
5. **Operator tooling** — `tools/wop_*` scripts on PATH
6. **Baseline evidence** — run dry-run lanes under `evidence/codex_hardening_v1/` and `evidence/grok_hardening_v1/`

## Privacy boundaries

| Collected | Not collected |
|---|---|
| Platform, Python version | API keys, tokens |
| Hashed hostname, username | Raw serial numbers |
| File hashes under seeds/private/bootstrap | File contents from private/ |

## Claim boundary

Genesis proves **local starting custody artifact hashes** at bootstrap time. It does not prove device ownership, external execution, or third-party publication.
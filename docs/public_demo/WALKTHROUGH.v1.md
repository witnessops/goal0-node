# Public demo walkthrough (v1)

**Lane:** `GOAL0_NODE_PUBLIC_DEMO_EVIDENCE_PROMOTION_V1`  
**Authority:** read-only / docs-only  
**Time:** ~10 minutes from clean clone

## 1. Clone and orient

```bash
git clone https://github.com/witnessops/goal0-node.git
cd goal0-node
```

Read first:

- [README.md](../../README.md) — dual-executor frame
- [docs/PUBLIC_DEMO.md](../PUBLIC_DEMO.md) — boundaries
- [SECURITY.md](../../SECURITY.md) — reporting limits

## 2. Public baseline integrity

```bash
sha256sum -c receipts/baseline/PUBLIC_BASELINE_MANIFEST.sha256
```

Expect three `OK` lines. See [GOLDEN_VERIFY_TRANSCRIPT.v1.txt](GOLDEN_VERIFY_TRANSCRIPT.v1.txt).

## 3. Trust anchor and relocation

```bash
cat identity/node_trust_anchor_manifest.v1.json | python3 -m json.tool | head -20
cat receipts/baseline/TRUST_ANCHOR_PUBLIC_REPO_RELOCATION_V1.md
```

Confirm `repo` is `witnessops/goal0-node`. Genesis receipt is **not** rewritten.

## 4. Verifier split (do not cross families)

| Receipt | Verifier |
|---|---|
| `receipts/baseline/genesis_000.json` | `wop-receipt-verify`, `wop-verify` |
| `evidence/codex_hardening_v1/receipt.json` | `codex-seed verify --strict` |
| `evidence/grok_hardening_v1/*.receipt.json` | `grok-seed verify --strict` |

Detail: [docs/receipts.md](../receipts.md#verifier-split). Anti-pattern: [KNOWN_BAD_VERIFY_TRANSCRIPT.v1.txt](KNOWN_BAD_VERIFY_TRANSCRIPT.v1.txt).

## 5. Full baseline regression (optional, requires Python deps)

```bash
python3 -m pip install cryptography pynacl pydantic rich typer
tools/baseline-regression.sh
```

Expect `summary: 4 passed, 0 failed`. Or inspect GitHub Actions **Baseline regression** on your commit.

## 6. Operator attestations (human gates)

```bash
cat evidence/codex_hardening_v1/operator_attestation.v1.json | python3 -m json.tool | head -30
cat evidence/grok_hardening_v1/operator_attestation.v1.json | python3 -m json.tool | head -30
```

Both should show `promotion_outcome: hold` with narrow `promote_scope`. Promote requires [Hold → Promote](../operators.md#moving-from-hold-to-promote).

## 7. Claim discipline

Use [CLAIM_MATRIX.v1.md](CLAIM_MATRIX.v1.md) before citing this repo publicly. Demo as **architecture + reference implementation**, not launch.
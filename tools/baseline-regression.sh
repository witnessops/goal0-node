#!/usr/bin/env bash
# Promotion checklist F: reproduce all tracked baseline verifiers.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

export PATH="${HOME}/.grok/bin:${HOME}/.local/bin:${ROOT}/codex/bin:${ROOT}/grok/bin:/usr/bin:/bin"
export PYTHONPATH="${ROOT}/codex/src:${ROOT}/grok/src${PYTHONPATH:+:${PYTHONPATH}}"

CODEX_RECEIPT="evidence/codex_hardening_v1/receipt.json"
GROK_RECEIPT="evidence/grok_hardening_v1/grok_task_summarize_repo_001.receipt.json"
GENESIS_RECEIPT="receipts/baseline/genesis_000.json"
GENESIS_SIDECAR="receipts/baseline/genesis_000.json.sha256"

failures=0
passed=0

run_step() {
  local name="$1"
  shift
  echo ""
  echo "==> ${name}"
  if "$@"; then
    echo "    PASS"
    passed=$((passed + 1))
  else
    echo "    FAIL (exit $?)"
    failures=$((failures + 1))
  fi
}

echo "baseline-regression: ${ROOT}"
echo "running 4 baseline verifiers (operators.md checklist F)"

run_step "codex-seed verify --strict" \
  python3 -m codex_openai_seed.cli verify --receipt "${CODEX_RECEIPT}" --strict

run_step "grok-seed verify --strict" \
  python3 -m grok_xai_seed.cli verify --receipt "${GROK_RECEIPT}" --strict

run_step "wop-receipt-verify (genesis + sidecar + signature)" \
  "${ROOT}/tools/wop-receipt-verify" "${GENESIS_RECEIPT}" \
    --sidecar "${GENESIS_SIDECAR}" \
    --require-schema witnessops.genesis_receipt.v1 \
    --verify-signature

run_step "wop-verify (genesis signature)" \
  "${ROOT}/tools/wop-verify" "${GENESIS_RECEIPT}"

echo ""
echo "summary: ${passed} passed, ${failures} failed"
if [[ "${failures}" -gt 0 ]]; then
  exit 1
fi
echo "baseline regression OK"
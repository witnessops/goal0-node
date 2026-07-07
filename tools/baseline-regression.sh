#!/usr/bin/env bash
# Promotion checklist F: reproduce all tracked baseline verifiers.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

export WOPS_ROOT="${WOPS_ROOT:-${ROOT}}"
export PATH="${HOME}/.grok/bin:${HOME}/.local/bin:${ROOT}/codex/bin:${ROOT}/grok/bin:${PATH:-/usr/bin:/bin}"
export PYTHONPATH="${ROOT}/tools:${ROOT}/codex/src:${ROOT}/grok/src${PYTHONPATH:+:${PYTHONPATH}}"
PYTHON="${PYTHON:-python3}"

CODEX_RECEIPT="evidence/codex_hardening_v1/receipt.json"
GROK_RECEIPT="evidence/grok_hardening_v1/grok_task_summarize_repo_001.receipt.json"
GROK_DIR="evidence/grok_hardening_v1"
GROK_TASK="${GROK_DIR}/grok_task_summarize_repo_001.task.json"
GROK_VERDICT="${GROK_DIR}/grok_task_summarize_repo_001.verdict.json"
GROK_PLAN="${GROK_DIR}/grok_task_summarize_repo_001.plan.json"
GROK_RUN="${GROK_DIR}/grok_task_summarize_repo_001.evidence.json"
GENESIS_RECEIPT="receipts/baseline/genesis_000.json"
GENESIS_SIDECAR="receipts/baseline/genesis_000.json.sha256"
NODE_PUB_KEY="${ROOT}/identity/public/node_ed25519.pub.pem"
RFC_LOOKUP_GOLDEN="docs/public_demo/examples/rfc_lookup_output.golden.v1.json"

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
echo "running 5 baseline verifiers (operators.md checklist F + RFC lookup pre-live)"

run_step "codex-seed verify --strict" \
  "${PYTHON}" -m codex_openai_seed.cli verify \
    --receipt "${CODEX_RECEIPT}" \
    --public-key "${NODE_PUB_KEY}" \
    --strict

run_step "grok-seed verify --strict" \
  "${PYTHON}" -m grok_xai_seed.cli verify \
    --receipt "${GROK_RECEIPT}" \
    --task "${GROK_TASK}" \
    --verdict "${GROK_VERDICT}" \
    --plan "${GROK_PLAN}" \
    --run "${GROK_RUN}" \
    --public-key "${NODE_PUB_KEY}" \
    --strict

run_step "wop-receipt-verify (genesis + sidecar + signature)" \
  "${PYTHON}" "${ROOT}/tools/wop-receipt-verify" "${GENESIS_RECEIPT}" \
    --sidecar "${GENESIS_SIDECAR}" \
    --require-schema witnessops.genesis_receipt.v1 \
    --verify-signature \
    --public-key "${NODE_PUB_KEY}"

run_step "wop-verify (genesis signature)" \
  "${PYTHON}" "${ROOT}/tools/wop-verify" "${GENESIS_RECEIPT}" \
    --public-key "${NODE_PUB_KEY}"

run_step "rfc-lookup-demo-verify (pre-live golden output)" \
  bash "${ROOT}/tools/rfc-lookup-demo-verify.sh" "${RFC_LOOKUP_GOLDEN}"

echo ""
echo "summary: ${passed} passed, ${failures} failed"
if [[ "${failures}" -gt 0 ]]; then
  exit 1
fi
echo "baseline regression OK"
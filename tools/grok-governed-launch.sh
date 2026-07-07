#!/usr/bin/env bash
set -euo pipefail

# WitnessOps operator launch helper for Grok CLI on debian-codex-node.
# Governed headless tasks use: grok/bin/grok-seed (validate -> render -> run -> seal).
# Auth requires a real TTY: run `grok login` once before interactive use.

export PATH="${HOME}/.grok/bin:${HOME}/.local/bin:/usr/bin:/bin"
export CODEX_HOME="${HOME}/.codex"
export GROK_HOME="${HOME}/.grok"

ROOT="${HOME}/witnessops-node"
cd "${ROOT}"

exec grok --no-alt-screen "$@"
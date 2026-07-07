#!/usr/bin/env bash
# Verifier checklist for RFC lookup demo: allowlisted source_urls + output JSON shape.
# Pre-live: run against examples/rfc_lookup_output.golden.v1.json
# Post-run: run against evidence/rfc_lookup_demo_v1/lookup_output.json
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

ALLOWED_URLS=(
  "https://www.rfc-editor.org/info/rfc2324"
  "https://www.rfc-editor.org/info/rfc1149"
  "https://www.rfc-editor.org/info/rfc2549"
)
ALLOWED_RFCS=("2324" "1149" "2549")
SCHEMA="${ROOT}/docs/public_demo/examples/rfc_lookup_output.schema.v1.json"

usage() {
  echo "usage: $0 <lookup_output.json>" >&2
  echo "  Verifies RFC lookup demo output: winner_rfc, boundary, allowlisted source_urls." >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
INPUT="$1"
[[ -f "${INPUT}" ]] || { echo "error: file not found: ${INPUT}" >&2; exit 1; }

failures=0
passed=0

check() {
  local name="$1"
  shift
  echo "==> ${name}"
  if "$@"; then
    echo "    PASS"
    passed=$((passed + 1))
  else
    echo "    FAIL"
    failures=$((failures + 1))
  fi
}

verify_json_parse() {
  "${PYTHON}" -c "import json; json.load(open('${INPUT}'))"
}

verify_schema_fields() {
  "${PYTHON}" - <<'PY' "${INPUT}" "${SCHEMA}"
import json, sys
from pathlib import Path

path, schema_path = sys.argv[1], sys.argv[2]
data = json.load(open(path))
schema = json.load(open(schema_path))
required = set(schema.get("required", []))
props = schema.get("properties", {})
missing = sorted(required - set(data.keys()))
if missing:
    print(f"missing required fields: {missing}")
    sys.exit(1)
for key, spec in props.items():
    if key not in data:
        continue
    val = data[key]
    if "const" in spec and val != spec["const"]:
        print(f"{key}: expected const {spec['const']!r}, got {val!r}")
        sys.exit(1)
    if spec.get("type") == "string" and "enum" in spec and val not in spec["enum"]:
        print(f"{key}: {val!r} not in enum")
        sys.exit(1)
    if spec.get("type") == "array" and "items" in spec:
        item_enum = spec["items"].get("enum")
        if item_enum:
            bad = [u for u in val if u not in item_enum]
            if bad:
                print(f"{key}: disallowed URLs: {bad}")
                sys.exit(1)
PY
}

verify_winner_rfc() {
  local rfc
  rfc="$("${PYTHON}" -c "import json; print(json.load(open('${INPUT}'))['winner_rfc'])")"
  for allowed in "${ALLOWED_RFCS[@]}"; do
    [[ "${rfc}" == "${allowed}" ]] && return 0
  done
  echo "    winner_rfc ${rfc} not in allowlist" >&2
  return 1
}

verify_source_urls_subset() {
  "${PYTHON}" - <<'PY' "${INPUT}"
import json, sys
allowed = {
    "https://www.rfc-editor.org/info/rfc2324",
    "https://www.rfc-editor.org/info/rfc1149",
    "https://www.rfc-editor.org/info/rfc2549",
}
urls = json.load(open(sys.argv[1])).get("source_urls", [])
if not urls:
    print("source_urls empty")
    sys.exit(1)
bad = [u for u in urls if u not in allowed]
if bad:
    print(f"non-allowlisted URLs: {bad}")
    sys.exit(1)
PY
}

verify_winner_in_source_urls() {
  "${PYTHON}" - <<'PY' "${INPUT}"
import json, sys
data = json.load(open(sys.argv[1]))
winner = data["winner_rfc"]
urls = data.get("source_urls", [])
needle = f"/info/rfc{winner}"
if not any(needle in u for u in urls):
    print(f"no source_url contains {needle}")
    sys.exit(1)
PY
}

echo "rfc-lookup-demo-verify: ${INPUT}"
echo "allowed URLs: ${ALLOWED_URLS[*]}"

check "json parse" verify_json_parse
check "schema fields (required, enum, const)" verify_schema_fields
check "winner_rfc allowlist" verify_winner_rfc
check "source_urls allowlist only" verify_source_urls_subset
check "winner_rfc cited in source_urls" verify_winner_in_source_urls

echo ""
echo "summary: ${passed} passed, ${failures} failed"
if [[ "${failures}" -gt 0 ]]; then
  exit 1
fi
echo "rfc lookup output verify OK"
from __future__ import annotations

import re
from typing import Any


def scan_secrets(text: str, patterns: list[str]) -> list[str]:
    hits = []
    for pattern in patterns:
        if re.search(pattern, text):
            hits.append(pattern)
    return hits


def redact_secrets(text: str, patterns: list[str]) -> tuple[str, list[str]]:
    redacted = text
    matched = []
    for pattern in patterns:
        if re.search(pattern, redacted):
            matched.append(pattern)
            redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted, matched
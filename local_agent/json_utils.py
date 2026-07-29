"""Helpers for extracting/repairing JSON from local-model output."""

from __future__ import annotations

import json
import re
from typing import Any, Optional


def strip_code_fences(text: str) -> str:
    content = (text or "").strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    return content.strip()


def sanitize_json_text(text: str) -> str:
    """Fix common local-model JSON defects (trailing commas)."""
    content = strip_code_fences(text)
    # Remove trailing commas before } or ]
    content = re.sub(r",(\s*[}\]])", r"\1", content)
    return content


def extract_balanced_json(text: str) -> Optional[str]:
    """Return the first balanced JSON object/array substring, if any."""
    content = sanitize_json_text(text)
    start = None
    opener = None
    for i, ch in enumerate(content):
        if ch in "{[":
            start = i
            opener = ch
            break
    if start is None or opener is None:
        return None
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(content)):
        ch = content[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return content[start : i + 1]
    return None


def loads_json_lenient(text: str) -> Any | None:
    """Parse JSON with fence/trailing-comma/balanced-extract fallbacks."""
    candidates = []
    cleaned = sanitize_json_text(text)
    if cleaned:
        candidates.append(cleaned)
    balanced = extract_balanced_json(text)
    if balanced and balanced not in candidates:
        candidates.append(balanced)
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None

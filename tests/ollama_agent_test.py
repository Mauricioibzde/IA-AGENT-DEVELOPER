"""Optional live smoke test against a local Ollama daemon."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def test_ollama_api():
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.load(response)
    except (urllib.error.URLError, TimeoutError) as exc:
        import pytest

        pytest.skip(f"Ollama not available: {exc}")
    assert "models" in data


if __name__ == "__main__":
    test_ollama_api()
    print("ollama ok")

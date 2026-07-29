"""Tool call parser tests."""

from __future__ import annotations

import json

from local_agent.tool_registry import parse_tool_call, parse_tool_calls


def test_parse_single_json() -> None:
    tool, args = parse_tool_call('{"tool":"write_file","args":{"path":"a.txt","content":"x"}}')
    assert tool == "write_file"
    assert args["path"] == "a.txt"


def test_parse_multiple_calls() -> None:
    payload = json.dumps(
        [
            {"tool": "write_file", "args": {"path": "a.txt", "content": "1"}},
            {"tool": "write_file", "args": {"path": "b.txt", "content": "2"}},
        ]
    )
    calls = parse_tool_calls(payload)
    assert len(calls) == 2


def test_parse_fenced_json() -> None:
    payload = '```json\n{"tool":"list_directory","args":{"path":"."}}\n```'
    assert parse_tool_calls(payload)[0]["tool"] == "list_directory"


def test_invalid_json_returns_empty() -> None:
    assert parse_tool_calls("not json at all") == []

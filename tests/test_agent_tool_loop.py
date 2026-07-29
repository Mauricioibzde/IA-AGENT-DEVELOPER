"""Unit tests for sandboxed Ollama agent tools (no live Ollama required)."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ollama_agent import (
    WorkspaceSecurityError,
    execute_tool,
    infer_tool_call_from_text,
    parse_tool_call,
    parse_tool_calls,
    resolve_in_workspace,
)


def test_parse_tool_call_with_json_payload():
    payload = '{"tool":"write_file","args":{"path":"notes.txt","content":"hello"}}'
    tool_name, args = parse_tool_call(payload)
    assert tool_name == "write_file"
    assert args["path"] == "notes.txt"
    assert args["content"] == "hello"


def test_parse_tool_calls_array():
    payload = json.dumps(
        [
            {"tool": "write_file", "args": {"path": "a.txt", "content": "1"}},
            {"tool": "write_file", "args": {"path": "b.txt", "content": "2"}},
        ]
    )
    calls = parse_tool_calls(payload)
    assert len(calls) == 2
    assert calls[0]["args"]["path"] == "a.txt"


def test_parse_tool_calls_from_fenced_json():
    payload = '```json\n{"tool":"list_dir","args":{"path":"."}}\n```'
    calls = parse_tool_calls(payload)
    assert calls == [{"tool": "list_dir", "args": {"path": "."}}]


def test_execute_tool_writes_file(tmp_path):
    result = execute_tool("write_file", {"path": "demo.txt", "content": "ok"}, workspace=str(tmp_path))
    assert result["ok"] is True
    assert (tmp_path / "demo.txt").read_text(encoding="utf-8") == "ok"


def test_execute_tool_creates_directory(tmp_path):
    result = execute_tool("create_directory", {"path": "nested"}, workspace=str(tmp_path))
    assert result["ok"] is True
    assert (tmp_path / "nested").exists() is True


def test_path_sandbox_blocks_escape(tmp_path):
    with pytest.raises(WorkspaceSecurityError):
        resolve_in_workspace(tmp_path, "../outside.txt")


def test_write_file_blocks_absolute_escape(tmp_path, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.txt"
    with pytest.raises(WorkspaceSecurityError):
        execute_tool("write_file", {"path": str(outside), "content": "nope"}, workspace=str(tmp_path))


def test_replace_in_file_reports_replacements(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("hello hello", encoding="utf-8")
    result = execute_tool(
        "replace_in_file",
        {"path": "file.txt", "old": "hello", "new": "hi"},
        workspace=str(tmp_path),
    )
    assert result["ok"] is True
    assert result["replacements"] == 2
    assert target.read_text(encoding="utf-8") == "hi hi"


def test_replace_in_file_errors_when_missing(tmp_path):
    (tmp_path / "file.txt").write_text("abc", encoding="utf-8")
    with pytest.raises(ValueError, match="No matches"):
        execute_tool(
            "replace_in_file",
            {"path": "file.txt", "old": "zzz", "new": "x"},
            workspace=str(tmp_path),
        )


def test_dry_run_does_not_write(tmp_path):
    result = execute_tool(
        "write_file",
        {"path": "demo.txt", "content": "ok"},
        workspace=str(tmp_path),
        dry_run=True,
    )
    assert result["dry_run"] is True
    assert not (tmp_path / "demo.txt").exists()


def test_scaffold_python_project(tmp_path):
    result = execute_tool(
        "scaffold_project",
        {"name": "demo", "path": "demo", "template": "python"},
        workspace=str(tmp_path),
    )
    assert result["ok"] is True
    assert (tmp_path / "demo" / "src" / "main.py").exists()
    assert (tmp_path / "demo" / "pyproject.toml").exists()


def test_create_multiple_files(tmp_path):
    result = execute_tool(
        "create_multiple_files",
        {
            "files": [
                {"path": "a/one.txt", "content": "1"},
                {"path": "a/two.txt", "content": "2"},
            ]
        },
        workspace=str(tmp_path),
    )
    assert result["ok"] is True
    assert (tmp_path / "a" / "one.txt").read_text(encoding="utf-8") == "1"
    assert (tmp_path / "a" / "two.txt").read_text(encoding="utf-8") == "2"


def test_validate_path_directory(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "x.txt").write_text("x", encoding="utf-8")
    result = execute_tool("validate_path", {"path": "app"}, workspace=str(tmp_path))
    assert result["ok"] is True
    assert result["kind"] == "directory"
    assert "x.txt" in result["items"]


def test_infer_portuguese_create_file():
    inferred = infer_tool_call_from_text('Criar um arquivo chamado demo.txt com o conteúdo hello')
    assert inferred is not None
    assert inferred["tool"] == "write_file"
    assert inferred["args"]["path"] == "demo.txt"


def test_infer_portuguese_scaffold():
    inferred = infer_tool_call_from_text("Criar um projeto chamado app_demo na pasta app_demo")
    assert inferred is not None
    assert inferred["tool"] == "scaffold_project"
    assert inferred["args"]["name"] == "app_demo"


def test_run_command_cwd_sandboxed(tmp_path):
    result = execute_tool(
        "run_command",
        {"command": f"{sys.executable} -c \"print('hi')\"", "cwd": "."},
        workspace=str(tmp_path),
    )
    assert result["ok"] is True, result
    assert "hi" in result["stdout"]

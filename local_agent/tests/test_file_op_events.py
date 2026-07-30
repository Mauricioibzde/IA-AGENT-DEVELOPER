"""Live file_op preview payload tests."""

from __future__ import annotations

from pathlib import Path

from local_agent.file_op_events import build_file_op_event


def test_write_start_preview_has_added_lines(tmp_path: Path) -> None:
    ev = build_file_op_event(
        workspace=tmp_path,
        tool="write_file",
        args={"path": "index.html", "content": "<h1>Hi</h1>\n<p>ok</p>\n"},
        status="start",
    )
    assert ev["type"] == "file_op"
    assert ev["op"] == "write"
    assert ev["path"] == "index.html"
    assert any(line["kind"] == "add" for line in ev["lines"])


def test_edit_done_uses_diff_when_present(tmp_path: Path) -> None:
    diff = "\n".join(
        [
            "--- a/app.js",
            "+++ b/app.js",
            "@@ -1,2 +1,2 @@",
            "-const x = 1",
            "+const x = 2",
        ]
    )
    ev = build_file_op_event(
        workspace=tmp_path,
        tool="edit_file",
        args={"path": "app.js", "old": "const x = 1", "new": "const x = 2"},
        status="done",
        result={"ok": True, "data": {"path": str(tmp_path / "app.js"), "diff": diff}},
    )
    kinds = {line["kind"] for line in ev["lines"]}
    assert "add" in kinds
    assert "del" in kinds


def test_read_done_parses_numbered_content(tmp_path: Path) -> None:
    ev = build_file_op_event(
        workspace=tmp_path,
        tool="read_file",
        args={"path": "main.py"},
        status="done",
        result={
            "ok": True,
            "data": {
                "path": str(tmp_path / "main.py"),
                "content": "1: print('hi')\n2: print('bye')\n",
                "total_lines": 2,
            },
        },
    )
    assert ev["op"] == "read"
    assert ev["lines"][0]["n"] == 1
    assert "print" in ev["lines"][0]["text"]

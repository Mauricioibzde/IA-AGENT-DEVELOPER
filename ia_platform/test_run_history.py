"""Run history persistence tests."""

from __future__ import annotations

from ia_platform.run_history import load_runs, record_run


def test_record_and_load_runs(tmp_path) -> None:
    record_run(
        tmp_path,
        goal="Create landing page",
        status="SUCCESS",
        report="Done\n- index.html created",
        created_files=["index.html"],
        modified_files=[],
        run_id="run-abc",
    )
    runs = load_runs(tmp_path)
    assert len(runs) == 1
    assert runs[0]["id"] == "run-abc"
    assert runs[0]["status"] == "SUCCESS"
    assert runs[0]["goal"] == "Create landing page"
    assert "index.html" in runs[0]["created_files"]


def test_runs_are_newest_first(tmp_path) -> None:
    record_run(tmp_path, goal="first", status="SUCCESS", report="a")
    record_run(tmp_path, goal="second", status="FAILED", report="b")
    runs = load_runs(tmp_path, limit=10)
    assert runs[0]["goal"] == "second"
    assert runs[1]["goal"] == "first"

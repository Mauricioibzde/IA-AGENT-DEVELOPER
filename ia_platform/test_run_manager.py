"""Tests for run event buffer / reconnect helpers."""

from __future__ import annotations

from ia_platform.run_manager import RunManager


def test_run_manager_buffers_events_and_active_workspace(tmp_path) -> None:
    mgr = RunManager()
    run_id = mgr.acquire(str(tmp_path))
    assert run_id
    mgr.set_goal(run_id, "criar app")
    mgr.append_event(run_id, {"type": "step", "message": "a"})
    mgr.append_event(run_id, {"type": "step", "message": "b"})
    events = mgr.events_after(run_id, after=1)
    assert len(events) == 1
    assert events[0]["message"] == "b"
    active = mgr.active_for_workspace(str(tmp_path))
    assert active and active["run_id"] == run_id
    assert active["goal"] == "criar app"
    mgr.clear(run_id, keep_events_seconds=30)
    assert mgr.active_for_workspace(str(tmp_path)) is None
    assert mgr.status(run_id)["active"] is False
    assert mgr.events_after(run_id, after=0)

"""Tests for run event buffer / reconnect helpers."""

from __future__ import annotations

import time

from ia_platform import run_manager as run_manager_mod
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


def test_run_manager_frees_cancelled_lock_after_grace(tmp_path, monkeypatch) -> None:
    mgr = RunManager()
    run_id = mgr.acquire(str(tmp_path))
    assert run_id
    mgr.cancel(run_id, force=False)
    assert mgr.is_workspace_busy(str(tmp_path)) is True

    meta = mgr._meta[run_id]
    meta["started_at"] = time.time() - (run_manager_mod.CANCELLED_GRACE_SECONDS + 5)
    assert mgr.is_workspace_busy(str(tmp_path)) is False
    assert mgr.active_for_workspace(str(tmp_path)) is None


def test_run_manager_frees_stale_idle_lock(tmp_path) -> None:
    mgr = RunManager()
    run_id = mgr.acquire(str(tmp_path))
    assert run_id
    meta = mgr._meta[run_id]
    meta["started_at"] = time.time() - 60
    meta["last_event_at"] = time.time() - (run_manager_mod.STALE_IDLE_SECONDS + 10)
    assert mgr.is_workspace_busy(str(tmp_path)) is False
    # After free, a new acquire must succeed.
    new_id = mgr.acquire(str(tmp_path))
    assert new_id and new_id != run_id


def test_run_manager_frees_max_age_lock(tmp_path) -> None:
    mgr = RunManager()
    run_id = mgr.acquire(str(tmp_path))
    assert run_id
    meta = mgr._meta[run_id]
    meta["started_at"] = time.time() - (run_manager_mod.MAX_LOCK_AGE_SECONDS + 30)
    meta["last_event_at"] = time.time()  # recent events, but age wins
    assert mgr.is_workspace_busy(str(tmp_path)) is False


def test_run_manager_force_cancel_frees_immediately(tmp_path) -> None:
    mgr = RunManager()
    run_id = mgr.acquire(str(tmp_path))
    assert mgr.is_workspace_busy(str(tmp_path))
    assert mgr.cancel(run_id, force=True) is True
    assert mgr.is_workspace_busy(str(tmp_path)) is False

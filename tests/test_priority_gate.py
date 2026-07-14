"""Tests for the MCP priority gate that enforces task_pipeline() first-call."""
import copy
import json
from pathlib import Path

from agent_guidance_mcp.server import (
    PRIORITY_ERROR,
    PRIORITY_RESOURCE_CONTENT,
    GATE_WHITELIST,
    GATE_SENTINEL_PATH,
    priority_gate_check,
    priority_gate_pass,
    priority_gate_reset,
    _gate_sentinel_write,
    _gate_sentinel_check,
    _gate_sentinel_clear,
)


def _reset() -> None:
    priority_gate_reset()
    _gate_sentinel_clear()


# ── Basic gate behavior ────────────────────────────────────────────────

def test_gate_blocks_before_task_pipeline() -> None:
    _reset()
    result = priority_gate_check()
    assert result is not None
    assert result["error"] == "PRIORITY_REQUIRED"
    assert "task_pipeline" in result["message"]
    assert result["resource"] == "agent-guidance-mcp://system/priority"


def test_gate_error_shape_immutable() -> None:
    _reset()
    result = priority_gate_check()
    assert result is not None
    assert set(result.keys()) == {"success", "error", "message", "resource", "resolution"}
    assert result["success"] is False
    assert result["error"] == "PRIORITY_REQUIRED"
    assert isinstance(result["message"], str)
    assert isinstance(result["resource"], str)
    assert isinstance(result["resolution"], str)
    before_keys = set(PRIORITY_ERROR.keys())
    result["_test_mutate"] = True
    assert set(PRIORITY_ERROR.keys()) == before_keys


def test_gate_passes_after_task_pipeline() -> None:
    _reset()
    assert priority_gate_check() is not None
    priority_gate_pass()
    assert priority_gate_check() is None


def test_gate_reset_works() -> None:
    _reset()
    priority_gate_pass()
    assert priority_gate_check() is None
    priority_gate_reset()
    assert priority_gate_check() is not None


def test_gate_whitelist_contains_expected_tools() -> None:
    expected = {"health_check", "diagnose", "token_stats"}
    assert GATE_WHITELIST == expected


def test_gate_twice_pass_is_idempotent() -> None:
    _reset()
    priority_gate_pass()
    assert priority_gate_check() is None
    priority_gate_pass()
    assert priority_gate_check() is None


def test_gate_thread_safety() -> None:
    import threading
    _reset()
    errors: list[bool] = []
    def worker() -> None:
        errors.append(priority_gate_check() is not None)
    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert all(errors)

    priority_gate_pass()
    errors2: list[bool] = []
    threads2 = [threading.Thread(target=lambda: errors2.append(priority_gate_check() is not None)) for _ in range(20)]
    for t in threads2: t.start()
    for t in threads2: t.join()
    assert not any(errors2)


def test_priority_error_immutable_default() -> None:
    before = copy.deepcopy(dict(PRIORITY_ERROR))
    _ = priority_gate_check()
    assert dict(PRIORITY_ERROR) == before


# ── Priority resource content ──────────────────────────────────────────

def test_priority_resource_content_has_gated_tools() -> None:
    assert "task_pipeline" in PRIORITY_RESOURCE_CONTENT
    assert "guidance" in PRIORITY_RESOURCE_CONTENT
    assert "project_context" in PRIORITY_RESOURCE_CONTENT
    assert "health_check" in PRIORITY_RESOURCE_CONTENT


# ── Sentinel file ──────────────────────────────────────────────────────

def test_sentinel_write_check_clear() -> None:
    _gate_sentinel_clear()
    assert not GATE_SENTINEL_PATH.exists()
    assert not _gate_sentinel_check()

    _gate_sentinel_write(project_path=".")
    assert GATE_SENTINEL_PATH.exists()
    assert _gate_sentinel_check()

    data = json.loads(GATE_SENTINEL_PATH.read_text(encoding="utf-8"))
    assert data["project_path"] == "."

    _gate_sentinel_clear()
    assert not GATE_SENTINEL_PATH.exists()
    assert not _gate_sentinel_check()


def test_sentinel_missing_returns_false() -> None:
    _gate_sentinel_clear()
    assert not _gate_sentinel_check()


def test_sentinel_corrupt_returns_false() -> None:
    _gate_sentinel_clear()
    GATE_SENTINEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    GATE_SENTINEL_PATH.write_text("not valid json", encoding="utf-8")
    assert not _gate_sentinel_check()
    _gate_sentinel_clear()


def test_sentinel_gate_fallback_passes() -> None:
    _reset()
    assert priority_gate_check() is not None
    _gate_sentinel_write(project_path=".")
    assert priority_gate_check() is None
    _gate_sentinel_clear()
    assert priority_gate_check() is None


def test_sentinel_any_project_path_passes() -> None:
    _reset()
    _gate_sentinel_write(project_path="/some/other/project")
    assert priority_gate_check() is None
    _gate_sentinel_clear()
    _reset()

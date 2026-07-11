"""Tests for the MCP priority gate that enforces task_pipeline() first-call."""
import copy

from agent_guidance_mcp.server import (
    PRIORITY_ERROR,
    GATE_WHITELIST,
    priority_gate_check,
    priority_gate_pass,
    priority_gate_reset,
)


def _reset() -> None:
    """Ensure gate is reset before each test."""
    priority_gate_reset()


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
    # Must contain exactly the expected keys
    assert set(result.keys()) == {"success", "error", "message", "resource", "resolution"}
    assert result["success"] is False
    assert result["error"] == "PRIORITY_REQUIRED"
    assert isinstance(result["message"], str)
    assert isinstance(result["resource"], str)
    assert isinstance(result["resolution"], str)
    # Modifying result must not mutate PRIORITY_ERROR
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
        result = priority_gate_check()
        errors.append(result is not None)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # All should be blocked (gate not passed)
    assert all(errors)

    # Now pass and retry
    priority_gate_pass()
    errors2: list[bool] = []
    threads2 = [threading.Thread(target=lambda: errors2.append(priority_gate_check() is not None)) for _ in range(20)]
    for t in threads2:
        t.start()
    for t in threads2:
        t.join()
    # All should be None (gate passed)
    assert not any(errors2)


def test_priority_error_immutable_default() -> None:
    """Verify the module-level PRIORITY_ERROR dict is never accidentally mutated."""
    before = copy.deepcopy(dict(PRIORITY_ERROR))
    _ = priority_gate_check()
    assert dict(PRIORITY_ERROR) == before

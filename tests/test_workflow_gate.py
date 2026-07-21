import os
import shutil
import tempfile
from pathlib import Path
import pytest

from agent_guidance_mcp.session import save_session, load_session, check_approval_in_text
from agent_guidance_mcp.pipelines import session_continuity
from agent_guidance_mcp.server import priority_gate_check

def test_check_approval_in_text():
    assert check_approval_in_text("proceed") is True
    assert check_approval_in_text("ok") is True
    assert check_approval_in_text("bắt đầu") is True
    assert check_approval_in_text("not approved") is False
    assert check_approval_in_text("waiting") is False

def test_planning_loop_block():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set AGENT_PROJECT_ROOT env var to allow validation in resolve_project_root
        os.environ["AGENT_PROJECT_ROOT"] = tmpdir
        os.environ["AGENT_PROJECT_ALLOWED_ROOTS"] = tmpdir
        try:
            # Save Plan stage first
            res = session_continuity(
                operation="save",
                project_path=tmpdir,
                task="Design DB architecture",
                metadata={"current_stage": "Plan"}
            )
            assert res["success"] is True
            
            # Try to transition to Build without approval
            res2 = session_continuity(
                operation="save",
                project_path=tmpdir,
                task="Write database code",
                metadata={"current_stage": "Build"}
            )
            assert res2["success"] is False
            assert res2["error"] == "PLAN_NOT_APPROVED"

            # Now transition with approval in task description
            res3 = session_continuity(
                operation="save",
                project_path=tmpdir,
                task="Okay, start build phase",
                metadata={"current_stage": "Build"}
            )
            assert res3["success"] is True
            assert res3["session"]["metadata"]["plan_approved"] is True
        finally:
            if "AGENT_PROJECT_ROOT" in os.environ:
                del os.environ["AGENT_PROJECT_ROOT"]
            if "AGENT_PROJECT_ALLOWED_ROOTS" in os.environ:
                del os.environ["AGENT_PROJECT_ALLOWED_ROOTS"]

def test_circuit_breaker():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["AGENT_PROJECT_ROOT"] = tmpdir
        os.environ["AGENT_PROJECT_ALLOWED_ROOTS"] = tmpdir
        try:
            # Start in Build stage
            session_continuity(
                operation="save",
                project_path=tmpdir,
                task="Write database code",
                metadata={"current_stage": "Build", "plan_approved": True}
            )

            # Transition into Fix stage (attempt 1)
            res1 = session_continuity(
                operation="save",
                project_path=tmpdir,
                task="Fix syntax error",
                metadata={"current_stage": "Fix"}
            )
            assert res1["success"] is True
            assert res1["session"]["metadata"]["fix_attempts"] == 1

            # Fix stage (attempt 2)
            res2 = session_continuity(
                operation="save",
                project_path=tmpdir,
                task="Fix compiler warning",
                metadata={"current_stage": "Fix"}
            )
            assert res2["success"] is True
            assert res2["session"]["metadata"]["fix_attempts"] == 2

            # Fix stage (attempt 3 - triggers circuit breaker)
            res3 = session_continuity(
                operation="save",
                project_path=tmpdir,
                task="Fix type warning again",
                metadata={"current_stage": "Fix"}
            )
            assert res3["success"] is False
            assert res3["error"] == "CIRCUIT_BREAKER_TRIGGERED"
            
            # Verify it fallback-saved to Ask_Revise stage and reset flags
            session = load_session(tmpdir)
            assert session["metadata"]["current_stage"] == "Ask_Revise"
            assert session["metadata"]["plan_approved"] is False
            assert session["metadata"]["fix_attempts"] == 0
        finally:
            del os.environ["AGENT_PROJECT_ROOT"]
            if "AGENT_PROJECT_ALLOWED_ROOTS" in os.environ:
                del os.environ["AGENT_PROJECT_ALLOWED_ROOTS"]


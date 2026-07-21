import os
import shutil
import tempfile
from pathlib import Path
import pytest

from agent_guidance_mcp.session import save_session, load_session, check_approval_in_text
from agent_guidance_mcp.pipelines import session_continuity, workflow_gate
from agent_guidance_mcp.server import priority_gate_check

def test_check_approval_in_text():
    assert check_approval_in_text("proceed") is True
    assert check_approval_in_text("ok") is True
    assert check_approval_in_text("bắt đầu") is True
    assert check_approval_in_text("not approved") is False
    assert check_approval_in_text("waiting") is False

def test_planning_loop_block():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["AGENT_PROJECT_ROOT"] = tmpdir
        os.environ["AGENT_PROJECT_ALLOWED_ROOTS"] = tmpdir
        try:
            # Set to Plan stage first
            res = workflow_gate(
                action="set_stage",
                project_path=tmpdir,
                target_stage="Plan"
            )
            assert res["success"] is True
            assert res["current_stage"] == "Plan"
            
            # Try to transition to Build without approval
            res2 = workflow_gate(
                action="set_stage",
                project_path=tmpdir,
                target_stage="Build"
            )
            assert res2["success"] is False
            assert res2["error"] == "PLAN_NOT_APPROVED"

            # Check user message containing approval
            res3 = workflow_gate(
                action="check",
                project_path=tmpdir,
                user_message="Okay, proceed with the implementation."
            )
            assert res3["success"] is True
            assert res3["plan_approved"] is True

            # Transition to Build should now succeed
            res4 = workflow_gate(
                action="set_stage",
                project_path=tmpdir,
                target_stage="Build"
            )
            assert res4["success"] is True
            assert res4["current_stage"] == "Build"
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
            # Transition to Build stage (with approval)
            workflow_gate(
                action="check",
                project_path=tmpdir,
                user_message="ok proceed"
            )
            workflow_gate(
                action="set_stage",
                project_path=tmpdir,
                target_stage="Build"
            )

            # Fix attempt 1
            res1 = workflow_gate(
                action="set_stage",
                project_path=tmpdir,
                target_stage="Fix"
            )
            assert res1["success"] is True
            assert res1["fix_attempts"] == 1

            # Fix attempt 2
            res2 = workflow_gate(
                action="set_stage",
                project_path=tmpdir,
                target_stage="Fix"
            )
            assert res2["success"] is True
            assert res2["fix_attempts"] == 2

            # Fix attempt 3 - Circuit Breaker triggers
            res3 = workflow_gate(
                action="set_stage",
                project_path=tmpdir,
                target_stage="Fix"
            )
            assert res3["success"] is False
            assert res3["error"] == "CIRCUIT_BREAKER_TRIGGERED"
            
            # Verify state was reset and reverted to Ask_Revise
            session = load_session(tmpdir)
            assert session["metadata"]["current_stage"] == "Ask_Revise"
            assert session["metadata"]["plan_approved"] is False
            assert session["metadata"]["fix_attempts"] == 0
        finally:
            if "AGENT_PROJECT_ROOT" in os.environ:
                del os.environ["AGENT_PROJECT_ROOT"]
            if "AGENT_PROJECT_ALLOWED_ROOTS" in os.environ:
                del os.environ["AGENT_PROJECT_ALLOWED_ROOTS"]

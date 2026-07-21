import os
import shutil
import tempfile
from pathlib import Path
import pytest

from agent_guidance_mcp.session import save_session, load_session, check_approval_in_text
from agent_guidance_mcp.pipelines import session_continuity, workflow_gate
from agent_guidance_mcp.server import priority_gate_check, workflow_gate_check

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
            res = workflow_gate(
                action="set_stage",
                project_path=tmpdir,
                target_stage="Plan"
            )
            assert res["success"] is True
            assert res["current_stage"] == "Plan"

            res2 = workflow_gate(
                action="set_stage",
                project_path=tmpdir,
                target_stage="Build"
            )
            assert res2["success"] is False
            assert res2["error"] == "PLAN_NOT_APPROVED"

            res3 = workflow_gate(
                action="check",
                project_path=tmpdir,
                user_message="Okay, proceed with the implementation."
            )
            assert res3["success"] is True
            assert res3["plan_approved"] is True

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

            res1 = workflow_gate(
                action="set_stage",
                project_path=tmpdir,
                target_stage="Fix"
            )
            assert res1["success"] is True
            assert res1["fix_attempts"] == 1

            res2 = workflow_gate(
                action="set_stage",
                project_path=tmpdir,
                target_stage="Fix"
            )
            assert res2["success"] is True
            assert res2["fix_attempts"] == 2

            res3 = workflow_gate(
                action="set_stage",
                project_path=tmpdir,
                target_stage="Fix"
            )
            assert res3["success"] is False
            assert res3["error"] == "CIRCUIT_BREAKER_TRIGGERED"

            session = load_session(tmpdir)
            assert session["metadata"]["current_stage"] == "Ask_Revise"
            assert session["metadata"]["plan_approved"] is False
            assert session["metadata"]["fix_attempts"] == 0
        finally:
            if "AGENT_PROJECT_ROOT" in os.environ:
                del os.environ["AGENT_PROJECT_ROOT"]
            if "AGENT_PROJECT_ALLOWED_ROOTS" in os.environ:
                del os.environ["AGENT_PROJECT_ALLOWED_ROOTS"]

def test_workflow_gate_matrix_enforcement():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["AGENT_PROJECT_ROOT"] = tmpdir
        os.environ["AGENT_PROJECT_ALLOWED_ROOTS"] = tmpdir
        try:
            res = workflow_gate_check(project_path=tmpdir, tool_name="project_context", tool_params={"operation": "read"})
            assert res is not None
            assert res["error"] == "WORKFLOW_STAGE_BLOCKED"

            workflow_gate(action="set_stage", project_path=tmpdir, target_stage="Plan")
            res_plan = workflow_gate_check(project_path=tmpdir, tool_name="project_context", tool_params={"operation": "read"})
            assert res_plan is None

            workflow_gate(action="set_stage", project_path=tmpdir, target_stage="Ask_Revise")
            res_ask = workflow_gate_check(project_path=tmpdir, tool_name="project_context", tool_params={"operation": "read"})
            assert res_ask is not None
            assert res_ask["error"] == "WORKFLOW_STAGE_BLOCKED"

            workflow_gate(action="check", project_path=tmpdir, user_message="ok proceed")
            res_approved_ask = workflow_gate_check(project_path=tmpdir, tool_name="project_context", tool_params={"operation": "read"})
            assert res_approved_ask is not None

            workflow_gate(action="set_stage", project_path=tmpdir, target_stage="Build")
            res_build = workflow_gate_check(project_path=tmpdir, tool_name="project_context", tool_params={"operation": "read"})
            assert res_build is None
        finally:
            if "AGENT_PROJECT_ROOT" in os.environ:
                del os.environ["AGENT_PROJECT_ROOT"]
            if "AGENT_PROJECT_ALLOWED_ROOTS" in os.environ:
                del os.environ["AGENT_PROJECT_ALLOWED_ROOTS"]

def test_ui_ux_search_bypasses_gate():
    gate = priority_gate_check(
        project_path=Path("/nonexistent"),
        tool_name="ui_ux",
        tool_params={"operation": "search", "query": "dashboard color"}
    )
    assert gate is None

    gate2 = priority_gate_check(
        project_path=Path("/nonexistent"),
        tool_name="ui_ux",
        tool_params={"operation": "slides"}
    )
    assert gate2 is None

def test_ui_ux_design_system_blocked_in_early_stages():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["AGENT_PROJECT_ROOT"] = tmpdir
        os.environ["AGENT_PROJECT_ALLOWED_ROOTS"] = tmpdir
        try:
            res = workflow_gate_check(
                project_path=tmpdir, tool_name="ui_ux",
                tool_params={"operation": "design_system"}
            )
            assert res is not None
            assert res["error"] == "WORKFLOW_STAGE_BLOCKED"

            workflow_gate(action="set_stage", project_path=tmpdir, target_stage="Plan")
            res_plan = workflow_gate_check(
                project_path=tmpdir, tool_name="ui_ux",
                tool_params={"operation": "design_system"}
            )
            assert res_plan is not None

            workflow_gate(action="set_stage", project_path=tmpdir, target_stage="Ask_Revise")
            res_ask = workflow_gate_check(
                project_path=tmpdir, tool_name="ui_ux",
                tool_params={"operation": "design_system"}
            )
            assert res_ask is not None

            workflow_gate(action="check", project_path=tmpdir, user_message="proceed")
            workflow_gate(action="set_stage", project_path=tmpdir, target_stage="Build")
            res_build = workflow_gate_check(
                project_path=tmpdir, tool_name="ui_ux",
                tool_params={"operation": "design_system"}
            )
            assert res_build is None
        finally:
            if "AGENT_PROJECT_ROOT" in os.environ:
                del os.environ["AGENT_PROJECT_ROOT"]
            if "AGENT_PROJECT_ALLOWED_ROOTS" in os.environ:
                del os.environ["AGENT_PROJECT_ALLOWED_ROOTS"]

def test_ui_ux_search_unblocked_always():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["AGENT_PROJECT_ROOT"] = tmpdir
        os.environ["AGENT_PROJECT_ALLOWED_ROOTS"] = tmpdir
        try:
            res = workflow_gate_check(
                project_path=tmpdir, tool_name="ui_ux",
                tool_params={"operation": "search"}
            )
            assert res is None

            workflow_gate(action="set_stage", project_path=tmpdir, target_stage="Plan")
            res_plan = workflow_gate_check(
                project_path=tmpdir, tool_name="ui_ux",
                tool_params={"operation": "search"}
            )
            assert res_plan is None
        finally:
            if "AGENT_PROJECT_ROOT" in os.environ:
                del os.environ["AGENT_PROJECT_ROOT"]
            if "AGENT_PROJECT_ALLOWED_ROOTS" in os.environ:
                del os.environ["AGENT_PROJECT_ALLOWED_ROOTS"]

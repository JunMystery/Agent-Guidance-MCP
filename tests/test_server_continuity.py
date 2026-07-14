import pytest
from pathlib import Path
from agent_guidance_mcp.server import create_server, priority_gate_pass

def test_session_continuity_path_traversal(tmp_path):
    mcp = create_server(root=str(tmp_path))
    # Must pass the priority gate before calling gated tools directly
    priority_gate_pass()

    session_continuity_tool = mcp._tool_manager._tools["session_continuity"].fn

    res = session_continuity_tool(operation="save", project_path=str(tmp_path / "../outside"), task="test")
    assert res["success"] is False
    assert "Invalid project_path" in res["error"]

    res = session_continuity_tool(operation="load", project_path=str(tmp_path / "../outside"))
    assert res["success"] is False
    assert "Invalid project_path" in res["error"]

    res = session_continuity_tool(operation="clear", project_path=str(tmp_path / "../outside"))
    assert res["success"] is False
    assert "Invalid project_path" in res["error"]

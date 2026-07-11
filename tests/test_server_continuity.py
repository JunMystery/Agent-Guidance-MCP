import pytest
from pathlib import Path
from agent_guidance_mcp.server import create_server, priority_gate_pass

def test_session_continuity_path_traversal(tmp_path):
    mcp = create_server(root=str(tmp_path))
    
    # Must pass the priority gate before calling gated tools directly
    priority_gate_pass()
    
    # Retrieve the registered session_continuity tool handler
    session_continuity_tool = mcp._tool_manager._tools["session_continuity"].fn
    
    # Try save with invalid path (outside project root)
    res = session_continuity_tool(operation="save", project_path=str(tmp_path / "../outside"), task="test")
    assert res["success"] is False
    assert "Invalid project_path" in res["error"]
    
    # Try load with invalid path
    res = session_continuity_tool(operation="load", project_path=str(tmp_path / "../outside"))
    assert res["success"] is False
    assert "Invalid project_path" in res["error"]

    # Try clear with invalid path
    res = session_continuity_tool(operation="clear", project_path=str(tmp_path / "../outside"))
    assert res["success"] is False
    assert "Invalid project_path" in res["error"]

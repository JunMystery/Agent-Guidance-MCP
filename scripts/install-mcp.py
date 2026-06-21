#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from pathlib import Path

SERVER_ID = "agent-guidance-mcp"
MODULE_NAME = "agent_guidance_mcp"


def owns_json_server_config(server_config):
    if not isinstance(server_config, dict):
        return False
    args = server_config.get("args", [])
    return isinstance(args, list) and MODULE_NAME in args


def main():
    repo_root = Path(__file__).resolve().parents[1]
    venv_dir = repo_root / ".venv"
    
    print("=== Agent Guidance MCP Auto-Installer ===")
    
    # 1. Setup virtual environment
    if not venv_dir.exists():
        print("Creating virtual environment (.venv)...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    
    # Determine python executable path in venv
    if os.name == "nt":
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:
        python_exe = venv_dir / "bin" / "python"
        
    # 2. Install dependencies
    print("Installing packages and dependencies in editable mode...")
    subprocess.run([str(python_exe), "-m", "pip", "install", "-e", "."], cwd=str(repo_root), check=True)
    
    # 3. Locate and configure targets
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", ""))
        claude_path = appdata / "Claude" / "claude_desktop_config.json"
        code_path = appdata / "Code" / "User" / "globalStorage"
        cursor_path = appdata / "Cursor" / "User" / "globalStorage"
    elif sys.platform == "darwin":
        home = Path.home()
        claude_path = home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        code_path = home / "Library" / "Application Support" / "Code" / "User" / "globalStorage"
        cursor_path = home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage"
    else: # Linux
        home = Path.home()
        claude_path = home / ".config" / "Claude" / "claude_desktop_config.json"
        code_path = home / ".config" / "Code" / "User" / "globalStorage"
        cursor_path = home / ".config" / "Cursor" / "User" / "globalStorage"

    targets = []
    # Always attempt to configure Claude Desktop and Gemini-compatible MCP config.
    targets.append(("Claude Desktop", claude_path, True))
    
    # Gemini-compatible MCP config path (cross-platform)
    gemini_mcp_path = Path.home() / ".gemini" / "config" / "mcp_config.json"
    targets.append(("Gemini MCP config", gemini_mcp_path, True))

    # Cursor Native config path (cross-platform)
    cursor_native_path = Path.home() / ".cursor" / "mcp.json"
    targets.append(("Cursor Native", cursor_native_path, True))

    # VS Code Native User config path (cross-platform)
    vscode_native_user_path = code_path.parent / "mcp.json"
    targets.append(("VS Code Native (User)", vscode_native_user_path, True))

    # VS Code Native Workspace config path
    vscode_native_workspace_path = repo_root / ".vscode" / "mcp.json"
    targets.append(("VS Code Native (Workspace)", vscode_native_workspace_path, True))

    # Continue Global config path (cross-platform)
    continue_global_path = Path.home() / ".continue" / "mcpServers" / "config.json"
    targets.append(("Continue (Global)", continue_global_path, True))

    # Continue Workspace config path
    continue_workspace_path = repo_root / ".continue" / "mcpServers" / "config.json"
    targets.append(("Continue (Workspace)", continue_workspace_path, True))

    # OpenCode Workspace config
    opencode_workspace_path = repo_root / "opencode.json"
    targets.append(("OpenCode", opencode_workspace_path, True))


    # Cline & Roo-Code for VS Code and Cursor
    extensions = [
        ("VS Code Cline", code_path / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"),
        ("VS Code Roo-Code", code_path / "roovet.roo-cline" / "settings" / "cline_mcp_settings.json"),
        ("Cursor Cline", cursor_path / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"),
        ("Cursor Roo-Code", cursor_path / "roovet.roo-cline" / "settings" / "cline_mcp_settings.json"),
    ]
    
    for name, path, *rest in [e + (False,) for e in extensions]:
        # Only configure if the parent directory exists (extension is installed)
        if path.parent.parent.exists():
            targets.append((name, path, False))

    print("\nConfiguring MCP Clients...")
    for name, path, force_create in targets:
        print(f"  Configuring {name}...")
        
        # Load or initialize config
        config = {}
        if path.exists():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"    Warning: Failed to read existing config: {e}. Starting fresh.")
                
        is_vscode_native = "VS Code Native" in name
        is_opencode = "OpenCode" in name
        
        if is_opencode:
            config_key = "mcp"
        else:
            config_key = "servers" if is_vscode_native else "mcpServers"

        if config_key not in config:
            config[config_key] = {}
            
        # Determine command and env PYTHONPATH to write
        if name == "VS Code Native (Workspace)":
            python_exe_str = "${workspaceFolder}/.venv/Scripts/python.exe" if os.name == "nt" else "${workspaceFolder}/.venv/bin/python"
            pythonpath_str = "${workspaceFolder}/src"
        else:
            python_exe_str = str(python_exe)
            pythonpath_str = str(repo_root / "src")

        if is_opencode:
            config[config_key][SERVER_ID] = {
                "type": "local",
                "command": [python_exe_str, "-m", MODULE_NAME],
                "enabled": True,
                "environment": {
                    "PYTHONPATH": pythonpath_str
                }
            }
        else:
            config[config_key][SERVER_ID] = {
                "command": python_exe_str,
                "args": ["-m", MODULE_NAME],
                "env": {
                    "PYTHONPATH": pythonpath_str
                }
            }

        
        # Write back config
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(config, indent=2), encoding="utf-8")
            print(f"    Success: Configured '{SERVER_ID}' server.")
        except Exception as e:
            print(f"    Error: Failed to write config file: {e}")
            
    # 4. Configure Codex (config.toml)
    configure_codex(python_exe, repo_root)

    # 5. Configure Global Agents Rules
    configure_global_agents_rules()

    # 6. Configure Supporting Agents Rules
    configure_supporting_agents(repo_root)

    # 7. Configure Workspace Rules for common Coding Agents
    configure_workspace_rules(repo_root)
            
    print("\n=== Installation Completed Successfully! ===")
    print("Restart your IDE / MCP Client to start using the server.")

def configure_workspace_rules(repo_root):
    targets = [
        (".cursorrules", repo_root / ".cursorrules"),
        (".clinerules", repo_root / ".clinerules"),
        (".copilotrules", repo_root / ".copilotrules")
    ]
    print("  Configuring Workspace Coding Agent Rules...")
    rule_block = (
        "\n"
        "## Agent Guidance MCP Server Tool Usage\n\n"
        "Whenever the user prompts you to perform any coding action, repository lookup, refactoring, or planning, you MUST involve the custom `agent-guidance-mcp` server tools.\n\n"
        "### Rules:\n"
        "1. **Always Start with Context Gathering**: Before you read files or make changes, invoke `task_pipeline` or `project_context(operation=\"tree\" / \"search\" / \"read\")` to load optimized project states.\n"
        "2. **Consult Standards**: Use the `guidance` tool (with `operation=\"search\"` or `operation=\"recommend\"`) to check if any coding standard or instruction applies to the implementation.\n"
        "3. **Minimize Tokens**: Ensure that you leverage the optimized output of the MCP server tools to run context-efficient development.\n"
        "4. **Enforce Execution**: Never perform direct filesystem lookups or file reads manually if the corresponding context can be loaded and optimized through the MCP server tools.\n"
    )
    for name, path in targets:
        try:
            content = ""
            if path.exists():
                content = path.read_text(encoding="utf-8")
            
            if "Agent Guidance MCP Server Tool Usage" not in content:
                with path.open("a", encoding="utf-8") as f:
                    if content and not content.endswith("\n"):
                        f.write("\n")
                    f.write(rule_block)
                print(f"    Success: Appended global agent rules to {name}")
            else:
                print(f"    Note: Agent rules already present in {name}")
        except Exception as e:
            print(f"    Error: Failed to configure {name}: {e}")

def configure_supporting_agents(repo_root):

    agents_dir = repo_root / "agents"
    if not agents_dir.exists() or not agents_dir.is_dir():
        print("  No supporting agents directory found.")
        return
        
    print("  Configuring Supporting Agents MCP Rules...")
    rule_block = (
        "\n"
        "## Agent Guidance MCP Server Tool Usage\n\n"
        "Whenever the user prompts you to perform any coding action, repository lookup, refactoring, or planning, you MUST involve the custom `agent-guidance-mcp` server tools.\n\n"
        "### Rules:\n"
        "1. **Always Start with Context Gathering**: Before you read files or make changes, invoke `task_pipeline` or `project_context(operation=\"tree\" / \"search\" / \"read\")` to load optimized project states.\n"
        "2. **Consult Standards**: Use the `guidance` tool (with `operation=\"search\"` or `operation=\"recommend\"`) to check if any coding standard or instruction applies to the implementation.\n"
        "3. **Minimize Tokens**: Ensure that you leverage the optimized output of the MCP server tools to run context-efficient development.\n"
        "4. **Enforce Execution**: Never perform direct filesystem lookups or file reads manually if the corresponding context can be loaded and optimized through the MCP server tools.\n"
    )
    for agent_file in agents_dir.glob("*.md"):
        try:
            content = agent_file.read_text(encoding="utf-8")
            if "Agent Guidance MCP Server Tool Usage" not in content:
                with agent_file.open("a", encoding="utf-8") as f:
                    if content and not content.endswith("\n"):
                        f.write("\n")
                    f.write(rule_block)
                print(f"    Success: Appended global agent rules to {agent_file.name}")
            else:
                print(f"    Note: Agent rules already present in {agent_file.name}")
        except Exception as e:
            print(f"    Error: Failed to configure supporting agent {agent_file.name}: {e}")

def configure_global_agents_rules():

    global_agents_md = Path.home() / ".gemini" / "config" / "AGENTS.md"
    print("  Configuring Global Agent Guidance MCP Rules...")
    rule_block = (
        "\n"
        "## Agent Guidance MCP Server Tool Usage\n\n"
        "Whenever the user prompts you to perform any coding action, repository lookup, refactoring, or planning, you MUST involve the custom `agent-guidance-mcp` server tools.\n\n"
        "### Rules:\n"
        "1. **Always Start with Context Gathering**: Before you read files or make changes, invoke `task_pipeline` or `project_context(operation=\"tree\" / \"search\" / \"read\")` to load optimized project states.\n"
        "2. **Consult Standards**: Use the `guidance` tool (with `operation=\"search\"` or `operation=\"recommend\"`) to check if any coding standard or instruction applies to the implementation.\n"
        "3. **Minimize Tokens**: Ensure that you leverage the optimized output of the MCP server tools to run context-efficient development.\n"
        "4. **Enforce Execution**: Never perform direct filesystem lookups or file reads manually if the corresponding context can be loaded and optimized through the MCP server tools.\n"
    )
    try:
        global_agents_md.parent.mkdir(parents=True, exist_ok=True)
        content = ""
        if global_agents_md.exists():
            content = global_agents_md.read_text(encoding="utf-8")
        
        if "Agent Guidance MCP Server Tool Usage" not in content:
            with global_agents_md.open("a", encoding="utf-8") as f:
                if content and not content.endswith("\n"):
                    f.write("\n")
                f.write(rule_block)
            print(f"    Success: Appended global agent rules to {global_agents_md}")
        else:
            print(f"    Note: Global agent rules already present in {global_agents_md}")
    except Exception as e:
        print(f"    Error: Failed to configure Global Agent Guidance MCP Rules: {e}")


def configure_codex(python_exe, repo_root):
    targets = [
        ("Global Codex config", Path.home() / ".codex" / "config.toml"),
        ("Project-local Codex config", repo_root / ".codex" / "config.toml")
    ]
    
    python_exe_str = str(python_exe).replace("\\", "\\\\")
    pythonpath_str = str(repo_root / "src").replace("\\", "\\\\")
    
    new_block = [
        f"[mcp_servers.{SERVER_ID}]",
        f'command = "{python_exe_str}"',
        f'args = ["-m", "{MODULE_NAME}"]',
        "",
        f"[mcp_servers.{SERVER_ID}.env]",
        f'PYTHONPATH = "{pythonpath_str}"',
        ""
    ]
    
    for name, config_path in targets:
        print(f"  Configuring {name}...")
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            content = ""
            if config_path.exists():
                content = config_path.read_text(encoding="utf-8")
                
            # Parse and replace owned current blocks while preserving unrelated blocks.
            lines = content.splitlines()
            new_lines = []
            block_found = False
    
            def matching_server_id(header):
                header_stripped = header.strip("[]")
                if header_stripped == f"mcp_servers.{SERVER_ID}" or header_stripped.startswith(f"mcp_servers.{SERVER_ID}."):
                    return SERVER_ID
                return None
    
            index = 0
            while index < len(lines):
                line = lines[index]
                stripped = line.strip()
                server_id = matching_server_id(stripped)
                if server_id is None:
                    new_lines.append(line)
                    index += 1
                    continue
    
                block_lines = [line]
                index += 1
                while index < len(lines) and not lines[index].strip().startswith("["):
                    block_lines.append(lines[index])
                    index += 1
    
                block_text = "\n".join(block_lines)
                if server_id == SERVER_ID:
                    if not block_found:
                        block_found = True
                        new_lines.extend(new_block[:-1]) # add new block without the trailing newline
                    continue
                new_lines.extend(block_lines)
                
            if not block_found:
                if new_lines and new_lines[-1] != "":
                    new_lines.append("")
                new_lines.extend(new_block)
                
            config_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            print(f"    Success: Configured '{SERVER_ID}' server in {name}.")
        except Exception as e:
            print(f"    Error: Failed to configure {name}: {e}")

if __name__ == "__main__":
    main()

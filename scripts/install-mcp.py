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


AGENT_RULES_BLOCK = (
    "\n"
    "## Agent Guidance MCP — Tool Selection Priority\n\n"
    "| You need to... | Use THIS tool first | Why |\n"
    "|---|---|---|\n"
    "| Start any coding task | `task_pipeline(task=\"...\")` | Recommendations + tree + code search + UI in ONE call |\n"
    "| Check coding standards | `guidance(operation=\"search\", query=\"...\")` | No other tool provides standards or skill lookup |\n"
    "| Read a file | `project_context(operation=\"read\", relative_path=\"...\")` | Token-capped at 300 lines — prevents context blowout |\n"
    "| Search codebase text | `project_context(operation=\"search\", query=\"...\")` | Ranked, bounded results. Fallback when codegraph unavailable |\n"
    "| Understand code structure | `project_context(operation=\"structure\", relative_path=\"...\")` | Hierarchical view of classes, methods, functions in a file |\n"
    "| Extract symbols | `project_context(operation=\"symbols\", relative_path=\"...\")` | Flat list of classes, functions, methods with signatures |\n"
    "| Find symbol references | `project_context(operation=\"references\", query=\"...\")` | Locate all usages of a symbol across the codebase |\n"
    "| Get UI/design guidance | `ui_ux(operation=\"search\", query=\"...\")` | Style, colors, typography, charts, slides |\n"
    "| Browse project tree | `project_context(operation=\"tree\")` | Optimized directory tree view |\n\n"
    "### Six Mandatory Rules\n\n"
    "1. **Context First**: Call `task_pipeline` or `project_context` BEFORE any file read or code change.\n"
    "2. **Standards Check**: Use `guidance(operation=\"search\")` BEFORE implementing.\n"
    "3. **Token Budget**: Prefer MCP tools over raw file reads — built-in limits prevent context blowout.\n"
    "4. **No Direct FS**: Never manually read/search files when MCP tools do it with optimization.\n"
    "5. **Ground & Plan**: Verify files/functions/symbols via search BEFORE proposing changes. Never guess.\n"
    "6. **300 LOC Cap**: Split files exceeding 300 lines of code. No monolithic files.\n\n"
    "**CRITICAL: All 6 rules apply to EVERY coding action without exception.**\n"
)


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
            project_root_str = "${workspaceFolder}"
        else:
            python_exe_str = str(python_exe)
            pythonpath_str = str(repo_root / "src")
            project_root_str = str(repo_root)

        if is_opencode:
            config[config_key][SERVER_ID] = {
                "type": "local",
                "command": [python_exe_str, "-m", MODULE_NAME],
                "enabled": True,
                "environment": {
                    "PYTHONPATH": pythonpath_str,
                    "AGENT_PROJECT_ROOT": project_root_str
                }
            }
            # Add instructions so OpenCode loads AGENTS.md as system prompt
            instructions = config.get("instructions", [])
            agends_md = "AGENTS.md"
            if agends_md not in instructions:
                instructions.append(agends_md)
                config["instructions"] = instructions
        else:
            config[config_key][SERVER_ID] = {
                "command": python_exe_str,
                "args": ["-m", MODULE_NAME],
                "env": {
                    "PYTHONPATH": pythonpath_str,
                    "AGENT_PROJECT_ROOT": project_root_str
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

    # 8. Configure OpenCode .opencode/ directory (agents, skills)
    configure_opencode_directory(repo_root)

    # 9. Configure OpenCode global config (~/.config/opencode/opencode.json)
    configure_opencode_global(python_exe, repo_root)
            
    print("\n=== Installation Completed Successfully! ===")
    print("Restart your IDE / MCP Client to start using the server.")

def configure_opencode_directory(repo_root):
    opencode_dir = repo_root / ".opencode"

    print("  Configuring OpenCode .opencode/ directory...")

    # Copy agent persona files to .opencode/agents/
    agents_src = repo_root / "agents"
    agents_dst = opencode_dir / "agents"
    if agents_src.exists() and agents_src.is_dir():
        agents_dst.mkdir(parents=True, exist_ok=True)
        copied = 0
        for agent_file in agents_src.glob("*.md"):
            try:
                content = agent_file.read_text(encoding="utf-8")
                dest_file = agents_dst / agent_file.name
                dest_file.write_text(content, encoding="utf-8")
                copied += 1
            except Exception as e:
                print(f"    Error: Failed to copy agent {agent_file.name}: {e}")
        if copied > 0:
            print(f"    Success: Copied {copied} agent(s) to .opencode/agents/")
        else:
            print("    Note: No agent files found to copy.")
    else:
        print("    Note: No agents/ directory in repo root.")

    # Ensure .opencode/skills reference exists
    skills_ref = opencode_dir / "skills"
    expected_ref = "../skills/"
    if skills_ref.exists():
        current = skills_ref.read_text(encoding="utf-8").strip()
        if current != expected_ref:
            skills_ref.write_text(expected_ref + "\n", encoding="utf-8")
            print(f"    Success: Updated .opencode/skills reference.")
        else:
            print(f"    Note: .opencode/skills reference already correct.")
    else:
        skills_ref.write_text(expected_ref + "\n", encoding="utf-8")
        print(f"    Success: Created .opencode/skills reference.")


def configure_opencode_global(python_exe, repo_root):
    opencode_global_dir = Path.home() / ".config" / "opencode"
    opencode_global_path = opencode_global_dir / "opencode.json"

    print("  Configuring OpenCode global config (~/.config/opencode/opencode.json)...")

    python_exe_str = str(python_exe)
    pythonpath_str = str(repo_root / "src")

    config = {}
    if opencode_global_path.exists():
        try:
            config = json.loads(opencode_global_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"    Warning: Failed to read existing global config: {e}. Starting fresh.")

    if "mcp" not in config:
        config["mcp"] = {}

    config["mcp"][SERVER_ID] = {
        "type": "local",
        "command": [python_exe_str, "-m", MODULE_NAME],
        "enabled": True,
        "environment": {
            "PYTHONPATH": pythonpath_str,
            "AGENT_PROJECT_ROOT": str(repo_root)
        }
    }

    if "$schema" not in config:
        config["$schema"] = "https://opencode.ai/config.json"

    try:
        opencode_global_dir.mkdir(parents=True, exist_ok=True)
        opencode_global_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        print(f"    Success: Configured 'agent-guidance-mcp' server in global OpenCode config.")
    except Exception as e:
        print(f"    Error: Failed to write global OpenCode config: {e}")


def configure_workspace_rules(repo_root):
    targets = [
        (".cursorrules", repo_root / ".cursorrules"),
        (".clinerules", repo_root / ".clinerules"),
        (".copilotrules", repo_root / ".copilotrules")
    ]
    print("  Configuring Workspace Coding Agent Rules...")
    for name, path in targets:
        try:
            content = ""
            if path.exists():
                content = path.read_text(encoding="utf-8")
            
            if "Agent Guidance MCP — Tool Selection Priority" not in content:
                with path.open("a", encoding="utf-8") as f:
                    if content and not content.endswith("\n"):
                        f.write("\n")
                    f.write(AGENT_RULES_BLOCK)
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
    for agent_file in agents_dir.glob("*.md"):
        try:
            content = agent_file.read_text(encoding="utf-8")
            if "Agent Guidance MCP — Tool Selection Priority" not in content:
                with agent_file.open("a", encoding="utf-8") as f:
                    if content and not content.endswith("\n"):
                        f.write("\n")
                    f.write(AGENT_RULES_BLOCK)
                print(f"    Success: Appended global agent rules to {agent_file.name}")
            else:
                print(f"    Note: Agent rules already present in {agent_file.name}")
        except Exception as e:
            print(f"    Error: Failed to configure supporting agent {agent_file.name}: {e}")

def configure_global_agents_rules():

    global_agents_md = Path.home() / ".gemini" / "config" / "AGENTS.md"
    print("  Configuring Global Agent Guidance MCP Rules...")
    try:
        global_agents_md.parent.mkdir(parents=True, exist_ok=True)
        content = ""
        if global_agents_md.exists():
            content = global_agents_md.read_text(encoding="utf-8")
        
        if "Agent Guidance MCP — Tool Selection Priority" not in content:
            with global_agents_md.open("a", encoding="utf-8") as f:
                if content and not content.endswith("\n"):
                    f.write("\n")
                f.write(AGENT_RULES_BLOCK)
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
    project_root_str = str(repo_root).replace("\\", "\\\\")
    
    new_block = [
        f"[mcp_servers.{SERVER_ID}]",
        f'command = "{python_exe_str}"',
        f'args = ["-m", "{MODULE_NAME}"]',
        "",
        f"[mcp_servers.{SERVER_ID}.env]",
        f'PYTHONPATH = "{pythonpath_str}"',
        f'AGENT_PROJECT_ROOT = "{project_root_str}"',
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

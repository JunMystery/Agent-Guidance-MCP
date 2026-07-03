"""Post-install configuration and IDE client registration for Agent Guidance MCP."""

import os
import sys
import json
import shutil
from pathlib import Path

SERVER_ID = "agent-guidance-mcp"
MODULE_NAME = "agent_guidance_mcp"

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

def get_executable_path() -> str:
    # Try to find the standalone binary
    exe_name = "agent-guidance-mcp.exe" if os.name == "nt" else "agent-guidance-mcp"
    which_path = shutil.which(exe_name)
    if which_path:
        return which_path
        
    # Check if run as a script wrapper
    if "agent-guidance-mcp" in sys.argv[0]:
        return sys.argv[0]
        
    # Fallback to sys.executable
    return sys.executable

def configure_mcp_clients(executable: str):
    print("\nConfiguring MCP Clients...")
    
    # Resolve OS-specific settings paths
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

    targets = [
        ("Claude Desktop", claude_path, True),
        ("Gemini MCP config", Path.home() / ".gemini" / "config" / "mcp_config.json", True),
        ("Cursor Native", Path.home() / ".cursor" / "mcp.json", True),
        ("VS Code Native (User)", code_path.parent / "mcp.json", True),
        ("Continue (Global)", Path.home() / ".continue" / "mcpServers" / "config.json", True)
    ]

    # Cline & Roo-Code extensions
    extensions = [
        ("VS Code Cline", code_path / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"),
        ("VS Code Roo-Code", code_path / "roovet.roo-cline" / settings_path()),
        ("Cursor Cline", cursor_path / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"),
        ("Cursor Roo-Code", cursor_path / "roovet.roo-cline" / settings_path()),
    ]
    for name, path in extensions:
        if path.parent.parent.exists():
            targets.append((name, path, False))

    is_script = executable == sys.executable
    cmd_args = [executable] if not is_script else [executable, "-m", MODULE_NAME]

    for name, path, force_create in targets:
        if not force_create and not path.parent.parent.exists():
            continue
            
        print(f"  Configuring {name}...")
        config = {}
        if path.exists():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"    Warning: Failed to read config {path.name}: {e}. Starting fresh.")

        config_key = "servers" if "VS Code Native" in name else "mcpServers"
        if config_key not in config:
            config[config_key] = {}

        config[config_key][SERVER_ID] = {
            "command": cmd_args[0],
            "args": cmd_args[1:]
        }

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(config, indent=2), encoding="utf-8")
            print(f"    Success: Registered '{SERVER_ID}'.")
        except Exception as e:
            print(f"    Error: Failed to write config: {e}")

def settings_path() -> Path:
    return Path("settings") / "cline_mcp_settings.json"

def configure_global_rules():
    print("\nConfiguring Global rules (~/.gemini/config/AGENTS.md)...")
    global_config_dir = Path.home() / ".gemini" / "config"
    agents_md = global_config_dir / "AGENTS.md"

    try:
        global_config_dir.mkdir(parents=True, exist_ok=True)
        content = ""
        if agents_md.exists():
            content = agents_md.read_text(encoding="utf-8")

        if "Agent Guidance MCP" not in content:
            new_content = content + AGENT_RULES_BLOCK
            agents_md.write_text(new_content, encoding="utf-8")
            print("    Success: Appended agent rules to global AGENTS.md.")
        else:
            print("    Note: Agent rules already configured in global AGENTS.md.")
    except Exception as e:
        print(f"    Error: Failed to configure global rules: {e}")

def run_setup() -> None:
    print("=== Agent Guidance MCP Setup ===")
    exe = get_executable_path()
    print(f"Using executable: {exe}")
    configure_mcp_clients(exe)
    configure_global_rules()
    print("\n=== Setup completed successfully! ===")
    print("Restart your IDE / MCP Client to apply the configuration.")

def remove_mcp_clients():
    print("\nRemoving MCP Clients registrations...")
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

    targets = [
        ("Claude Desktop", claude_path),
        ("Gemini MCP config", Path.home() / ".gemini" / "config" / "mcp_config.json"),
        ("Cursor Native", Path.home() / ".cursor" / "mcp.json"),
        ("VS Code Native (User)", code_path.parent / "mcp.json"),
        ("Continue (Global)", Path.home() / ".continue" / "mcpServers" / "config.json")
    ]

    # Cline & Roo-Code extensions
    extensions = [
        ("VS Code Cline", code_path / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"),
        ("VS Code Roo-Code", code_path / "roovet.roo-cline" / settings_path()),
        ("Cursor Cline", cursor_path / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"),
        ("Cursor Roo-Code", cursor_path / "roovet.roo-cline" / settings_path()),
    ]
    for name, path in extensions:
        if path.parent.parent.exists():
            targets.append((name, path))

    for name, path in targets:
        if not path.exists():
            continue
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
            config_key = "servers" if "VS Code Native" in name else "mcpServers"
            if config_key in config and SERVER_ID in config[config_key]:
                del config[config_key][SERVER_ID]
                path.write_text(json.dumps(config, indent=2), encoding="utf-8")
                print(f"    Success: Removed '{SERVER_ID}' registration from {name}.")
        except Exception as e:
            print(f"    Error updating config {name}: {e}")

def remove_global_rules():
    print("\nRemoving global configuration and directories...")
    global_config_dir = Path.home() / ".gemini" / "config"
    agents_md = global_config_dir / "AGENTS.md"
    if agents_md.exists():
        try:
            content = agents_md.read_text(encoding="utf-8")
            if AGENT_RULES_BLOCK in content:
                content = content.replace(AGENT_RULES_BLOCK, "")
                agents_md.write_text(content, encoding="utf-8")
                print("    Success: Removed agent rules block from global AGENTS.md.")
        except Exception as e:
            print(f"    Error updating global AGENTS.md: {e}")
            
    # Remove ~/.agent-guidance directory
    agent_guidance_dir = Path.home() / ".agent-guidance"
    if agent_guidance_dir.exists() and agent_guidance_dir.is_dir():
        try:
            shutil.rmtree(agent_guidance_dir)
            print("    Success: Deleted ~/.agent-guidance directory.")
        except Exception as e:
            print(f"    Error deleting ~/.agent-guidance: {e}")

def run_uninstall() -> None:
    print("=== Agent Guidance MCP Uninstall ===")
    remove_mcp_clients()
    remove_global_rules()
    print("\n=== Uninstall completed successfully! ===")
    print("Client configurations cleared. You can now safely uninstall the python package.")

if __name__ == "__main__":
    run_setup()

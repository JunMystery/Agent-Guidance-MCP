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
    "| Persist/recover session | `session_continuity(operation=\"save\"/\"load\"/\"clear\")` | State recovery / task checklist continuity |\n"
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
    exe_name = "agent-guidance-mcp.exe" if os.name == "nt" else "agent-guidance-mcp"
    which_path = shutil.which(exe_name)
    if which_path:
        return which_path
    if "agent-guidance-mcp" in sys.argv[0]:
        return sys.argv[0]
    return sys.executable

def configure_mcp_clients(executable: str):
    print("\nConfiguring MCP Clients...")
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
    else:
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
                print(f"    Warning: Failed to read config: {e}. Starting fresh.")

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

def configure_opencode(executable: str):
    print("\nConfiguring OpenCode & OMO...")
    opencode_global_dir = Path.home() / ".config" / "opencode"
    opencode_global_path = opencode_global_dir / "opencode.json"
    
    is_script = executable == sys.executable
    cmd_args = [executable] if not is_script else [executable, "-m", MODULE_NAME]

    targets = [(opencode_global_path, True)]
    if (Path.cwd() / "pyproject.toml").exists():
        targets.append((Path.cwd() / "opencode.json", False))

    for path, is_global in targets:
        config = {}
        if path.exists():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"    Warning: Failed to read OpenCode config: {e}")

        if "mcp" not in config:
            config["mcp"] = {}

        config["mcp"][SERVER_ID] = {
            "type": "local",
            "command": cmd_args,
            "enabled": True,
            "environment": {}
        }

        instructions = config.get("instructions", [])
        agents_md = "AGENTS.md"
        if agents_md not in instructions:
            instructions.append(agents_md)
            config["instructions"] = instructions

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(config, indent=2), encoding="utf-8")
            print(f"    Success: Configured '{SERVER_ID}' in OpenCode config: {path.name}")
        except Exception as e:
            print(f"    Error: Failed to write OpenCode config: {e}")

def configure_codex(executable: str):
    print("\nConfiguring Codex...")
    is_script = executable == sys.executable
    cmd_args = [executable] if not is_script else [executable, "-m", MODULE_NAME]

    targets = [("Global Codex config", Path.home() / ".codex" / "config.toml")]
    if (Path.cwd() / "pyproject.toml").exists():
        targets.append(("Project-local Codex config", Path.cwd() / ".codex" / "config.toml"))

    exe_str = str(cmd_args[0]).replace("\\", "\\\\")
    args_str = ", ".join(f'"{a}"' for a in cmd_args[1:]).replace("\\", "\\\\")

    new_block = [
        f"[mcp_servers.{SERVER_ID}]",
        f'command = "{exe_str}"',
    ]
    if cmd_args[1:]:
        new_block.append(f'args = [{args_str}]')
    new_block.append("")

    for name, config_path in targets:
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            content = ""
            if config_path.exists():
                content = config_path.read_text(encoding="utf-8")

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

                if server_id == SERVER_ID:
                    if not block_found:
                        block_found = True
                        new_lines.extend(new_block[:-1])
                    continue
                new_lines.extend(block_lines)

            if not block_found:
                if new_lines and new_lines[-1] != "":
                    new_lines.append("")
                new_lines.extend(new_block)

            config_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            print(f"    Success: Configured '{SERVER_ID}' in {name}.")
        except Exception as e:
            print(f"    Error: Failed to configure {name}: {e}")

def configure_global_rules():
    print("\nConfiguring Global rules (~/.gemini/config/AGENTS.md)...")
    global_config_dir = Path.home() / ".gemini" / "config"
    agents_md = global_config_dir / "AGENTS.md"
    try:
        global_config_dir.mkdir(parents=True, exist_ok=True)
        content = ""
        if agents_md.exists():
            content = agents_md.read_text(encoding="utf-8")

        if "Agent Guidance MCP — Tool Selection Priority" not in content:
            new_content = content + AGENT_RULES_BLOCK
            agents_md.write_text(new_content, encoding="utf-8")
            print("    Success: Appended agent rules to global AGENTS.md.")
        else:
            print("    Note: Agent rules already configured in global AGENTS.md.")
    except Exception as e:
        print(f"    Error: Failed to configure global rules: {e}")

def configure_workspace_rules():
    if not (Path.cwd() / "pyproject.toml").exists():
        return
    targets = [
        (".cursorrules", Path.cwd() / ".cursorrules"),
        (".clinerules", Path.cwd() / ".clinerules"),
        (".copilotrules", Path.cwd() / ".copilotrules"),
        (".codexrules", Path.cwd() / ".codexrules"),
        ("AGENTS.md", Path.cwd() / "AGENTS.md"),
    ]
    print("\nConfiguring Workspace Coding Agent Rules...")
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
                print(f"    Success: Appended agent rules to local {name}")
            else:
                print(f"    Note: Agent rules already present in local {name}")
        except Exception as e:
            print(f"    Error: Failed to configure {name}: {e}")

def run_setup(mode: str = "auto", selected: set[int] | None = None) -> None:
    """Run post-install configuration.

    Args:
        mode: 'auto' (configure all) or 'manual' (show menu)
        selected: set of component indices to configure (manual mode only)
    """
    print("=== Agent Guidance MCP Setup ===")
    exe = get_executable_path()
    print(f"Using executable: {exe}")

    # All setup steps in order, with recommended defaults marked
    steps = [
        (1, "MCP Clients (Claude, Gemini, Cursor, VS Code, Continue)", lambda: configure_mcp_clients(exe), True),
        (2, "OpenCode & OMO", lambda: configure_opencode(exe), True),
        (3, "Codex (global + project-local)", lambda: configure_codex(exe), False),
        (4, "Global Agent Rules", configure_global_rules, True),
        (5, "Workspace Rules (.cursorrules, .clinerules, etc.)", configure_workspace_rules, False),
    ]

    if mode == "manual":
        selected = manual_select_components(steps)

    for index, _, fn, _ in steps:
        if selected is None or index in selected:
            fn()

    print("\n=== Setup completed successfully! ===")
    print("Restart your IDE / MCP Client to apply the configuration.")


PAGE_SIZE = 9


def manual_select_components(steps: list[tuple[int, str, object, bool]]) -> set[int]:
    """Interactive paginated checklist for manual install mode.

    Pages items in groups of PAGE_SIZE. 'n' for next page, '0' to go back.
    Returns set of selected component indices.
    """
    selected: set[int] = {idx for idx, _, _, rec in steps if rec}
    page = 0
    total_pages = (len(steps) + PAGE_SIZE - 1) // PAGE_SIZE

    while True:
        start = page * PAGE_SIZE
        page_items = steps[start:start + PAGE_SIZE]

        print(f"\n  ── Page {page + 1}/{total_pages} ──")
        for i, (idx, name, _, rec) in enumerate(page_items):
            mark = "\u2713" if idx in selected else " "
            tag = " (recommended)" if rec else ""
            print(f"  [{i + 1}]  {mark}  {name}{tag}")

        if total_pages > 1:
            if page > 0:
                print(f"  [0]  ── back ──")
            if page < total_pages - 1:
                print(f"  [n]  ── next page ──")
        print(f"\n  Enter numbers to toggle, or press Enter to confirm: ")

        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.")
            return selected

        if choice == "":
            break
        if choice == "n" and page < total_pages - 1:
            page += 1
            continue
        if choice == "0" and page > 0:
            page -= 1
            continue
        if choice == "0" and page == 0:
            print("  Returning to main menu...")
            return set()

        for token in choice.split():
            try:
                num = int(token)
                if 1 <= num <= len(page_items):
                    real_idx = steps[start + num - 1][0]
                    if real_idx in selected:
                        selected.discard(real_idx)
                    else:
                        selected.add(real_idx)
            except ValueError:
                pass

    return selected

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
    else:
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

def remove_opencode_and_codex():
    print("\nRemoving OpenCode, OMO, and Codex registrations...")
    opencode_global_path = Path.home() / ".config" / "opencode" / "opencode.json"
    local_opencode = Path.cwd() / "opencode.json"
    
    for path in [opencode_global_path, local_opencode]:
        if path.exists():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
                if "mcp" in config and SERVER_ID in config["mcp"]:
                    del config["mcp"][SERVER_ID]
                    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
                    print(f"    Success: Removed '{SERVER_ID}' from OpenCode config {path.name}")
            except Exception as e:
                print(f"    Error updating OpenCode config {path}: {e}")

    # Remove Codex block
    codex_paths = [Path.home() / ".codex" / "config.toml", Path.cwd() / ".codex" / "config.toml"]
    for path in codex_paths:
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                lines = content.splitlines()
                new_lines = []
                index = 0
                while index < len(lines):
                    line = lines[index]
                    stripped = line.strip()
                    if stripped == f"[mcp_servers.{SERVER_ID}]" or stripped.startswith(f"[mcp_servers.{SERVER_ID}."):
                        index += 1
                        while index < len(lines) and not lines[index].strip().startswith("["):
                            index += 1
                        continue
                    new_lines.append(line)
                    index += 1
                path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                print(f"    Success: Removed '{SERVER_ID}' from Codex config {path.parent.name}")
            except Exception as e:
                print(f"    Error: Failed to clean Codex config {path}: {e}")

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
    remove_opencode_and_codex()
    remove_global_rules()
    print("\n=== Uninstall completed successfully! ===")
    print("Client configurations cleared. You can now safely uninstall the python package.")

if __name__ == "__main__":
    run_setup()

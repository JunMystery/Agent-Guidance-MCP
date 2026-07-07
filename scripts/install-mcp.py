#!/usr/bin/env python3
"""Agent Guidance MCP - Cross-platform installer (mirrors install.sh / install.ps1).

Usage:
    python scripts/install-mcp.py              # interactive
    python scripts/install-mcp.py --uninstall   # uninstall everything
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

SERVER_ID = "agent-guidance-mcp"
GITHUB_URL = "git+https://github.com/JunMystery/Agent-Guidance-MCP.git"


# -- ANSI colors (Windows 10+ supports them) ----------------------------------

def _supports_color():
    try:
        return sys.stdout.isatty() and os.environ.get("TERM") != "dumb"
    except Exception:
        return False

_HAS_COLOR = _supports_color()

def c(text, color=""):
    if not _HAS_COLOR:
        return text
    codes = {"red": "31", "green": "32", "yellow": "33", "cyan": "36", "magenta": "35", "gray": "90", "bold": "1"}
    code = codes.get(color, "")
    return f"\033[{code}m{text}\033[0m" if code else text


# -- Helpers ------------------------------------------------------------------

def header():
    print()
    print(c("=" + "=" * 62, "magenta"))
    print(c("        Agent Guidance MCP Installer", "magenta"))
    print(c("=" + "=" * 62, "magenta"))
    print()


def step(num, total, msg):
    print(c(f"Step {num}/{total} - {msg}", "bold"))


def ok(msg=""):
    print(f"  {c('v', 'green')} {msg}")


def warn(msg=""):
    print(f"  {c('!', 'yellow')} {msg}")


def info(msg=""):
    print(f"  {c('>', 'magenta')} {msg}")


def run(cmd, **kwargs):
    """Run a command, exit on failure."""
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(c(f"Command failed: {' '.join(str(c) for c in cmd)}", "red"), file=sys.stderr)
        sys.exit(1)
    return result


def find_uv():
    """Find uv binary or return None."""
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path
    if os.name == "nt":
        candidate = Path.home() / ".local" / "bin" / "uv.exe"
    else:
        candidate = Path.home() / ".local" / "bin" / "uv"
    if candidate.is_file():
        return str(candidate)
    return None


def install_uv():
    """Install uv via official installer."""
    print(c("   Installing uv (fast Python package manager)...", "yellow"))
    if os.name == "nt":
        # Windows: use PowerShell installer
        ps_script = (
            "powershell -ExecutionPolicy Bypass -Command "
            "\"irm https://astral.sh/uv/install.ps1 | iex\""
        )
        os.system(ps_script)
    else:
        # Unix: use curl
        os.system("curl -LsSf https://astral.sh/uv/install.sh | sh")
    return find_uv()


def find_tool_bin():
    """Find agent-guidance-mcp binary."""
    exe_name = "agent-guidance-mcp.exe" if os.name == "nt" else "agent-guidance-mcp"
    path = shutil.which(exe_name)
    if path:
        return path
    if os.name == "nt":
        candidate = Path.home() / ".local" / "bin" / exe_name
    else:
        candidate = Path.home() / ".local" / "bin" / exe_name
    if candidate.is_file():
        return str(candidate)
    return None


# -- Uninstall ----------------------------------------------------------------

def do_uninstall():
    """Uninstall Agent Guidance MCP completely."""
    print()
    print(c("[DEL]  Uninstalling Agent Guidance MCP...", "red"))
    print()

    tool_bin = find_tool_bin()

    # Step 1: Remove IDE registrations
    step(1, 3, "Removing IDE registrations...")
    if tool_bin:
        try:
            subprocess.run([tool_bin, "--uninstall"], capture_output=True, timeout=30)
            ok("Done")
        except Exception:
            ok("Done (tool ran)")
    else:
        warn("Tool not found - skipping")

    # Step 2: Remove skills data
    print()
    step(2, 3, "Removing skills data...")
    agent_dir = Path.home() / ".agent-guidance"
    if agent_dir.exists():
        shutil.rmtree(agent_dir, ignore_errors=True)
        ok(f"Removed {c(str(agent_dir), 'gray')}")
    else:
        print(f"  {c('', 'gray')} Not found")

    # Step 3: Remove MCP server
    print()
    step(3, 3, "Removing MCP server...")
    uv = find_uv()
    if uv:
        try:
            subprocess.run([uv, "tool", "uninstall", SERVER_ID], capture_output=True, timeout=30)
            ok("Uninstalled from uv")
        except Exception:
            print(f"  {c('', 'gray')} Not found in uv")
    else:
        print(f"  {c('', 'gray')} uv not found")

    # Remove MCP server
    print()
    step(3, 3, "Removing MCP server...")
    uv = find_uv()
    if uv:
        try:
            subprocess.run([uv, "tool", "uninstall", SERVER_ID], capture_output=True, timeout=30)
            ok("Uninstalled from uv")
        except Exception:
            print(f"  {c('.', 'gray')} Not found in uv")
    else:
        print(f"  {c('.', 'gray')} uv not found")

    print()
    print(c("=" + "=" * 62, "green"))
    print(c("        Uninstallation complete!", "green"))
    print(c("=" + "=" * 62, "green"))
    print()


def kill_running_instances():
    """Kill any running agent-guidance-mcp processes to release file locks on Windows/Linux/Mac."""
    print(c("   Checking for running instances to release file locks...", "yellow"))
    if os.name == "nt":
        # Windows
        subprocess.run(["taskkill", "/f", "/im", "agent-guidance-mcp.exe"], capture_output=True)
    else:
        # Unix
        subprocess.run(["killall", "agent-guidance-mcp"], capture_output=True)
        subprocess.run(["pkill", "-f", "agent-guidance-mcp"], capture_output=True)


# -- Install ------------------------------------------------------------------

def do_install(action="1"):
    """Install Agent Guidance MCP."""
    print()

    # Step 1: Detect or install uv
    step(1, 3, "Checking Python toolchain (uv)...")
    uv = find_uv()
    if uv:
        ok(f"Found 'uv' in PATH")
    else:
        uv = install_uv()
        if uv:
            ok("uv installed")
        else:
            print(c("  Failed to install uv. Please install manually: https://docs.astral.sh/uv/", "red"))
            sys.exit(1)

    # Step 2: Install the MCP server
    print()
    step(2, 3, "Installing agent-guidance-mcp...")

    kill_running_instances()

    has_pyproject = Path("pyproject.toml").exists() or (Path(__file__).resolve().parents[1] / "pyproject.toml").exists()
    repo_root = Path(__file__).resolve().parents[1] if has_pyproject else None

    if repo_root and (repo_root / "pyproject.toml").exists():
        print(f"  {c('', 'cyan')} Found local project - installing from source...")
        result = subprocess.run([uv, "tool", "install", str(repo_root), "--force", "-q"],
                                capture_output=True, text=True)
        if result.returncode != 0:
            warn("Local install failed - falling back to GitHub...")
            run([uv, "tool", "install", GITHUB_URL, "--force"])
    else:
        print(f"  {c('[NET]', 'cyan')} Installing from GitHub repository...")
        run([uv, "tool", "install", GITHUB_URL, "--force"])
    ok("MCP server installed")

    # Resolve tool binary
    tool_bin = find_tool_bin()

    # Step 3: Post-install configuration
    print()
    step(3, 3, "Configuring IDE clients...")
    mode_flag = "--mode=ide" if action == "2" else ""

    print()
    info("Registering with detected IDEs...")
    if tool_bin:
        cmd = [tool_bin, "--setup"]
        if mode_flag:
            cmd.append(mode_flag)
        subprocess.run(cmd)
        print()
        info("Downloading skill catalog...")
        subprocess.run([tool_bin, "--update"])
    else:
        cmd = [uv, "tool", "run", SERVER_ID, "--setup"]
        if mode_flag:
            cmd.append(mode_flag)
        subprocess.run(cmd)
        print()
        info("Downloading skill catalog...")
        subprocess.run([uv, "tool", "run", SERVER_ID, "--update"])

    # Footer
    print()
    print(c("=" + "=" * 62, "green"))
    print(c("          Installation completed successfully!", "green"))
    print(c("=" + "=" * 62, "green"))
    print()
    print("  Next steps:")
    print("     Restart your IDE / MCP Client")
    print(f"     Run {c('agent-guidance-mcp --help', 'cyan')} to see options")
    print(f"     Update skills: {c('agent-guidance-mcp --update', 'cyan')}")
    print()


# -- Main ---------------------------------------------------------------------

def main():
    header()

    # Check for --uninstall flag
    if "--uninstall" in sys.argv:
        do_uninstall()
        return

    # Choose mode
    print(c("What would you like to do", "bold"))
    print(f"  {c('[1]', 'green')}  Install - auto-configure all detected IDEs")
    print(f"  {c('[2]', 'cyan')}  Install - manual (choose which IDEs to configure)")
    print(f"  {c('[3]', 'red')}  Uninstall - remove everything")
    print()

    try:
        action = input("Choice [1]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        sys.exit(1)

    if not action:
        action = "1"

    if action == "3":
        do_uninstall()
    elif action in ("1", "2"):
        do_install(action)
    else:
        print(c(f"Invalid choice: {action}", "red"))
        sys.exit(1)


if __name__ == "__main__":
    main()

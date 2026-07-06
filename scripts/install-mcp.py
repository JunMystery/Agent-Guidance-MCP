#!/usr/bin/env python3
"""Agent Guidance MCP - Cross-platform installer (mirrors install.sh / install.ps1).

Usage:
    python scripts/install-mcp.py              # interactive
    python scripts/install-mcp.py --uninstall   # uninstall everything
"""
import os
import sys
import shutil
import platform
import subprocess
import tempfile
import urllib.request
import zipfile
import tarfile
from pathlib import Path

SERVER_ID = "agent-guidance-mcp"
GITHUB_URL = "git+https://github.com/JunMystery/Agent-Guidance-MCP.git"
RTK_BASE_URL = "https://github.com/rtk-ai/rtk/releases/latest/download"


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


# -- RTK installer ------------------------------------------------------------

def install_rtk():
    """Download and install RTK (Rust Token Killer) binary."""
    step(4, 4, "Installing RTK token optimizer...")
    rtk_path = shutil.which("rtk")
    if rtk_path:
        try:
            ver = subprocess.run([rtk_path, "--version"], capture_output=True, text=True, timeout=5)
            ok(f"RTK already installed ({ver.stdout.strip()})")
        except Exception:
            ok("RTK already installed")
        return

    system = platform.system()
    machine = platform.machine().lower()

    rtk_url = None
    if system == "Windows" and machine in ("amd64", "x86_64"):
        rtk_url = f"{RTK_BASE_URL}/rtk-x86_64-pc-windows-msvc.zip"
    elif system == "Linux" and machine in ("x86_64", "amd64"):
        rtk_url = f"{RTK_BASE_URL}/rtk-x86_64-unknown-linux-musl.tar.gz"
    elif system == "Linux" and machine in ("aarch64", "arm64"):
        rtk_url = f"{RTK_BASE_URL}/rtk-aarch64-unknown-linux-gnu.tar.gz"
    elif system == "Darwin" and machine in ("x86_64", "amd64"):
        rtk_url = f"{RTK_BASE_URL}/rtk-x86_64-apple-darwin.tar.gz"
    elif system == "Darwin" and machine in ("arm64", "aarch64"):
        rtk_url = f"{RTK_BASE_URL}/rtk-aarch64-apple-darwin.tar.gz"

    if not rtk_url:
        warn(f"No pre-built RTK binary for {system}/{machine} - build from source if needed")
        return

    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    rtk_dest = bin_dir / ("rtk.exe" if os.name == "nt" else "rtk")

    print(f"  {c('', 'cyan')} Downloading RTK for {system}/{machine}...")
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".archive")
        urllib.request.urlretrieve(rtk_url, tmp.name)
        tmp.close()

        extract_dir = tempfile.mkdtemp()
        if rtk_url.endswith(".zip"):
            with zipfile.ZipFile(tmp.name) as z:
                z.extractall(extract_dir)
        else:
            with tarfile.open(tmp.name, "r:gz") as t:
                t.extractall(extract_dir)

        # Find rtk binary
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                if f == "rtk" or f == "rtk.exe":
                    shutil.copy2(os.path.join(root, f), rtk_dest)
                    if os.name != "nt":
                        rtk_dest.chmod(0o755)
                    break

        os.unlink(tmp.name)
        shutil.rmtree(extract_dir, ignore_errors=True)

        if rtk_dest.is_file():
            ok(f"RTK installed to {c(str(rtk_dest), 'gray')}")
        else:
            warn("RTK download failed - run 'agent-guidance-mcp --update' later to retry")
    except Exception as e:
        warn(f"RTK download failed ({e}) - run 'agent-guidance-mcp --update' later to retry")


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

    # Remove RTK
    rtk_path = shutil.which("rtk")
    if not rtk_path:
        rtk_path = str(Path.home() / ".local" / "bin" / ("rtk.exe" if os.name == "nt" else "rtk"))
    if Path(rtk_path).is_file():
        try:
            Path(rtk_path).unlink()
            ok("RTK removed")
        except Exception:
            pass

    print()
    print(c("=" + "=" * 62, "green"))
    print(c("        Uninstallation complete!", "green"))
    print(c("=" + "=" * 62, "green"))
    print()


# -- Install ------------------------------------------------------------------

def do_install(action="1"):
    """Install Agent Guidance MCP."""
    print()

    # Step 1: Detect or install uv
    step(1, 4, "Checking Python toolchain (uv)...")
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
    step(2, 4, "Installing agent-guidance-mcp...")

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
    step(3, 4, "Configuring IDE clients...")
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

    # Step 4: Install RTK
    print()
    install_rtk()

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

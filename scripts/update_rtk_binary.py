#!/usr/bin/env python3
"""Updates the RTK binary to the latest release from GitHub.

Downloads the pre-built binary for the current platform and replaces
the existing one at ~/.local/bin/rtk (or ~/.local/bin/rtk.exe on Windows).
No Rust toolchain required.
"""

import os
import sys
import shutil
import tempfile
import urllib.request
import zipfile
import tarfile
from pathlib import Path

RTK_RELEASES = "https://github.com/rtk-ai/rtk/releases/latest/download"


def _get_platform_url() -> str | None:
    system = os.uname().sysname if hasattr(os, "uname") else os.name
    machine = os.uname().machine if hasattr(os, "uname") else "x86_64"

    if system == "Linux":
        if machine in ("x86_64", "amd64"):
            return f"{RTK_RELEASES}/rtk-x86_64-unknown-linux-musl.tar.gz"
        if machine in ("aarch64", "arm64"):
            return f"{RTK_RELEASES}/rtk-aarch64-unknown-linux-gnu.tar.gz"
    elif system == "Darwin":
        if machine in ("x86_64", "amd64"):
            return f"{RTK_RELEASES}/rtk-x86_64-apple-darwin.tar.gz"
        if machine in ("arm64", "aarch64"):
            return f"{RTK_RELEASES}/rtk-aarch64-apple-darwin.tar.gz"
    elif os.name == "nt":
        arch = "x86_64" if "64" in os.environ.get("PROCESSOR_ARCHITECTURE", "") else "i686"
        return f"{RTK_RELEASES}/rtk-{arch}-pc-windows-msvc.zip"

    return None


def update_rtk_binary() -> bool:
    url = _get_platform_url()
    if not url:
        print("  ⚠  No pre-built RTK binary for this platform.")
        return False

    print(f"  📥 Downloading RTK from {url}...")
    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    bin_name = "rtk.exe" if os.name == "nt" else "rtk"
    target_path = bin_dir / bin_name

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        headers = {"User-Agent": "agent-guidance-mcp-updater/1.0"}
        req = urllib.request.Request(url, headers=headers)

        archive_path = tmp_dir / "rtk_archive"
        with urllib.request.urlopen(req, timeout=60) as resp, open(archive_path, "wb") as f:
            shutil.copyfileobj(resp, f)

        if url.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(tmp_dir)
        else:
            with tarfile.open(archive_path, "r:gz") as tf:
                tf.extractall(tmp_dir)

        for candidate in tmp_dir.rglob(bin_name):
            shutil.copy2(candidate, target_path)
            target_path.chmod(0o755)
            result = os.popen(f"{target_path} --version 2>&1").read().strip()
            print(f"  ✓ RTK updated: {result}")
            return True

        print("  ⚠  RTK binary not found in archive.")
        return False
    except Exception as e:
        print(f"  ⚠  RTK update failed: {e}")
        return False
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== RTK Binary Updater ===")
    ok = update_rtk_binary()
    sys.exit(0 if ok else 1)

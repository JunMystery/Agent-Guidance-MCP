#!/usr/bin/env python3
"""Downloads and updates the rtk (Rust Token Killer) subproject from GitHub."""

import os
import sys
import tempfile
import urllib.request
import zipfile
import shutil
from pathlib import Path

REPO_ZIP_URL = "https://github.com/rtk-ai/rtk/archive/refs/heads/main.zip"


def update_rtk():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    target_dir = repo_root / "rtk"

    print("=== RTK (Rust Token Killer) Auto-Updater ===")
    print(f"Target directory: {target_dir}")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "rtk.zip"

            print(f"Downloading latest rtk snapshot from: {REPO_ZIP_URL}")
            headers = {"User-Agent": "agent-guidance-mcp-updater/1.0"}
            req = urllib.request.Request(REPO_ZIP_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response, open(zip_path, "wb") as out_file:
                shutil.copyfileobj(response, out_file)

            print("Extracting archive...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)

            # Locate the extracted folder (typically 'rtk-main')
            extracted_dirs = [
                p for p in Path(tmpdir).iterdir()
                if p.is_dir() and p.name.startswith("rtk")
            ]
            if not extracted_dirs:
                print("Error: Could not find extracted rtk folder.")
                return False

            src_dir = extracted_dirs[0]
            print(f"Deploying from {src_dir.name}...")

        # Only keep what's needed to build the Rust binary (no git/CI artifacts)
        essentials = {
            "Cargo.toml",
            "Cargo.lock",
            "build.rs",
            "src",
            "tests",
            "LICENSE",
            "README.md",
        }
        # Strip git artifacts from source before deploying
        git_patterns = (".git", ".github", ".gitignore", ".gitattributes",
                        ".release-please-manifest.json", "release-please-config.json")
        for pattern in git_patterns:
            for p in src_dir.rglob(pattern):
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                elif p.is_file():
                    p.unlink(missing_ok=True)

            # Full replace: clear old, deploy fresh essentials
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)

            print("Deploying essential source files...")
            for item in src_dir.iterdir():
                if item.name not in essentials:
                    continue
                dest_item = target_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest_item)
                else:
                    shutil.copy2(item, dest_item)

            print("\u2713 RTK subproject successfully updated!")
            return True

    except Exception as e:
        print(f"Error during RTK update: {e}")
        return False


if __name__ == "__main__":
    success = update_rtk()
    sys.exit(0 if success else 1)

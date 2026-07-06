#!/usr/bin/env python3
"""Downloads and updates Anthropic Skills from GitHub."""

import sys
import tempfile
import urllib.request
import zipfile
import shutil
from pathlib import Path

REPO_ZIP_URL = "https://github.com/anthropics/skills/archive/refs/heads/main.zip"

# Source-available only (not Apache 2.0) — cannot redistribute
BLOCKLIST = {"docx", "pdf", "pptx", "xlsx"}


def update_anthropic_skills():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    target_dir = repo_root / "skills" / "anthropic-skills"

    print("=== Anthropic Skills Auto-Updater ===")
    print(f"Target directory: {target_dir}")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "anthropic-skills.zip"

            print(f"Downloading latest snapshot from: {REPO_ZIP_URL}")
            headers = {"User-Agent": "agent-guidance-mcp-updater/1.0"}
            req = urllib.request.Request(REPO_ZIP_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as response, open(zip_path, "wb") as out_file:
                shutil.copyfileobj(response, out_file)

            print("Extracting archive...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)

            # Locate the extracted folder (typically 'skills-main')
            extracted_dirs = [
                p for p in Path(tmpdir).iterdir()
                if p.is_dir() and p.name.lower().startswith("skills")
            ]
            if not extracted_dirs:
                print("Error: Could not find extracted skills folder.")
                return False

            # Navigate into the skills/ subdirectory
            src_skills_dir = extracted_dirs[0] / "skills"
            if not src_skills_dir.exists():
                print("Error: 'skills' directory not found in the extracted repository.")
                return False

            print(f"Deploying from {extracted_dirs[0].name}/skills/...")

            # Full replace: clear old, deploy fresh
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)

            skipped = []
            copied = 0
            for item in sorted(src_skills_dir.iterdir()):
                if not item.is_dir():
                    continue
                if item.name in BLOCKLIST:
                    skipped.append(item.name)
                    continue
                shutil.copytree(item, target_dir / item.name)
                copied += 1

            print(f"  Copied {copied} skill(s)")
            if skipped:
                print(f"  Skipped {len(skipped)} source-available skill(s): {', '.join(skipped)}")
            print("\u2713 Anthropic Skills successfully updated!")
            return True

    except Exception as e:
        print(f"Error during Anthropic Skills update: {e}")
        return False


if __name__ == "__main__":
    success = update_anthropic_skills()
    sys.exit(0 if success else 1)

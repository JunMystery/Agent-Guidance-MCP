#!/usr/bin/env python3
"""Downloads and updates OWASP Cheat Sheets from GitHub."""

import sys
import tempfile
import urllib.request
import zipfile
import shutil
from pathlib import Path

REPO_ZIP_URL = "https://github.com/OWASP/CheatSheetSeries/archive/refs/heads/master.zip"

# Repo metadata files, not cheat sheet content
EXCLUDE = {"Index.md", "IndexASVS.md", "IndexProactiveControls.md", "README.md"}


def update_owasp_cheatsheets():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    target_dir = repo_root / "skills" / "owasp-cheatsheets"

    print("=== OWASP Cheat Sheets Auto-Updater ===")
    print(f"Target directory: {target_dir}")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "owasp-cheatsheets.zip"

            print(f"Downloading latest snapshot from: {REPO_ZIP_URL}")
            headers = {"User-Agent": "agent-guidance-mcp-updater/1.0"}
            req = urllib.request.Request(REPO_ZIP_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as response, open(zip_path, "wb") as out_file:
                shutil.copyfileobj(response, out_file)

            print("Extracting archive...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)

            # Locate the extracted folder (typically 'CheatSheetSeries-master')
            extracted_dirs = [
                p for p in Path(tmpdir).iterdir()
                if p.is_dir() and p.name.lower().startswith("cheatsheetseries")
            ]
            if not extracted_dirs:
                print("Error: Could not find extracted CheatSheetSeries folder.")
                return False

            # Navigate into the cheatsheets/ subdirectory
            src_dir = extracted_dirs[0] / "cheatsheets"
            if not src_dir.exists():
                print("Error: 'cheatsheets' directory not found in the extracted repository.")
                return False

            # Copy LICENSE from repo root
            license_src = extracted_dirs[0] / "LICENSE"

            print(f"Deploying from {extracted_dirs[0].name}/cheatsheets/...")

            # Full replace: clear old, deploy fresh
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)

            skipped = []
            copied = 0
            for item in sorted(src_dir.iterdir()):
                if not item.is_file() or not item.suffix == ".md":
                    continue
                if item.name in EXCLUDE:
                    skipped.append(item.name)
                    continue
                shutil.copy2(item, target_dir / item.name)
                copied += 1

            # Copy license for CC BY-SA 4.0 attribution
            if license_src.is_file():
                shutil.copy2(license_src, target_dir / "LICENSE")

            print(f"  Copied {copied} cheat sheet(s)")
            if skipped:
                print(f"  Skipped {len(skipped)} index/readme file(s): {', '.join(skipped)}")
            print("\u2713 OWASP Cheat Sheets successfully updated!")
            return True

    except Exception as e:
        print(f"Error during OWASP Cheat Sheets update: {e}")
        return False


if __name__ == "__main__":
    success = update_owasp_cheatsheets()
    sys.exit(0 if success else 1)

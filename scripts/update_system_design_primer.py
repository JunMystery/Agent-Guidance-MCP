#!/usr/bin/env python3
"""Downloads and updates the System Design Primer from GitHub."""

import sys
import tempfile
import urllib.request
import zipfile
import shutil
from pathlib import Path

REPO_ZIP_URL = "https://github.com/donnemartin/system-design-primer/archive/refs/heads/master.zip"


def update_system_design_primer():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    target_dir = repo_root / "skills" / "system-design-primer"

    print("=== System Design Primer Auto-Updater ===")
    print(f"Target directory: {target_dir}")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "system-design-primer.zip"

            print(f"Downloading latest snapshot from: {REPO_ZIP_URL}")
            headers = {"User-Agent": "agent-guidance-mcp-updater/1.0"}
            req = urllib.request.Request(REPO_ZIP_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as response, open(zip_path, "wb") as out_file:
                shutil.copyfileobj(response, out_file)

            print("Extracting archive...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)

            # Locate the extracted folder (typically 'system-design-primer-master')
            extracted_dirs = [
                p for p in Path(tmpdir).iterdir()
                if p.is_dir() and p.name.lower().startswith("system-design-primer")
            ]
            if not extracted_dirs:
                print("Error: Could not find extracted system-design-primer folder.")
                return False

            src_root = extracted_dirs[0]
            solutions_src = src_root / "solutions" / "system_design"

            print(f"Deploying from {src_root.name}/...")

            # Full replace: clear old, deploy fresh
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)

            # Copy the main primer README
            readme_src = src_root / "README.md"
            if readme_src.is_file():
                shutil.copy2(readme_src, target_dir / "README.md")
                size_kb = readme_src.stat().st_size // 1024
                print(f"  Copied README.md ({size_kb} KB)")
            else:
                print("  Warning: README.md not found")

            # Copy LICENSE
            license_src = src_root / "LICENSE.txt"
            if license_src.is_file() or (src_root / "LICENSE").is_file():
                lic = license_src if license_src.is_file() else src_root / "LICENSE"
                shutil.copy2(lic, target_dir / "LICENSE")
                print(f"  Copied {lic.name}")

            # Copy solution exercise READMEs
            if solutions_src.exists():
                targets_dir = target_dir / "solutions"
                targets_dir.mkdir(exist_ok=True)
                copied = 0
                for solution_dir in sorted(solutions_src.iterdir()):
                    if not solution_dir.is_dir():
                        continue
                    solution_readme = solution_dir / "README.md"
                    if not solution_readme.is_file():
                        continue
                    dest_dir = targets_dir / solution_dir.name
                    dest_dir.mkdir(exist_ok=True)
                    shutil.copy2(solution_readme, dest_dir / "README.md")
                    copied += 1
                print(f"  Copied {copied} solution(s)")
            else:
                print("  Warning: solutions/system_design/ not found")

            print("\u2713 System Design Primer successfully updated!")
            return True

    except Exception as e:
        print(f"Error during System Design Primer update: {e}")
        return False


if __name__ == "__main__":
    success = update_system_design_primer()
    sys.exit(0 if success else 1)

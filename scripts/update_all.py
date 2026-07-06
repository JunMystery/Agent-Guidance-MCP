#!/usr/bin/env python3
"""Orchestrator: runs all MCP auto-updaters in sequence.

Usage:
    python scripts/update_all.py              # run all updates
    python scripts/update_all.py --dry-run    # show what would run (no execution)
"""

import os
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

UPDATERS = [
    ("update_ecc.py", "ECC (168-skill catalog)"),
    ("update_ui_ux.py", "UI/UX Pro Max (design data)"),
    ("update_anthropic_skills.py", "Anthropic Skills (creative, dev, enterprise)"),
    ("update_owasp_cheatsheets.py", "OWASP Cheat Sheets (~100 security references)"),
    ("update_system_design_primer.py", "System Design Primer (large-scale system design)"),
    ("update_rtk.py", "RTK — Rust Token Killer (subproject)"),
    ("update_rtk_binary.py", "RTK Binary — latest release (~/.local/bin/rtk)"),
]


def run_updater(script_name: str) -> bool:
    script_path = SCRIPT_DIR / script_name
    if not script_path.is_file():
        print(f"  SKIP — script not found: {script_name}")
        return False

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=False,
        text=True,
    )
    return result.returncode == 0


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("  Agent Guidance MCP — Auto-Update Orchestrator")
    if dry_run:
        print("  [DRY RUN — no updates will be executed]")
    print("=" * 60)
    print()

    results: dict[str, bool] = {}

    for script_name, label in UPDATERS:
        print(f"--- {label} ---")
        if dry_run:
            print(f"  Would run: python {SCRIPT_DIR / script_name}")
            results[script_name] = True
        else:
            ok = run_updater(script_name)
            results[script_name] = ok
            if not ok:
                print(f"  FAILED: {script_name}")
        print()

    # Summary
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    all_ok = True
    for script_name, label in UPDATERS:
        ok = results.get(script_name, False)
        status = "OK" if ok else "FAIL"
        print(f"  [{status:4s}] {label}")
        if not ok:
            all_ok = False

    if dry_run:
        print("\n  Dry run complete. Remove --dry-run to execute.")
    elif all_ok:
        print(f"\n  All {len(UPDATERS)} updaters passed.")
    else:
        failed = sum(1 for ok in results.values() if not ok)
        print(f"\n  {failed} updater(s) failed. Check output above.")
    print("=" * 60)

    sys.exit(0 if (dry_run or all_ok) else 1)


if __name__ == "__main__":
    main()

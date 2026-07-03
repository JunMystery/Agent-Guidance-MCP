#!/usr/bin/env python3
"""Downloads and updates the UI/UX Pro Max skill from GitHub."""

import os
import sys
import tempfile
import urllib.request
import zipfile
import shutil
from pathlib import Path

REPO_ZIP_URL = "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/archive/refs/heads/main.zip"

def update_skill():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    target_dir = repo_root / "skills" / "ui-ux-pro-max"
    
    print("=== UI/UX Pro Max Skill Updater ===")
    print(f"Target directory: {target_dir}")
    
    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Download the ZIP file
    print(f"Downloading latest skill snapshot from: {REPO_ZIP_URL}")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "skill.zip"
            
            headers = {"User-Agent": "agent-guidance-mcp-updater/1.0"}
            req = urllib.request.Request(REPO_ZIP_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response, open(zip_path, "wb") as out_file:
                shutil.copyfileobj(response, out_file)
                
            print("Extracting archive...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)
                
            # Locate the extracted folder (typically 'ui-ux-pro-max-skill-main')
            extracted_dirs = [p for p in Path(tmpdir).iterdir() if p.is_dir() and p.name.startswith("ui-ux-pro-max-skill")]
            if not extracted_dirs:
                print("Error: Could not find extracted folder structure.")
                return False
                
            src_dir = extracted_dirs[0]
            print(f"Deploying skill files from {src_dir.name}...")
            
            # Copy all files from src_dir into target_dir
            # Define essential files/directories to keep
            essentials = {"SKILL.md", "data"}
            
            # Clear target directory first to clean up old non-essential files
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)

            print(f"Deploying essential skill files from {src_dir.name}...")

            for item in src_dir.iterdir():
                if item.name not in essentials:
                    continue
                dest_item = target_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest_item)
                else:
                    shutil.copy2(item, dest_item)
                    
            print("✓ Skill successfully updated and deployed locally!")
            return True
            
    except Exception as e:
        print(f"Error during update: {e}")
        return False

if __name__ == "__main__":
    success = update_skill()
    sys.exit(0 if success else 1)

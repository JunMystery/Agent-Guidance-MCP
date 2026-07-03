#!/usr/bin/env python3
"""Downloads and updates the ECC skills library from GitHub."""

import os
import sys
import tempfile
import urllib.request
import zipfile
import shutil
from pathlib import Path

REPO_ZIP_URL = "https://github.com/affaan-m/ECC/archive/refs/heads/main.zip"

def update_ecc():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    target_skills_dir = repo_root / "skills"
    
    print("=== ECC Skills Updater ===")
    print(f"Target skills directory: {target_skills_dir}")
    
    # Ensure target directory exists
    target_skills_dir.mkdir(parents=True, exist_ok=True)
    
    # Download the ZIP file
    print(f"Downloading latest ECC repository snapshot: {REPO_ZIP_URL}")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "ecc.zip"
            
            headers = {"User-Agent": "agent-guidance-mcp-updater/1.0"}
            req = urllib.request.Request(REPO_ZIP_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as response, open(zip_path, "wb") as out_file:
                shutil.copyfileobj(response, out_file)
                
            print("Extracting repository...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)
                
            # Locate the extracted folder (typically 'ECC-main')
            extracted_dirs = [p for p in Path(tmpdir).iterdir() if p.is_dir() and p.name.lower().startswith("ecc")]
            if not extracted_dirs:
                print("Error: Could not find extracted ECC folder structure.")
                return False
                
            src_skills_dir = extracted_dirs[0] / "skills"
            if not src_skills_dir.exists():
                print("Error: 'skills' directory not found in the extracted repository.")
                return False
                
            print(f"Deploying skills from {src_skills_dir.parent.name}/skills...")
            
            # Copy all items from src_skills_dir into target_skills_dir
            # Define essential folders/files to keep for each individual skill folder
            skill_essentials = {"SKILL.md", "scripts", "examples", "resources", "references"}

            for item in src_skills_dir.iterdir():
                dest_item = target_skills_dir / item.name
                if item.is_dir():
                    if dest_item.exists():
                        shutil.rmtree(dest_item)
                    dest_item.mkdir(parents=True, exist_ok=True)
                    
                    for sub_item in item.iterdir():
                        if sub_item.name in skill_essentials:
                            sub_dest = dest_item / sub_item.name
                            if sub_item.is_dir():
                                shutil.copytree(sub_item, sub_dest)
                            else:
                                shutil.copy2(sub_item, sub_dest)
                else:
                    # Root files inside skills/ directory (if any) can be copied
                    shutil.copy2(item, dest_item)
                    
            print("✓ ECC skills successfully updated!")
            return True
            
    except Exception as e:
        print(f"Error during update: {e}")
        return False

if __name__ == "__main__":
    success = update_ecc()
    sys.exit(0 if success else 1)

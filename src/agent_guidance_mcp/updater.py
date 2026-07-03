"""Updater module to download and update skills and UI/UX data from GitHub."""

import os
import sys
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ECC_ZIP_URL = "https://github.com/affaan-m/ECC/archive/refs/heads/main.zip"
UI_UX_ZIP_URL = "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/archive/refs/heads/main.zip"

def download_and_extract(url: str, dest_dir: Path) -> Path:
    headers = {"User-Agent": "agent-guidance-mcp-updater/1.0"}
    req = urllib.request.Request(url, headers=headers)
    
    # We use a temporary directory for extraction
    tmp_dir = Path(tempfile.mkdtemp())
    zip_path = tmp_dir / "archive.zip"
    
    try:
        with urllib.request.urlopen(req, timeout=45) as response, open(zip_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
            
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmp_dir)
            
        return tmp_dir
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"Failed to download or extract archive from {url}: {e}")

def update_ecc_library(dest_root: Path) -> bool:
    print("Updating ECC Skills library...")
    target_skills_dir = dest_root / "skills"
    target_skills_dir.mkdir(parents=True, exist_ok=True)
    
    tmp_dir = None
    try:
        tmp_dir = download_and_extract(ECC_ZIP_URL, target_skills_dir)
        extracted_dirs = [p for p in tmp_dir.iterdir() if p.is_dir() and p.name.lower().startswith("ecc")]
        if not extracted_dirs:
            print("  Error: Could not find extracted ECC folder structure.")
            return False
            
        src_skills_dir = extracted_dirs[0] / "skills"
        if not src_skills_dir.exists():
            print("  Error: 'skills' directory not found in the extracted repository.")
            return False
            
        # Copy only essential files (SKILL.md, scripts, examples, resources, references)
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
                shutil.copy2(item, dest_item)
                
        print("  ✓ ECC skills successfully updated!")
        return True
    except Exception as e:
        print(f"  Error updating ECC: {e}")
        return False
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)

def update_ui_ux_data(dest_root: Path) -> bool:
    print("Updating UI/UX Pro Max data...")
    target_dir = dest_root / "skills" / "ui-ux-pro-max"
    tmp_dir = None
    try:
        tmp_dir = download_and_extract(UI_UX_ZIP_URL, target_dir)
        extracted_dirs = [p for p in tmp_dir.iterdir() if p.is_dir() and p.name.startswith("ui-ux-pro-max-skill")]
        if not extracted_dirs:
            print("  Error: Could not find extracted folder structure.")
            return False
            
        src_dir = extracted_dirs[0]
        essentials = {"SKILL.md", "data"}
        
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        for item in src_dir.iterdir():
            if item.name not in essentials:
                continue
            dest_item = target_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest_item)
            else:
                shutil.copy2(item, dest_item)
                
        print("  ✓ UI/UX Pro Max data successfully updated!")
        return True
    except Exception as e:
        print(f"  Error updating UI/UX: {e}")
        return False
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)

def run_update() -> None:
    dest_root = Path.home() / ".agent-guidance"
    dest_root.mkdir(parents=True, exist_ok=True)
    print(f"Target directory for updates: {dest_root}")
    
    ecc_success = update_ecc_library(dest_root)
    ui_success = update_ui_ux_data(dest_root)
    
    if ecc_success and ui_success:
        print("\n✓ All updates completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Some updates failed.")
        sys.exit(1)

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
ANTHROPIC_ZIP_URL = "https://github.com/anthropics/skills/archive/refs/heads/main.zip"
OWASP_ZIP_URL = "https://github.com/OWASP/CheatSheetSeries/archive/refs/heads/master.zip"
SYSTEM_DESIGN_ZIP_URL = "https://github.com/donnemartin/system-design-primer/archive/refs/heads/master.zip"

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
    
    results = []
    results.append(("ECC (168-skill catalog)", update_ecc_library(dest_root)))
    results.append(("UI/UX Pro Max", update_ui_ux_data(dest_root)))
    results.append(("Anthropic Skills", update_anthropic_skills(dest_root)))
    results.append(("OWASP Cheat Sheets", update_owasp_cheatsheets(dest_root)))
    results.append(("System Design Primer", update_system_design_primer(dest_root)))
    
    failures = [name for name, ok in results if not ok]
    if not failures:
        print(f"\n\u2713 All {len(results)} updates completed successfully!")
        sys.exit(0)
    else:
        print(f"\n\u2717 {len(failures)} update(s) failed: {', '.join(failures)}")
        sys.exit(1)


def update_anthropic_skills(dest_root: Path) -> bool:
    print("Updating Anthropic Skills...")
    target_dir = dest_root / "skills" / "anthropic-skills"
    tmp_dir = None
    BLOCKLIST = {"docx", "pdf", "pptx", "xlsx"}
    try:
        tmp_dir = download_and_extract(ANTHROPIC_ZIP_URL, target_dir)
        extracted_dirs = [p for p in tmp_dir.iterdir() if p.is_dir() and p.name.lower().startswith("skills")]
        if not extracted_dirs:
            print("  Error: Could not find extracted skills folder.")
            return False
        src_skills_dir = extracted_dirs[0] / "skills"
        if not src_skills_dir.exists():
            print("  Error: 'skills' directory not found.")
            return False
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        copied, skipped = 0, []
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
            print(f"  Skipped {len(skipped)} source-available: {', '.join(skipped)}")
        print("  \u2713 Anthropic Skills successfully updated!")
        return True
    except Exception as e:
        print(f"  Error updating Anthropic Skills: {e}")
        return False
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def update_owasp_cheatsheets(dest_root: Path) -> bool:
    EXCLUDE = {"Index.md", "IndexASVS.md", "IndexProactiveControls.md", "README.md"}
    print("Updating OWASP Cheat Sheets...")
    target_dir = dest_root / "skills" / "owasp-cheatsheets"
    tmp_dir = None
    try:
        tmp_dir = download_and_extract(OWASP_ZIP_URL, target_dir)
        extracted_dirs = [p for p in tmp_dir.iterdir() if p.is_dir() and p.name.lower().startswith("cheatsheetseries")]
        if not extracted_dirs:
            print("  Error: Could not find extracted folder.")
            return False
        src_dir = extracted_dirs[0] / "cheatsheets"
        if not src_dir.exists():
            print("  Error: 'cheatsheets' directory not found.")
            return False
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        copied, skipped = 0, []
        for item in sorted(src_dir.iterdir()):
            if not item.is_file() or not item.suffix == ".md":
                continue
            if item.name in EXCLUDE:
                skipped.append(item.name)
                continue
            shutil.copy2(item, target_dir / item.name)
            copied += 1
        license_src = extracted_dirs[0] / "LICENSE"
        if license_src.is_file():
            shutil.copy2(license_src, target_dir / "LICENSE")
        print(f"  Copied {copied} cheat sheet(s)")
        print("  \u2713 OWASP Cheat Sheets successfully updated!")
        return True
    except Exception as e:
        print(f"  Error updating OWASP Cheat Sheets: {e}")
        return False
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def update_system_design_primer(dest_root: Path) -> bool:
    print("Updating System Design Primer...")
    target_dir = dest_root / "skills" / "system-design-primer"
    tmp_dir = None
    try:
        tmp_dir = download_and_extract(SYSTEM_DESIGN_ZIP_URL, target_dir)
        extracted_dirs = [p for p in tmp_dir.iterdir() if p.is_dir() and p.name.lower().startswith("system-design-primer")]
        if not extracted_dirs:
            print("  Error: Could not find extracted folder.")
            return False
        src_root = extracted_dirs[0]
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        readme_src = src_root / "README.md"
        if readme_src.is_file():
            shutil.copy2(readme_src, target_dir / "README.md")
        license_src = src_root / "LICENSE.txt"
        if not license_src.is_file():
            license_src = src_root / "LICENSE"
        if license_src.is_file():
            shutil.copy2(license_src, target_dir / "LICENSE")
        solutions_src = src_root / "solutions" / "system_design"
        if solutions_src.exists():
            targets_dir = target_dir / "solutions"
            targets_dir.mkdir(exist_ok=True)
            copied = 0
            for d in sorted(solutions_src.iterdir()):
                if not d.is_dir():
                    continue
                readme = d / "README.md"
                if not readme.is_file():
                    continue
                (targets_dir / d.name).mkdir(exist_ok=True)
                shutil.copy2(readme, targets_dir / d.name / "README.md")
                copied += 1
            print(f"  Copied README + {copied} solution(s)")
        print("  \u2713 System Design Primer successfully updated!")
        return True
    except Exception as e:
        print(f"  Error updating System Design Primer: {e}")
        return False
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)

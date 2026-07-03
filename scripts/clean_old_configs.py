import shutil
from pathlib import Path

def main():
    repo_root = Path(__file__).resolve().parent.parent
    
    # 1. Clean workspace cache directories
    dirs_to_clean = [
        repo_root / ".agent-context",
        repo_root / ".codegraph",
        repo_root / ".omo",
        repo_root / "build",
        repo_root / "dist",
        repo_root / ".pytest_cache",
        repo_root / "tests" / ".tmp_install_mcp",
        repo_root / "install.sh",
        repo_root / "install.ps1",
    ]
    
    # Add VSCode backup files
    vscode_dir = repo_root / ".vscode"
    if vscode_dir.exists() and vscode_dir.is_dir():
        for item in vscode_dir.iterdir():
            if ".bak" in item.name:
                dirs_to_clean.append(item)

    print("Cleaning workspace cache and backup directories...")
    for d in dirs_to_clean:
        if d.exists() and d.is_dir():
            try:
                shutil.rmtree(d)
                print(f"  Successfully removed: {d.relative_to(repo_root)}")
            except Exception as e:
                print(f"  Error removing {d.relative_to(repo_root)}: {e}")
        elif d.exists() and d.is_file():
            try:
                d.unlink()
                print(f"  Successfully removed: {d.relative_to(repo_root)}")
            except Exception as e:
                print(f"  Error removing {d.relative_to(repo_root)}: {e}")

    # 2. Clean old installed egg-info or dist-info in virtual environment
    site_packages = repo_root / ".venv" / "Lib" / "site-packages"
    if site_packages.exists() and site_packages.is_dir():
        print("\nScanning virtual environment site-packages for old v3.2.x metadata...")
        deleted_packages = 0
        for item in site_packages.iterdir():
            name_lower = item.name.lower()
            # Find metadata dirs for agent-guidance-mcp version 3.2
            if "agent_guidance_mcp" in name_lower or "agent-guidance-mcp" in name_lower:
                if "3.2" in item.name or "3.3" in item.name:
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                        print(f"  Successfully removed old package metadata: {item.name}")
                        deleted_packages += 1
                    except Exception as e:
                        print(f"  Error removing {item.name}: {e}")
        if deleted_packages == 0:
            print("  No old v3.2.x/v3.3.x package metadata found in site-packages.")
            
    print("\nCleanup completed!")

if __name__ == "__main__":
    main()

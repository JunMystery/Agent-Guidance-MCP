"""Updater module — download skills/UI data, compatibility tracking, auto-update.

Features:
- Compatibility tracking: save server version on update, warn on mismatch.
- Auto-update: check persisted state, run update when interval has elapsed.
"""

import json
import sys
import shutil
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__

ECC_ZIP_URL = "https://github.com/affaan-m/ECC/archive/refs/heads/main.zip"
UI_UX_ZIP_URL = "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/archive/refs/heads/main.zip"
ANTHROPIC_ZIP_URL = "https://github.com/anthropics/skills/archive/refs/heads/main.zip"
OWASP_ZIP_URL = "https://github.com/OWASP/CheatSheetSeries/archive/refs/heads/master.zip"
SYSTEM_DESIGN_ZIP_URL = "https://github.com/donnemartin/system-design-primer/archive/refs/heads/master.zip"

_STATE_FILE = Path.home() / ".agent-guidance" / ".update-state.json"

_GIT_ARTIFACTS = (
    ".git", ".github", ".gitignore", ".gitattributes",
    ".release-please-manifest.json", "release-please-config.json",
)


def _strip_git_artifacts(directory: Path) -> None:
    """Recursively remove .git directories and git metadata from extracted repos."""
    for pattern in _GIT_ARTIFACTS:
        for p in directory.rglob(pattern):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.is_file():
                p.unlink(missing_ok=True)

# ── State persistence ────────────────────────────────────────────────────────


def _load_state() -> dict[str, Any]:
    if _STATE_FILE.is_file():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(state: dict[str, Any]) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Compatibility check ──────────────────────────────────────────────────────


def check_compatibility(dest_root: Path | None = None) -> bool:
    """Check server version against last update version.  Returns True if
    compatible; prints warnings otherwise."""
    state = _load_state()
    stored_version = state.get("server_version")
    if stored_version is None:
        return True

    if stored_version != __version__:
        print(
            f"\n⚠  Compatibility note: skills were last updated with server "
            f"v{stored_version}, but current server is v{__version__}. "
            f"Run 'agent-guidance-mcp --update' to refresh."
        )
        return False
    return True


# ── Auto-update scheduler ────────────────────────────────────────────────────


def check_auto_update(interval: str = "weekly") -> bool:
    """Return True if an auto-update ran (or is pending and was executed).

    interval: 'weekly' or 'monthly'.
    Does NOT run the update if the state file indicates it was already done
    within the interval window.
    """
    now = datetime.now(timezone.utc)
    state = _load_state()
    last_str = state.get("last_update")

    if last_str:
        try:
            last_update = datetime.fromisoformat(last_str)
        except (ValueError, TypeError):
            last_update = None
    else:
        last_update = None

    if interval == "monthly":
        threshold_days = 30
        label = "monthly"
    else:
        threshold_days = 7
        label = "weekly"

    if last_update is not None:
        delta = (now - last_update).days
        if delta < threshold_days:
            remaining = threshold_days - delta
            print(f"Auto-update ({label}): last update was {delta}d ago "
                  f"({remaining}d until next check). Skipping.")
            return False

    print(f"Auto-update ({label}): running scheduled update...")
    try:
        run_update()
    except Exception as e:
        print(f"Auto-update ({label}): failed — {e}")
        return False
    return True


# ── Download helpers ─────────────────────────────────────────────────────────


def download_and_extract(url: str, dest_dir: Path) -> Path:
    import re
    import subprocess

    tmp_dir = Path(tempfile.mkdtemp())

    # Try Git clone fallback if git is installed
    match = re.match(r"^https://github\.com/([^/]+)/([^/]+)/archive/refs/heads/(.+)\.zip$", url)
    if match and shutil.which("git"):
        owner, repo, branch = match.groups()
        git_url = f"https://github.com/{owner}/{repo}.git"
        clone_dir = tmp_dir / f"{repo}-{branch}"
        print(f"  Cloning {owner}/{repo} ({branch}) via Git...")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", branch, git_url, str(clone_dir)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _strip_git_artifacts(tmp_dir)
            return tmp_dir
        except Exception as e:
            print(f"  Git clone failed, falling back to zip download: {e}")
            shutil.rmtree(clone_dir, ignore_errors=True)

    headers = {"User-Agent": "agent-guidance-mcp-updater/1.0"}
    req = urllib.request.Request(url, headers=headers)
    zip_path = tmp_dir / "archive.zip"

    try:
        with urllib.request.urlopen(req, timeout=45) as response, open(zip_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmp_dir)

        _strip_git_artifacts(tmp_dir)

        return tmp_dir
    except urllib.error.URLError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"Network error downloading {url}: {e}")
    except zipfile.BadZipFile as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"Corrupt archive from {url}: {e}")
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"Failed to download or extract archive from {url}: {e}")


# ── Per-updater functions ────────────────────────────────────────────────────


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

        print("  \u2713 ECC skills successfully updated!")
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
        # Resolve to the actual skill subfolder if it exists in the .claude structure
        alt_src_dir = src_dir / ".claude" / "skills" / "ui-ux-pro-max"
        if alt_src_dir.is_dir():
            src_dir = alt_src_dir

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

        print("  \u2713 UI/UX Pro Max data successfully updated!")
        return True
    except Exception as e:
        print(f"  Error updating UI/UX: {e}")
        return False
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


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


# ── Main update entry point ──────────────────────────────────────────────────


def _get_latest_commit_sha(owner: str, repo: str, branch: str) -> str | None:
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "agent-guidance-mcp-updater/1.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("sha")
    except Exception:
        return None


UPDATER_REPOS = {
    "ecc": {
        "name": "ECC (168-skill catalog)",
        "owner": "affaan-m",
        "repo": "ECC",
        "branch": "main",
        "update_fn": update_ecc_library,
        "check_dir": "skills/api-design",
    },
    "ui_ux": {
        "name": "UI/UX Pro Max",
        "owner": "nextlevelbuilder",
        "repo": "ui-ux-pro-max-skill",
        "branch": "main",
        "update_fn": update_ui_ux_data,
        "check_dir": "skills/ui-ux-pro-max",
    },
    "anthropic": {
        "name": "Anthropic Skills",
        "owner": "anthropics",
        "repo": "skills",
        "branch": "main",
        "update_fn": update_anthropic_skills,
        "check_dir": "skills/anthropic-skills",
    },
    "owasp": {
        "name": "OWASP Cheat Sheets",
        "owner": "OWASP",
        "repo": "CheatSheetSeries",
        "branch": "master",
        "update_fn": update_owasp_cheatsheets,
        "check_dir": "skills/owasp-cheatsheets",
    },
    "system_design": {
        "name": "System Design Primer",
        "owner": "donnemartin",
        "repo": "system-design-primer",
        "branch": "master",
        "update_fn": update_system_design_primer,
        "check_dir": "skills/system-design-primer",
    },
}


def run_update() -> None:
    dest_root = Path.home() / ".agent-guidance"
    dest_root.mkdir(parents=True, exist_ok=True)
    print(f"Target directory for updates: {dest_root}")

    # Pre-download the embedding model for semantic search
    print("  Downloading embedding model for semantic search...")
    try:
        from .embeddings import pre_download_models
        model_ok = pre_download_models()
        if model_ok:
            print("  \u2713 Embedding model ready")
        else:
            print("  \u26a0 Embedding model not available (sentence-transformers missing?)")
    except Exception as e:
        print(f"  \u26a0 Embedding model download failed: {e}")

    print("  Downloading LLM skill selector model (Qwen2.5-0.5B)...")
    try:
        from .llm_selector import pre_download_llm
        if pre_download_llm():
            print("  \u2713 LLM skill selector ready")
        else:
            print("  \u26a0 LLM skill selector not available (transformers missing?)")
    except Exception as e:
        print(f"  \u26a0 LLM model download failed: {e}")

    state = _load_state()
    commits_state = state.get("commits", {})
    new_commits = dict(commits_state)

    results: list[tuple[str, bool]] = []

    for key, info in UPDATER_REPOS.items():
        name = info["name"]
        check_path = dest_root / info["check_dir"]
        cached_sha = commits_state.get(key)
        latest_sha = None

        if cached_sha and check_path.exists():
            print(f"Checking {name} for updates...")
            latest_sha = _get_latest_commit_sha(info["owner"], info["repo"], info["branch"])
            if latest_sha and latest_sha == cached_sha:
                print(f"  \u2713 Up to date (commit {latest_sha[:7]})")
                results.append((name, True))
                continue

        if not latest_sha:
            latest_sha = _get_latest_commit_sha(info["owner"], info["repo"], info["branch"])

        success = info["update_fn"](dest_root)
        results.append((name, success))
        if success and latest_sha:
            new_commits[key] = latest_sha

    # Save update state for compatibility checks and auto-update scheduling
    _save_state({
        "last_update": datetime.now(timezone.utc).isoformat(),
        "server_version": __version__,
        "commits": new_commits,
    })

    failures = [name for name, ok in results if not ok]
    if not failures:
        print(f"\n\u2713 All {len(results)} updates completed successfully!")
        sys.exit(0)
    else:
        print(f"\n\u2717 {len(failures)} update(s) failed: {', '.join(failures)}")
        sys.exit(1)

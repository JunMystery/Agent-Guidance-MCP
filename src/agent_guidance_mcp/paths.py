"""Repository discovery and content-path helpers."""


import os
from pathlib import Path
from typing import Iterable

from .constants import DEFAULT_INCLUDE_DIRS, SKIP_PARTS, TEXT_SUFFIXES
from .text import normalize_identifier


def find_standards_root(root: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if root:
        candidates.append(Path(root))
    if os.environ.get("AGENT_GUIDANCE_ROOT"):
        candidates.append(Path(os.environ["AGENT_GUIDANCE_ROOT"]))

    candidates.append(Path.home() / ".agent-guidance")
    
    here = Path(__file__).resolve()
    candidates.append(here.parent / "bundled")
    for depth, parent in enumerate(here.parents):
        if depth > 4:
            break
        candidates.append(parent)
    for depth, parent in enumerate(Path.cwd().parents):
        if depth > 4:
            break
        if parent not in candidates:
            candidates.append(parent)

    for candidate in candidates:
        resolved = candidate.resolve()
        if is_standards_root(resolved):
            return resolved

    raise FileNotFoundError(
        "Could not find Agent Guidance root. Set AGENT_GUIDANCE_ROOT or pass --root."
    )


def is_standards_root(path: Path) -> bool:
    markers = [
        "karpathy/principles.md",
        "SKILL-REFERENCE.md",
        "agent-guidance/INDEX.md",
    ]
    missing = [m for m in markers if not (path / m).is_file()]
    if missing:
        import sys as _sys
        print(f"Note: standards root not found at {path}. Missing markers: {', '.join(missing)}", file=_sys.stderr)
    return len(missing) == 0


def iter_content_files(root: Path) -> Iterable[str]:
    root_files = ("README.md", "SKILL-REFERENCE.md", "PROJECT-STANDARDS.md")
    for name in root_files:
        if (root / name).is_file():
            yield name

    for directory in DEFAULT_INCLUDE_DIRS:
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_symlink():
                continue
            if not path.is_file():
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            if directory == "skills" and path.name != "SKILL.md":
                continue
            yield path.relative_to(root).as_posix()

    # Also scan ~/.agent-guidance/skills/ for 3rd party repos downloaded by updater
    user_skills = Path.home() / ".agent-guidance" / "skills"
    if user_skills.is_dir() and user_skills.resolve() != (root / "skills").resolve():
        yield from _iter_user_skills(user_skills, root)


def _iter_user_skills(user_skills: Path, root: Path) -> Iterable[str]:
    """Yield content files from ~/.agent-guidance/skills/ for 3rd party repos."""
    _OWASP = "owasp-cheatsheets"
    _ANTHROPIC = "anthropic-skills"
    _SYSDESIGN = "system-design-primer"

    for entry in sorted(user_skills.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name.lower()

        if name == _OWASP:
            for md in sorted(entry.glob("*.md")):
                if md.name.startswith(("Index", "README")):
                    continue
                yield f"skills/owasp-cheatsheets/{md.name}"

        elif name == _ANTHROPIC:
            for skill_dir in sorted(entry.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if skill_md.is_file():
                    yield f"skills/anthropic-skills/{skill_dir.name}/SKILL.md"

        elif name == _SYSDESIGN:
            for md in sorted(entry.rglob("*.md")):
                if md.is_symlink():
                    continue
                rel = md.relative_to(user_skills)
                yield f"skills/{rel.as_posix()}"


def infer_kind(relative_path: str) -> str:
    parts = Path(relative_path).parts
    if not parts:
        return "root"
    if "skills" in parts:
        if relative_path.endswith("SKILL.md"):
            return "skill"
        if "owasp-cheatsheets" in parts:
            return "doc"
        if "system-design-primer" in parts:
            return "doc"
        return "skill"
    if parts[0] == "docs":
        return "doc"
    if parts[0] == "karpathy":
        return "principle"
    if parts[0] == "agent-guidance":
        return "standard"
    if parts[0] == "references":
        return "reference"
    if parts[0] == "agents":
        return "agent"
    import sys as _sys
    print(f"Note: unknown content directory {parts[0]!r} in {relative_path!r}, classifying as 'root'", file=_sys.stderr)
    return "root"


def infer_category(relative_path: str) -> str:
    parts = Path(relative_path).parts
    if not parts:
        return "root"
    if parts[0] == "agent-guidance":
        return "agent-guidance"
    if "skills" in parts:
        if "owasp-cheatsheets" in parts:
            return "security"
        if "system-design-primer" in parts:
            return "architecture"
        return "skills"
    if parts[0] in {"karpathy", "docs", "references", "agents"}:
        return parts[0]
    return "root"


def identifier_for(relative_path: str, kind: str) -> str:
    path = Path(relative_path)
    if kind == "skill" and "skills" in path.parts:
        idx = path.parts.index("skills")
        if idx + 1 < len(path.parts):
            # Check if there are more sub-parts before SKILL.md
            if len(path.parts) > idx + 3:
                return normalize_identifier("-".join(path.parts[idx + 1:-1]))
            return normalize_identifier(path.parts[idx + 1])

    stem_path = relative_path
    for suffix in TEXT_SUFFIXES:
        if stem_path.lower().endswith(suffix):
            stem_path = stem_path[: -len(suffix)]
            break
    return normalize_identifier(stem_path)


def resolve_inside_root(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"Path escapes standards root: {relative_path!r}") from exc
    if not path.is_file():
        raise FileNotFoundError(relative_path)
    return path

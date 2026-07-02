"""Text extraction, normalization, and task keyword helpers."""


import re
from pathlib import Path


TASK_KEYWORD_TRIGGERS = {
    "tests": {
        "test",
        "tests",
        "testing",
        "pytest",
        "unit",
        "integration",
        "e2e",
        "coverage",
        "tdd",
        "regression",
        "verification",
        "playwright",
    },
    "security": {
        "security",
        "secure",
        "auth",
        "secret",
        "secrets",
        "token",
        "password",
        "owasp",
        "audit",
        "vulnerability",
        "vulnerabilities",
        "csrf",
        "xss",
        "compliance",
        "hipaa",
    },
    "api": {
        "api",
        "endpoint",
        "endpoints",
        "rest",
        "schema",
        "request",
        "response",
        "mcp",
        "connector",
        "webhook",
    },
    "backend": {
        "backend",
        "server",
        "service",
        "services",
        "database",
        "postgres",
        "postgresql",
        "mysql",
        "redis",
        "prisma",
        "django",
        "fastapi",
        "spring",
        "springboot",
        "quarkus",
        "nestjs",
        "node",
        "laravel",
        "go",
        "golang",
        "rust",
        "dotnet",
        "kotlin",
        "java",
        "python",
    },
    "docs": {
        "docs",
        "readme",
        "documentation",
        "changelog",
        "research",
        "article",
        "content",
        "seo",
        "market",
        "scientific",
        "pubmed",
    },
    "accessibility": {"a11y", "accessibility", "wcag", "aria", "keyboard"},
    "performance": {"performance", "cache", "latency", "database", "query"},
    "release": {"release", "semver", "version", "ci"},
    "skills": {"skill", "skills", "capsule"},
    "workflow": {
        "workflow",
        "orchestration",
        "orchestrate",
        "pipeline",
        "agent",
        "agents",
        "plan",
        "planning",
        "recap",
        "rollback",
        "session",
        "parallel",
    },
    "review": {"review", "audit", "checklist", "quality"},
    "ui": {
        "ui",
        "ux",
        "frontend",
        "design",
        "dashboard",
        "landing",
        "branding",
        "brand",
        "slides",
        "typography",
        "color",
        "component",
        "components",
        "react",
        "next",
        "nextjs",
        "vite",
        "vue",
        "angular",
        "nuxt",
        "mobile",
        "flutter",
        "swiftui",
        "animation",
        "motion",
    },
}


def normalize_identifier(value: str) -> str:
    cleaned = value.strip().replace("\\", "/")
    cleaned = cleaned.removeprefix("standards://document/")
    cleaned = cleaned.removeprefix("standards://skill/")
    cleaned = cleaned.removesuffix("/SKILL.md")
    cleaned = cleaned.removesuffix(".md")
    cleaned = cleaned.removesuffix(".mdc")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned.lower()


def extract_title(content: str) -> str | None:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def extract_description(content: str) -> str:
    lines = [line.strip() for line in content.splitlines()]
    in_frontmatter = lines[:1] == ["---"]
    description = ""
    if in_frontmatter:
        for line in lines[1:]:
            if line == "---":
                break
            if line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip('"')
                break
    if description:
        return description

    for line in lines:
        if not line or line.startswith("#") or line.startswith("---"):
            continue
        if line.startswith("**") and line.endswith("**"):
            continue
        return strip_markdown(line)[:220]
    return ""


def title_from_path(relative_path: str) -> str:
    stem = Path(relative_path).stem
    if stem.upper() == stem:
        return stem
    return stem.replace("-", " ").replace("_", " ").title()


def tokenize(value: str, min_length: int = 2) -> list[str]:
    if min_length <= 1:
        return [term for term in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", value.lower())]
    return [term for term in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{1,}", value.lower())]



def make_snippet(content: str, terms: list[str], radius: int = 140) -> str:
    lower = content.lower()
    positions = [lower.find(term) for term in terms if lower.find(term) >= 0]
    if not positions:
        return strip_markdown(content[: radius * 2]).strip()

    start = max(0, min(positions) - radius)
    end = min(len(content), min(positions) + radius)
    snippet = strip_markdown(content[start:end]).replace("\n", " ")
    return re.sub(r"\s+", " ", snippet).strip()


def strip_markdown(value: str) -> str:
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = value.replace("*", "").replace("_", "")
    return value.strip()


def parse_frontmatter(content: str) -> dict[str, object]:
    import json as _json
    lines = [line.strip() for line in content.splitlines()]
    in_frontmatter = bool(lines) and lines[0].lstrip("\ufeff").strip() == "---"
    data: dict[str, object] = {}
    if in_frontmatter:
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip().lower()
                val = val.strip().strip('"').strip("'")
                if val.startswith("[") and val.endswith("]"):
                    try:
                        data[key] = _json.loads(val)
                    except (_json.JSONDecodeError, ValueError):
                        items = [item.strip().strip('"').strip("'") for item in val[1:-1].split(",")]
                        data[key] = [i for i in items if i]
                else:
                    data[key] = val
    return data


def infer_task_keywords(task: str, custom_triggers: dict[str, set[str]] | None = None) -> list[str]:
    task_terms = set(tokenize(task))
    keywords: list[str] = []
    
    # Merge custom triggers if provided
    merged_triggers = {label: set(triggers) for label, triggers in TASK_KEYWORD_TRIGGERS.items()}
    if custom_triggers:
        for label, triggers in custom_triggers.items():
            label_key = label.lower()
            if label_key in merged_triggers:
                merged_triggers[label_key] = merged_triggers[label_key] | triggers
            else:
                merged_triggers[label_key] = triggers
                
    for label, triggers in merged_triggers.items():
        if task_terms & triggers:
            keywords.extend([label, *sorted(triggers & task_terms)])

    return list(dict.fromkeys(keywords))


def make_recommendation_reason(result: dict[str, object], keywords: list[str]) -> str:
    matched = [keyword for keyword in keywords if keyword in str(result).lower()]
    if matched:
        return f"Matches task signal: {', '.join(matched[:3])}"
    return "Keyword match in standards corpus"


def extract_code_terms(task: str) -> str | None:
    pattern = r"[a-zA-Z0-9]+[a-z0-9]+[A-Z0-9]+[a-zA-Z0-9]*|[a-zA-Z0-9]+_[a-zA-Z0-9_]+|[a-zA-Z0-9]+\.[a-zA-Z0-9]{2,4}|[a-zA-Z0-9]+/[a-zA-Z0-9_/]+"
    matches = re.findall(pattern, task)
    vowels = set("aeiou")
    for term in tokenize(task):
        if (
            len(term) >= 6
            and term.islower()
            and sum(1 for ch in term if ch in vowels) <= 1
            and not any(term != m and term in m for m in matches)
        ):
            matches.append(term)
    if matches:
        return " ".join(dict.fromkeys(matches))
    return None

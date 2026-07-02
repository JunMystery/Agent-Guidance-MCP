"""Catalog and search logic for AI Agent Coding Standards content."""


import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import re
from .constants import TASK_ANCHORS
from .paths import (
    find_standards_root,
    identifier_for,
    infer_category,
    infer_kind,
    iter_content_files,
    resolve_inside_root,
)
from .text import (
    extract_description,
    extract_title,
    infer_task_keywords,
    make_recommendation_reason,
    make_snippet,
    normalize_identifier,
    title_from_path,
    tokenize,
)
from .token_config import TokenOptimizationConfig, load_config_from_env


@dataclass
class CatalogEntry:
    identifier: str
    title: str
    path: str
    kind: str
    category: str
    description: str = ""
    triggers: tuple[str, ...] = ()
    anchors: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    _content: str | None = field(default=None, compare=False, repr=False)

    @property
    def uri(self) -> str:
        if self.kind == "skill":
            return f"standards://skill/{self.identifier}"
        return f"standards://document/{self.identifier}"

    def to_dict(self) -> dict[str, object]:
        return {
            "identifier": self.identifier,
            "title": self.title,
            "path": self.path,
            "kind": self.kind,
            "category": self.category,
            "description": self.description,
            "uri": self.uri,
            "triggers": list(self.triggers),
            "anchors": list(self.anchors),
            "dependencies": list(self.dependencies),
        }


class StandardsCatalog:
    def __init__(self, root: Path, entries: Iterable[CatalogEntry]):
        self.root = root
        self.entries = sorted(entries, key=lambda entry: (entry.kind, entry.path))
        self._by_identifier = {entry.identifier: entry for entry in self.entries}
        self._by_path = {entry.path.replace("\\", "/").lower(): entry for entry in self.entries}

        # Initialize and populate task anchors dynamically
        self.task_anchors: dict[str, list[str]] = {k: list(v) for k, v in TASK_ANCHORS.items()}
        # Validate built-in task anchors point to real entries
        for anchor_key, paths in self.task_anchors.items():
            for p in paths:
                if p.replace("\\", "/").lower() not in self._by_path:
                    print(f"Warning: task anchor '{anchor_key}' references missing file: {p}", file=sys.stderr)
        for entry in self.entries:
            for anchor in entry.anchors:
                anchor_lower = anchor.lower()
                if anchor_lower not in self.task_anchors:
                    self.task_anchors[anchor_lower] = []
                if entry.path not in self.task_anchors[anchor_lower]:
                    self.task_anchors[anchor_lower].append(entry.path)

        # Expose custom triggers mapping
        self.custom_triggers: dict[str, set[str]] = {}
        for entry in self.entries:
            if entry.triggers:
                # Group triggers under their respective entry categories/anchors
                label = entry.identifier
                if label not in self.custom_triggers:
                    self.custom_triggers[label] = set()
                self.custom_triggers[label].update(entry.triggers)

    def list_entries(
        self, category: str | None = None, kind: str | None = None
    ) -> list[dict[str, object]]:
        entries = self.entries
        if category:
            category_key = category.lower()
            entries = [entry for entry in entries if entry.category.lower() == category_key]
        if kind:
            kind_key = kind.lower()
            entries = [entry for entry in entries if entry.kind.lower() == kind_key]
        return [entry.to_dict() for entry in entries]

    def get_entry(self, identifier: str) -> CatalogEntry:
        key = normalize_identifier(identifier)
        if key in self._by_identifier:
            return self._by_identifier[key]

        path_key = identifier.replace("\\", "/").lower().strip("/")
        if path_key in self._by_path:
            return self._by_path[path_key]

        raise KeyError(f"No standards entry found for {identifier!r}.")

    def read_entry(
        self,
        identifier: str,
        optimize: bool = True,
        config: TokenOptimizationConfig | None = None,
    ) -> str:
        entry = self.get_entry(identifier)
        if not optimize and entry._content is not None:
            content = entry._content
        else:
            content = self.read_path(entry.path)
        config = config or load_config_from_env()
        if optimize and config.enabled:
            from .response_optimizer import TokenBudget, optimize_markdown

            budget = (
                config.skill_max_tokens
                if entry.kind == "skill"
                else config.document_max_tokens
            )
            content = optimize_markdown(content, max_tokens=budget, config=config)
        return content

    def read_path(self, relative_path: str) -> str:
        path = resolve_inside_root(self.root, relative_path)
        content = path.read_text(encoding="utf-8")
        return content

    def manifest(self) -> dict[str, object]:
        kinds: dict[str, int] = {}
        categories: dict[str, int] = {}
        for entry in self.entries:
            kinds[entry.kind] = kinds.get(entry.kind, 0) + 1
            categories[entry.category] = categories.get(entry.category, 0) + 1

        return {
            "name": "AI Agent Coding Standards",
            "root": str(self.root),
            "entry_count": len(self.entries),
            "kinds": dict(sorted(kinds.items())),
            "categories": dict(sorted(categories.items())),
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def manifest_json(self) -> str:
        return json.dumps(self.manifest(), indent=2, sort_keys=True)

    def search_entries(
        self, query: str, limit: int = 10, kind: str | None = None
    ) -> list[dict[str, object]]:
        terms = tokenize(query)
        if not terms:
            return []

        results: list[tuple[int, CatalogEntry, str]] = []
        compiled_terms = [re.compile(rf'\b{re.escape(term)}\b') for term in terms]
        for entry in self.entries:
            if kind and entry.kind.lower() != kind.lower():
                continue

            content = entry._content
            if content is None:
                continue
            title_lower = entry.title.lower()
            desc_lower = entry.description.lower()
            path_lower = entry.path.lower()
            content_lower = content.lower()

            # Location-weighted scoring (Title: 10x, Description: 5x, Path: 3x, Content: 1x)
            score = 0
            for i, term in enumerate(terms):
                score += title_lower.count(term) * 10
                score += desc_lower.count(term) * 5
                score += path_lower.count(term) * 3
                score += len(compiled_terms[i].findall(content_lower)) * 1

            if score:
                results.append((score, entry, make_snippet(content, terms)))

        results.sort(key=lambda result: (-result[0], result[1].path))
        return [
            {
                **entry.to_dict(),
                "score": score,
                "snippet": snippet,
            }
            for score, entry, snippet in results[: max(1, limit)]
        ]

    def recommend_context(self, task: str, limit: int = 8) -> dict[str, object]:
        keywords = infer_task_keywords(task, self.custom_triggers)
        weighted_query = " ".join([task, *keywords, *keywords])
        results = self.search_entries(weighted_query, limit=max(limit * 2, limit))

        essentials = [
            "karpathy-principles",
            "skill-reference",
            "docs-repo-map-for-agents",
        ]
        selected: list[dict[str, object]] = []
        seen: set[str] = set()

        def add_recommendation(identifier: str, reason: str) -> bool:
            try:
                entry = self.get_entry(identifier)
            except KeyError:
                return False
            if entry.identifier in seen:
                return False
            selected.append({**entry.to_dict(), "reason": reason})
            seen.add(entry.identifier)
            return True

        for identifier in essentials:
            add_recommendation(identifier, "Core operating context")

        # Dynamic task anchors from file frontmatter take precedence
        # Pre-compute anchor entries for fast lookup (O(1) vs O(N) per call)
        for keyword in keywords:
            for identifier in self.task_anchors.get(keyword, ()):
                if add_recommendation(identifier, f"Task-specific {keyword} reference"):
                    break
            if len(selected) >= limit:
                break

        for result in results:
            identifier = str(result["identifier"])
            if identifier in seen:
                continue
            selected.append(
                {
                    key: value
                    for key, value in result.items()
                    if key not in {"score", "snippet"}
                }
                | {"reason": make_recommendation_reason(result, keywords)}
            )
            seen.add(identifier)
            if len(selected) >= limit:
                break

        return {
            "task": task,
            "keywords": keywords,
            "recommendations": selected[:limit],
        }


def build_catalog(root: str | Path | None = None) -> StandardsCatalog:
    standards_root = find_standards_root(root)
    entries: list[CatalogEntry] = []

    for relative in iter_content_files(standards_root):
        entry = make_entry(standards_root, relative)
        if entry is not None:
            entries.append(entry)

    return StandardsCatalog(standards_root, entries)


def make_entry(root: Path, relative_path: str) -> CatalogEntry | None:
    from .text import parse_frontmatter
    path = root / relative_path
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Warning: skipping unreadable file {relative_path}: {exc}", file=sys.stderr)
        return None
    title = extract_title(content) or title_from_path(relative_path)
    description = extract_description(content)
    kind = infer_kind(relative_path)
    category = infer_category(relative_path)
    identifier = identifier_for(relative_path, kind)
    
    frontmatter = parse_frontmatter(content)
    
    triggers_val = frontmatter.get("triggers", [])
    if isinstance(triggers_val, list):
        triggers = tuple(str(t).lower() for t in triggers_val)
    elif isinstance(triggers_val, str):
        triggers = tuple(t.strip().lower() for t in triggers_val.split(",") if t.strip())
    else:
        triggers = ()
        
    anchors_val = frontmatter.get("anchors", [])
    if isinstance(anchors_val, list):
        anchors = tuple(str(a).lower() for a in anchors_val)
    elif isinstance(anchors_val, str):
        anchors = tuple(a.strip().lower() for a in anchors_val.split(",") if a.strip())
    else:
        anchors = ()

    dependencies_val = frontmatter.get("dependencies", [])
    if isinstance(dependencies_val, list):
        dependencies = tuple(str(d).lower() for d in dependencies_val)
    elif isinstance(dependencies_val, str):
        dependencies = tuple(d.strip().lower() for d in dependencies_val.split(",") if d.strip())
    else:
        dependencies = ()

    return CatalogEntry(
        identifier,
        title,
        relative_path,
        kind,
        category,
        description,
        triggers,
        anchors,
        dependencies,
        content,
    )

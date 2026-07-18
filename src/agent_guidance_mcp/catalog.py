"""Catalog and search logic for AI Agent Coding Standards content."""


import json
import logging
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import re
from .constants import TASK_ANCHORS
from .embeddings import (
    load_precomputed_embeddings,
    load_embedding_hashes,
    get_embedding,
    cosine_similarity,
    save_embeddings,
    hash_text,
    embed_text_for_entry,
    _E5_MODEL,
)
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
        self._content_cache: dict[str, str] = {}

        # Load pre-computed embeddings and dynamically embed workspace-local skills
        self.skills_embeddings = load_precomputed_embeddings()
        self._embed_hashes = load_embedding_hashes()
        self._local_skills_embedded = False
        self._failed_embeddings: set[str] = set()
        self._embed_lock = threading.Lock()

        # Initialize and populate task anchors dynamically
        self.task_anchors: dict[str, list[str]] = {k: list(v) for k, v in TASK_ANCHORS.items()}
        # Validate built-in task anchors point to real entries
        logger = logging.getLogger("agent-guidance-mcp")
        for anchor_key, paths in self.task_anchors.items():
            for p in paths:
                if p.replace("\\", "/").lower() not in self._by_path:
                    logger.warning(f"Task anchor '{anchor_key}' references missing file: {p}")
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

    def _load_content(self, entry: CatalogEntry) -> str:
        """Lazy-load file content with caching."""
        if entry.path not in self._content_cache:
            self._content_cache[entry.path] = self._read_content(entry.path)
        return self._content_cache[entry.path]

    def _read_content(self, relative_path: str) -> str:
        path = self.root / relative_path
        if not path.is_file():
            # Check project root next (for workspace-local skills)
            try:
                from .project_scan import resolve_project_root
                proj_path = resolve_project_root(".") / relative_path
                if proj_path.is_file():
                    path = proj_path
            except Exception:
                pass
        if not path.is_file():
            alt = Path.home() / ".agent-guidance" / relative_path
            if alt.is_file():
                path = alt
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8")

    def read_entry(
        self,
        identifier: str,
        optimize: bool = True,
        config: TokenOptimizationConfig | None = None,
    ) -> str:
        entry = self.get_entry(identifier)
        content = self._load_content(entry)
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
        return self._read_content(relative_path)

    def manifest(self) -> dict[str, object]:
        kinds: dict[str, int] = {}
        categories: dict[str, int] = {}
        errors = 0
        for entry in self.entries:
            kinds[entry.kind] = kinds.get(entry.kind, 0) + 1
            categories[entry.category] = categories.get(entry.category, 0) + 1

        return {
            "name": "AI Agent Coding Standards",
            "root": str(self.root),
            "entry_count": len(self.entries),
            "kinds": dict(sorted(kinds.items())),
            "categories": dict(sorted(categories.items())),
            "errors": errors,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def manifest_json(self) -> str:
        return json.dumps(self.manifest(), indent=2, sort_keys=True)

    def _ensure_local_skills_embedded(self) -> None:
        """Ensure every entry has a fresh embedding (F2/F5).

        Lazily: dynamically embed entries that have no vector (workspace-local
        skills), and re-embed precomputed entries whose source content changed
        (auto-heal staleness via content hash). Persists any updates.
        Runs in a background thread so the first tool call is not blocked.
        """
        if getattr(self, "_local_skills_embedded", False):
            return
        with self._embed_lock:
            if getattr(self, "_local_skills_embedding_started", False):
                return
            self._local_skills_embedding_started = True
        threading.Thread(target=self._embed_local_skills_worker, daemon=True).start()

    def _embed_local_skills_worker(self) -> None:
        self._local_skills_embedded = True
        logger = logging.getLogger("agent-guidance-mcp")
        changed = False
        for entry in self.entries:
            identifier = entry.identifier
            if identifier in self._failed_embeddings:
                continue
            if identifier in self.skills_embeddings:
                stored_hash = self._embed_hashes.get(identifier)
                if stored_hash is None:
                    continue
                if self._entry_hash(entry) == stored_hash:
                    continue
                logger.info("re-embedding stale entry '%s'", identifier)
                if self._embed_and_store(entry):
                    changed = True
                else:
                    self._failed_embeddings.add(identifier)
            else:
                if self._embed_and_store(entry):
                    changed = True
                else:
                    self._failed_embeddings.add(identifier)
        if changed:
            self._persist_embeddings()

    def _entry_hash(self, entry: "CatalogEntry") -> str:
        content = self._load_content(entry)
        return hash_text(embed_text_for_entry(entry.title, entry.description, content))

    def _embed_and_store(self, entry: "CatalogEntry") -> bool:
        logger = logging.getLogger("agent-guidance-mcp")
        try:
            content = self._load_content(entry)
            text_to_embed = f"Title: {entry.title}\nDescription: {entry.description}\nContent: {content[:1000]}"
            vector = get_embedding(text_to_embed, prefix="passage")
            if vector:
                self.skills_embeddings[entry.identifier] = vector
                self._embed_hashes[entry.identifier] = self._entry_hash(entry)
                return True
        except Exception as e:
            logger.warning(f"Failed to embed entry '{entry.identifier}' — {e}")
        return False

    def _persist_embeddings(self) -> None:
        if "pytest" in sys.modules:
            return  # never mutate the bundled file under test
        try:
            save_embeddings(self.skills_embeddings, self._embed_hashes)
        except Exception as e:
            logging.getLogger("agent-guidance-mcp").warning(f"Failed to persist embeddings: {e}")

    def search_entries(
        self, query: str, limit: int = 10, kind: str | None = None
    ) -> list[dict[str, object]]:
        self._ensure_local_skills_embedded()
        terms = list(dict.fromkeys(tokenize(query)))

        # Try semantic search embedding
        query_vector = get_embedding(query, prefix="query")

        results: list[tuple[float, CatalogEntry, str]] = []
        # F3: boundary-aware matching for all fields (avoids substring false
        # positives like "api" matching "rapid").
        compiled_terms = (
            [re.compile(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])") for term in terms]
            if terms
            else []
        )
        for entry in self.entries:
            if kind and entry.kind.lower() != kind.lower():
                continue

            # 1. Compute keyword score
            keyword_score = 0
            title_lower = entry.title.lower()
            desc_lower = entry.description.lower()
            path_lower = entry.path.lower()

            if terms:
                for i, term in enumerate(terms):
                    keyword_score += len(compiled_terms[i].findall(title_lower)) * 10
                    keyword_score += len(compiled_terms[i].findall(desc_lower)) * 5
                    keyword_score += len(compiled_terms[i].findall(path_lower)) * 3

                content = self._load_content(entry)
                content_lower = content.lower()
                for i, term in enumerate(terms):
                    keyword_score += len(compiled_terms[i].findall(content_lower)) * 1
            else:
                content = self._load_content(entry)

            # 2. Compute semantic score (F4: any entry with a vector, not just skills)
            semantic_score = 0.0
            if query_vector and entry.identifier in self.skills_embeddings:
                skill_vector = self.skills_embeddings[entry.identifier]
                semantic_score = cosine_similarity(query_vector, skill_vector)
                # F1: negative cosine must never suppress a keyword-relevant result
                if semantic_score < 0.0:
                    semantic_score = 0.0

            # 3. Combine scores (hybrid search)
            # Scale semantic similarity (0.0 to 1.0) to range 0-150, added to keyword score.
            combined_score = keyword_score + (semantic_score * 150)
            # Skip only when neither signal contributes (F1)
            if keyword_score <= 0 and semantic_score <= 0:
                continue

            results.append((combined_score, entry, make_snippet(content, terms if terms else [query])))

        results.sort(key=lambda result: (-result[0], result[1].path))
        returned = results[: max(1, limit)]

        # Log every query (semantic + silent fallback) with status="ok"/"fallback"
        # so the dashboard can show whether the embed model actually worked.
        try:
            from .server import get_usage

            _u = get_usage()
            if _u is not None:
                _u.record_embed_query(
                    query_text=query,
                    prefix_type="query",
                    model_name=_E5_MODEL,
                    vector_dim=len(query_vector) if query_vector is not None else 0,
                    result_count=len(returned),
                    status="ok" if query_vector is not None else "fallback",
                )
        except Exception:
            pass

        return [
            {
                **entry.to_dict(),
                "score": score,
                "snippet": snippet,
                "embedding_used": query_vector is not None,
            }
            for score, entry, snippet in returned
        ]

    def recommend_context(
        self,
        task: str,
        limit: int = 8,
        include_content: bool = False,
        config: object = None,
    ) -> dict[str, object]:
        keywords = infer_task_keywords(task, self.custom_triggers)
        weighted_query = " ".join([task, *keywords, *keywords])
        results = self.search_entries(weighted_query, limit=max(limit * 2, limit))

        llm_picks: list[str] = []
        try:
            from .llm_selector import LLMSelector
            selector = LLMSelector()
            candidate_list = [
                {"identifier": r["identifier"], "title": r.get("title", ""), "description": r.get("description", "")}
                for r in results
            ]
            llm_picks = selector.select(task, candidate_list, limit=3)
        except Exception:
            pass

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
            rec = entry.to_dict()
            if include_content:
                # Load content for at least the first 2 entries, or if it represents a skill,
                # or if the entry triggers match the active task keywords.
                should_load = len(seen) < 2 or entry.kind == "skill" or any(t in keywords for t in entry.triggers)
                if should_load:
                    rec["content"] = self.read_entry(entry.identifier, config=config)
            selected.append({**rec, "reason": reason})
            seen.add(entry.identifier)
            return True

        for identifier in essentials:
            add_recommendation(identifier, "Core operating context")

        # LLM picks
        for identifier in llm_picks:
            add_recommendation(identifier, "LLM-recommended for this task")

        # Feedback-boosted skills: well-rated (>=4) skills for similar tasks
        try:
            from .usage import get_usage
            usage = get_usage()
            if usage is not None:
                feedback_boost = usage.get_top_feedback_skills(keywords, limit=3)
                for fid, avg in feedback_boost.items():
                    if add_recommendation(fid, f"High-feedback skill (avg {avg:.1f}/5)"):
                        break
        except Exception:
            pass

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
            rec = {
                key: value
                for key, value in result.items()
                if key not in {"score", "snippet"}
            }
            if include_content:
                try:
                    entry = self.get_entry(identifier)
                    should_load = len(seen) < 2 or entry.kind == "skill" or any(t in keywords for t in entry.triggers)
                    if should_load:
                        rec["content"] = self.read_entry(identifier, config=config)
                except KeyError:
                    pass
            selected.append(
                rec | {"reason": make_recommendation_reason(result, keywords)}
            )
            seen.add(identifier)
            if len(selected) >= limit:
                break

        return {
            "task": task,
            "keywords": keywords,
            "recommendations": selected[:limit],
        }

    def recommend_reasoning_framework(self, task: str) -> dict[str, object]:
        """Return a structured reasoning framework for the given task."""
        from .reasoning import get_reasoning_framework
        framework = get_reasoning_framework(task)
        skill_entries: list[dict[str, object]] = []
        for skill_id in framework["skills_to_invoke"]:
            try:
                entry = self.get_entry(skill_id)
                skill_entries.append(entry.to_dict())
            except KeyError:
                continue
        framework["skill_entries"] = skill_entries
        return framework


def build_catalog(root: str | Path | None = None) -> StandardsCatalog:
    standards_root = find_standards_root(root)
    entries: list[CatalogEntry] = []

    for relative in iter_content_files(standards_root):
        entry = make_entry(standards_root, relative)
        if entry is not None:
            entries.append(entry)

    # Discover workspace-local skills (from project root)
    try:
        from .project_scan import resolve_project_root
        project_root = resolve_project_root(".")
        local_skills_dirs = [
            project_root / ".agents" / "skills",
            project_root / ".opencode" / "skills",
            project_root / ".claude" / "skills",
        ]
        for skills_dir in local_skills_dirs:
            if skills_dir.is_dir():
                for child in sorted(skills_dir.iterdir()):
                    if child.is_dir():
                        skill_md = child / "SKILL.md"
                        if skill_md.is_file():
                            rel_path = str(skill_md.relative_to(project_root))
                            entry = make_entry(project_root, rel_path)
                            if entry is not None:
                                # Ensure we don't duplicate global skills
                                if not any(e.identifier == entry.identifier for e in entries):
                                    entries.append(entry)
    except Exception as e:
        import sys as _sys
        print(f"Warning: failed to scan workspace-local skills — {e}", file=_sys.stderr)

    return StandardsCatalog(standards_root, entries)


def make_entry(root: Path, relative_path: str) -> CatalogEntry | None:
    from .text import parse_frontmatter
    path = root / relative_path
    if not path.is_file():
        alt = Path.home() / ".agent-guidance" / relative_path
        if alt.is_file():
            path = alt
    try:
        # Read only first 4KB for metadata — content loaded lazily on demand
        with path.open("r", encoding="utf-8") as f:
            content = f.read(4096)
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
    )

"""UI/UX Pro Max search and recommendation helpers."""


from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from math import log
from pathlib import Path
from typing import Iterable


DATA_RELATIVE_PATH = Path("skills") / "ui-ux-pro-max" / "data"
MAX_RESULTS = 3

_BM25_CACHE: dict[str, tuple[BM25, list[dict[str, str]]]] = {}


def clear_bm25_cache() -> None:
    """Clear the BM25 index cache (useful for testing)."""
    _BM25_CACHE.clear()

CSV_CONFIG = {
    "style": {
        "file": "styles.csv",
        "search_cols": ["Style Category", "Keywords", "Best For", "Type", "AI Prompt Keywords"],
        "output_cols": [
            "Style Category",
            "Type",
            "Keywords",
            "Primary Colors",
            "Effects & Animation",
            "Best For",
            "Light Mode ✓",
            "Dark Mode ✓",
            "Performance",
            "Accessibility",
            "Framework Compatibility",
            "Complexity",
            "AI Prompt Keywords",
            "CSS/Technical Keywords",
            "Implementation Checklist",
            "Design System Variables",
        ],
    },
    "color": {
        "file": "colors.csv",
        "search_cols": ["Product Type", "Notes"],
        "output_cols": [
            "Product Type",
            "Primary",
            "On Primary",
            "Secondary",
            "On Secondary",
            "Accent",
            "On Accent",
            "Background",
            "Foreground",
            "Card",
            "Card Foreground",
            "Muted",
            "Muted Foreground",
            "Border",
            "Destructive",
            "On Destructive",
            "Ring",
            "Notes",
        ],
    },
    "chart": {
        "file": "charts.csv",
        "search_cols": [
            "Data Type",
            "Keywords",
            "Best Chart Type",
            "When to Use",
            "When NOT to Use",
            "Accessibility Notes",
        ],
        "output_cols": [
            "Data Type",
            "Keywords",
            "Best Chart Type",
            "Secondary Options",
            "When to Use",
            "When NOT to Use",
            "Data Volume Threshold",
            "Color Guidance",
            "Accessibility Grade",
            "Accessibility Notes",
            "A11y Fallback",
            "Library Recommendation",
            "Interactive Level",
        ],
    },
    "landing": {
        "file": "landing.csv",
        "search_cols": ["Pattern Name", "Keywords", "Conversion Optimization", "Section Order"],
        "output_cols": [
            "Pattern Name",
            "Keywords",
            "Section Order",
            "Primary CTA Placement",
            "Color Strategy",
            "Conversion Optimization",
        ],
    },
    "product": {
        "file": "products.csv",
        "search_cols": ["Product Type", "Keywords", "Primary Style Recommendation", "Key Considerations"],
        "output_cols": [
            "Product Type",
            "Keywords",
            "Primary Style Recommendation",
            "Secondary Styles",
            "Landing Page Pattern",
            "Dashboard Style (if applicable)",
            "Color Palette Focus",
        ],
    },
    "ux": {
        "file": "ux-guidelines.csv",
        "search_cols": ["Category", "Issue", "Description", "Platform"],
        "output_cols": [
            "Category",
            "Issue",
            "Platform",
            "Description",
            "Do",
            "Don't",
            "Code Example Good",
            "Code Example Bad",
            "Severity",
        ],
    },
    "typography": {
        "file": "typography.csv",
        "search_cols": [
            "Font Pairing Name",
            "Category",
            "Mood/Style Keywords",
            "Best For",
            "Heading Font",
            "Body Font",
        ],
        "output_cols": [
            "Font Pairing Name",
            "Category",
            "Heading Font",
            "Body Font",
            "Mood/Style Keywords",
            "Best For",
            "Google Fonts URL",
            "CSS Import",
            "Tailwind Config",
            "Notes",
        ],
    },
    "icons": {
        "file": "icons.csv",
        "search_cols": ["Category", "Icon Name", "Keywords", "Best For"],
        "output_cols": [
            "Category",
            "Icon Name",
            "Keywords",
            "Library",
            "Import Code",
            "Usage",
            "Best For",
            "Style",
        ],
    },
    "react": {
        "file": "react-performance.csv",
        "search_cols": ["Category", "Issue", "Keywords", "Description"],
        "output_cols": [
            "Category",
            "Issue",
            "Platform",
            "Description",
            "Do",
            "Don't",
            "Code Example Good",
            "Code Example Bad",
            "Severity",
        ],
    },
    "web": {
        "file": "app-interface.csv",
        "search_cols": ["Category", "Issue", "Keywords", "Description"],
        "output_cols": [
            "Category",
            "Issue",
            "Platform",
            "Description",
            "Do",
            "Don't",
            "Code Example Good",
            "Code Example Bad",
            "Severity",
        ],
    },
    "google-fonts": {
        "file": "google-fonts.csv",
        "search_cols": [
            "Family",
            "Category",
            "Stroke",
            "Classifications",
            "Keywords",
            "Subsets",
            "Designers",
        ],
        "output_cols": [
            "Family",
            "Category",
            "Stroke",
            "Classifications",
            "Styles",
            "Variable Axes",
            "Subsets",
            "Designers",
            "Popularity Rank",
            "Google Fonts URL",
        ],
    },
}

STACK_CONFIG = {
    "react": {"file": "stacks/react.csv"},
    "nextjs": {"file": "stacks/nextjs.csv"},
    "vue": {"file": "stacks/vue.csv"},
    "svelte": {"file": "stacks/svelte.csv"},
    "astro": {"file": "stacks/astro.csv"},
    "swiftui": {"file": "stacks/swiftui.csv"},
    "react-native": {"file": "stacks/react-native.csv"},
    "flutter": {"file": "stacks/flutter.csv"},
    "nuxtjs": {"file": "stacks/nuxtjs.csv"},
    "nuxt-ui": {"file": "stacks/nuxt-ui.csv"},
    "html-tailwind": {"file": "stacks/html-tailwind.csv"},
    "shadcn": {"file": "stacks/shadcn.csv"},
    "jetpack-compose": {"file": "stacks/jetpack-compose.csv"},
    "threejs": {"file": "stacks/threejs.csv"},
    "angular": {"file": "stacks/angular.csv"},
    "laravel": {"file": "stacks/laravel.csv"},
}

STACK_COLS = {
    "search_cols": ["Category", "Guideline", "Description", "Do", "Don't"],
    "output_cols": [
        "Category",
        "Guideline",
        "Description",
        "Do",
        "Don't",
        "Code Good",
        "Code Bad",
        "Severity",
        "Docs URL",
    ],
}

SLIDE_CSV_CONFIG = {
    "strategy": {
        "file": "slides/slide-strategies.csv",
        "search_cols": ["strategy_name", "keywords", "goal", "audience", "narrative_arc"],
        "output_cols": [
            "strategy_name",
            "keywords",
            "slide_count",
            "structure",
            "goal",
            "audience",
            "tone",
            "narrative_arc",
            "sources",
        ],
    },
    "layout": {
        "file": "slides/slide-layouts.csv",
        "search_cols": ["layout_name", "keywords", "use_case", "recommended_for"],
        "output_cols": [
            "layout_name",
            "keywords",
            "use_case",
            "content_zones",
            "visual_weight",
            "cta_placement",
            "recommended_for",
            "avoid_for",
            "css_structure",
        ],
    },
    "copy": {
        "file": "slides/slide-copy.csv",
        "search_cols": ["formula_name", "keywords", "use_case", "emotion_trigger", "slide_type"],
        "output_cols": [
            "formula_name",
            "keywords",
            "components",
            "use_case",
            "example_template",
            "emotion_trigger",
            "slide_type",
            "source",
        ],
    },
    "chart": {
        "file": "slides/slide-charts.csv",
        "search_cols": ["chart_type", "keywords", "best_for", "when_to_use", "slide_context"],
        "output_cols": [
            "chart_type",
            "keywords",
            "best_for",
            "data_type",
            "when_to_use",
            "when_to_avoid",
            "max_categories",
            "slide_context",
            "css_implementation",
            "accessibility_notes",
        ],
    },
}


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: list[list[str]] = []
        self.doc_lengths: list[int] = []
        self.avgdl = 0.0
        self.idf: dict[str, float] = {}
        self.doc_freqs: dict[str, int] = defaultdict(int)
        self.n = 0

    def _tokenize_bm25(self, text: str) -> list[str]:
        cleaned = re.sub(r"[^\w\s]", " ", str(text).lower())
        return [word for word in cleaned.split() if len(word) >= 2]

    def fit(self, documents: Iterable[str]) -> None:
        self.corpus = [self._tokenize_bm25(document) for document in documents]
        self.n = len(self.corpus)
        if self.n == 0:
            return
        self.doc_lengths = [len(document) for document in self.corpus]
        self.avgdl = sum(self.doc_lengths) / self.n

        for document in self.corpus:
            for word in set(document):
                self.doc_freqs[word] += 1

        for word, frequency in self.doc_freqs.items():
            self.idf[word] = log((self.n - frequency + 0.5) / (frequency + 0.5) + 1)

    def score(self, query: str) -> list[tuple[int, float]]:
        if not self.corpus or self.avgdl == 0:
            return []
        query_tokens = self._tokenize_bm25(query)
        scores: list[tuple[int, float]] = []
        for index, document in enumerate(self.corpus):
            document_score = 0.0
            term_freqs: dict[str, int] = defaultdict(int)
            for word in document:
                term_freqs[word] += 1

            for token in query_tokens:
                if token not in self.idf:
                    continue
                term_frequency = term_freqs[token]
                numerator = term_frequency * (self.k1 + 1)
                denominator = term_frequency + self.k1 * (
                    1 - self.b + self.b * self.doc_lengths[index] / self.avgdl
                )
                document_score += self.idf[token] * numerator / denominator

            scores.append((index, document_score))

        return sorted(scores, key=lambda item: item[1], reverse=True)


def search_ui_ux_guidance(
    root: Path, query: str, domain: str | None = None, stack: str | None = None, limit: int = 3
) -> dict[str, object]:
    """Search UI/UX Pro Max guidance by domain or stack."""
    data_dir = root / DATA_RELATIVE_PATH
    max_results = _bounded_limit(limit)

    if stack:
        stack_key = stack.lower()
        if stack_key not in STACK_CONFIG:
            return {
                "error": f"Unknown stack: {stack}",
                "available_stacks": sorted(STACK_CONFIG),
            }
        config = {**STACK_CONFIG[stack_key], **STACK_COLS}
        results = _search_csv(data_dir / config["file"], config, query, max_results)
        return {
            "domain": "stack",
            "stack": stack_key,
            "query": query,
            "file": config["file"],
            "count": len(results),
            "results": results,
        }

    domain_key = (domain or _detect_ui_domain(query)).lower()
    if domain_key not in CSV_CONFIG:
        return {
            "error": f"Unknown domain: {domain}",
            "available_domains": sorted(CSV_CONFIG),
        }

    config = CSV_CONFIG[domain_key]
    results = _search_csv(data_dir / config["file"], config, query, max_results)
    return {
        "domain": domain_key,
        "query": query,
        "file": config["file"],
        "count": len(results),
        "results": results,
    }


def generate_ui_ux_design_system(
    root: Path, query: str, project_name: str | None = None, output_format: str = "markdown"
) -> str:
    """Generate a compact design-system recommendation from UI/UX Pro Max data."""
    format_key = output_format.lower()
    if format_key not in {"markdown", "ascii"}:
        raise ValueError("output_format must be 'markdown' or 'ascii'.")

    recommendation = _generate_design_system(root, query, project_name)
    if format_key == "ascii":
        return _format_design_system_ascii(recommendation)
    return _format_design_system_markdown(recommendation)


def search_slide_guidance(
    root: Path, query: str, domain: str | None = None, limit: int = 3
) -> dict[str, object]:
    """Search slide strategy, layout, copy, or chart guidance."""
    data_dir = root / DATA_RELATIVE_PATH
    domain_key = (domain or _detect_slide_domain(query)).lower()
    if domain_key not in SLIDE_CSV_CONFIG:
        return {
            "error": f"Unknown slide domain: {domain}",
            "available_domains": sorted(SLIDE_CSV_CONFIG),
        }

    config = SLIDE_CSV_CONFIG[domain_key]
    results = _search_csv(data_dir / config["file"], config, query, _bounded_limit(limit))
    return {
        "domain": domain_key,
        "query": query,
        "file": config["file"],
        "count": len(results),
        "results": results,
    }


def _generate_design_system(root: Path, query: str, project_name: str | None) -> dict[str, object]:
    product = search_ui_ux_guidance(root, query, domain="product", limit=1)
    product_results = list(product.get("results", []))
    category = "General"
    if product_results:
        category = str(product_results[0].get("Product Type", "General"))

    reasoning = _apply_reasoning(root, category)
    style_priority = reasoning["style_priority"]

    style_query = f"{query} {' '.join(style_priority[:2])}".strip()
    style = search_ui_ux_guidance(root, style_query, domain="style", limit=3)
    colors = search_ui_ux_guidance(root, query, domain="color", limit=2)
    landing = search_ui_ux_guidance(root, query, domain="landing", limit=2)
    typography = search_ui_ux_guidance(root, query, domain="typography", limit=2)

    best_style = _select_best_match(list(style.get("results", [])), style_priority)
    best_color = _first_result(colors)
    best_landing = _first_result(landing)
    best_typography = _first_result(typography)

    style_effects = str(best_style.get("Effects & Animation", ""))
    return {
        "project_name": project_name or query.upper(),
        "category": category,
        "pattern": {
            "name": best_landing.get("Pattern Name", reasoning["pattern"]),
            "sections": best_landing.get("Section Order", "Hero > Features > CTA"),
            "cta_placement": best_landing.get("Primary CTA Placement", "Above fold"),
            "color_strategy": best_landing.get("Color Strategy", ""),
            "conversion": best_landing.get("Conversion Optimization", ""),
        },
        "style": {
            "name": best_style.get("Style Category", "Minimalism"),
            "type": best_style.get("Type", "General"),
            "keywords": best_style.get("Keywords", ""),
            "effects": style_effects or reasoning["key_effects"],
            "best_for": best_style.get("Best For", ""),
            "performance": best_style.get("Performance", ""),
            "accessibility": best_style.get("Accessibility", ""),
            "light_mode": best_style.get("Light Mode ✓", ""),
            "dark_mode": best_style.get("Dark Mode ✓", ""),
        },
        "colors": {
            "primary": best_color.get("Primary", "#2563EB"),
            "on_primary": best_color.get("On Primary", ""),
            "secondary": best_color.get("Secondary", "#3B82F6"),
            "accent": best_color.get("Accent", "#F97316"),
            "background": best_color.get("Background", "#F8FAFC"),
            "foreground": best_color.get("Foreground", "#1E293B"),
            "muted": best_color.get("Muted", ""),
            "border": best_color.get("Border", ""),
            "destructive": best_color.get("Destructive", ""),
            "ring": best_color.get("Ring", ""),
            "notes": best_color.get("Notes", ""),
        },
        "typography": {
            "heading": best_typography.get("Heading Font", "Inter"),
            "body": best_typography.get("Body Font", "Inter"),
            "mood": best_typography.get("Mood/Style Keywords", reasoning["typography_mood"]),
            "best_for": best_typography.get("Best For", ""),
            "google_fonts_url": best_typography.get("Google Fonts URL", ""),
            "css_import": best_typography.get("CSS Import", ""),
        },
        "key_effects": style_effects or reasoning["key_effects"],
        "anti_patterns": reasoning["anti_patterns"],
        "severity": reasoning["severity"],
    }


def _search_csv(
    filepath: Path, config: dict[str, object], query: str, max_results: int
) -> list[dict[str, str]]:
    if not filepath.is_file():
        return []

    search_cols = list(config["search_cols"])  # type: ignore[index]
    cache_key = f"{filepath}:{','.join(search_cols)}"
    if cache_key in _BM25_CACHE:
        bm25, rows = _BM25_CACHE[cache_key]
    else:
        try:
            rows = _load_csv(filepath)
        except (FileNotFoundError, OSError):
            return []
        documents = [" ".join(str(row.get(column, "")) for column in search_cols) for row in rows]
        bm25 = BM25()
        bm25.fit(documents)
        _BM25_CACHE[cache_key] = (bm25, rows)

    results: list[dict[str, str]] = []
    output_cols = list(config["output_cols"])  # type: ignore[index]
    for index, score in bm25.score(query)[:max_results]:
        if score <= 0:
            continue
        row = rows[index]
        safe_row: dict[str, str] = {}
        for column in output_cols:
            if column in row:
                val = row.get(column, "")
                if val and val[0] in "=+-@\t\r":
                    val = "'" + val
                safe_row[column] = val
        results.append(safe_row)
    return results


_MAX_CSV_BYTES = 50_000_000


def _load_csv(filepath: Path) -> list[dict[str, str]]:
    if filepath.stat().st_size > _MAX_CSV_BYTES:
        return []
    try:
        with filepath.open("r", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except (UnicodeDecodeError, csv.Error):
        return []


def _bounded_limit(limit: int) -> int:
    return max(1, min(limit, 20))


def _detect_ui_domain(query: str) -> str:
    query_lower = query.lower()
    domain_keywords = {
        "color": [
            "color",
            "palette",
            "hex",
            "#",
            "rgb",
            "token",
            "semantic",
            "accent",
            "destructive",
            "muted",
            "foreground",
        ],
        "chart": ["chart", "graph", "visualization", "trend", "bar", "pie", "scatter", "heatmap"],
        "landing": ["landing", "page", "cta", "conversion", "hero", "testimonial", "pricing"],
        "product": [
            "saas",
            "ecommerce",
            "e-commerce",
            "fintech",
            "healthcare",
            "gaming",
            "portfolio",
            "crypto",
            "dashboard",
            "restaurant",
            "hotel",
            "education",
            "legal",
            "medical",
            "beauty",
            "booking",
            "crm",
            "marketplace",
        ],
        "style": [
            "style",
            "design",
            "ui",
            "minimalism",
            "glassmorphism",
            "neumorphism",
            "brutalism",
            "dark mode",
            "flat",
            "tailwind",
        ],
        "ux": [
            "ux",
            "usability",
            "accessibility",
            "wcag",
            "touch",
            "scroll",
            "animation",
            "keyboard",
            "navigation",
            "mobile",
        ],
        "typography": ["font pairing", "typography pairing", "heading font", "body font"],
        "google-fonts": ["google font", "font family", "variable font"],
        "icons": ["icon", "icons", "lucide", "heroicons", "symbol", "svg icon"],
        "react": ["react", "next.js", "nextjs", "suspense", "memo", "useeffect", "rerender"],
        "web": ["aria", "focus", "outline", "semantic", "autocomplete", "form"],
    }
    scores = {
        domain: sum(1 for keyword in keywords if re.search(r"\b" + re.escape(keyword) + r"\b", query_lower))
        for domain, keywords in domain_keywords.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "style"


def _detect_slide_domain(query: str) -> str:
    query_lower = query.lower()
    domain_keywords = {
        "strategy": [
            "pitch",
            "deck",
            "investor",
            "seed",
            "series",
            "demo",
            "sales",
            "webinar",
            "board",
            "structure",
        ],
        "layout": ["slide", "layout", "grid", "column", "title", "hero", "section", "screenshot"],
        "copy": ["headline", "copy", "formula", "aida", "pas", "hook", "cta", "benefit"],
        "chart": ["chart", "graph", "bar", "line", "pie", "funnel", "metrics", "data", "kpi"],
    }
    scores = {
        domain: sum(1 for keyword in keywords if keyword in query_lower)
        for domain, keywords in domain_keywords.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "strategy"


def _apply_reasoning(root: Path, category: str) -> dict[str, object]:
    default = {
        "pattern": "Hero + Features + CTA",
        "style_priority": ["Minimalism", "Flat Design"],
        "color_mood": "Professional",
        "typography_mood": "Clean",
        "key_effects": "Subtle hover transitions",
        "anti_patterns": "",
        "severity": "MEDIUM",
    }
    reasoning_file = root / DATA_RELATIVE_PATH / "ui-reasoning.csv"
    if not reasoning_file.is_file():
        return default

    try:
        rules = _load_csv(reasoning_file)
    except (FileNotFoundError, OSError):
        return default

    category_lower = category.lower()
    for rule in rules:
        rule_category = rule.get("UI_Category", "").lower()
        if (
            rule_category == category_lower
            or rule_category in category_lower
            or category_lower in rule_category
        ):
            style_priority = [
                style.strip()
                for style in rule.get("Style_Priority", "").split("+")
                if style.strip()
            ]
            return {
                "pattern": rule.get("Recommended_Pattern", default["pattern"]),
                "style_priority": style_priority or default["style_priority"],
                "color_mood": rule.get("Color_Mood", default["color_mood"]),
                "typography_mood": rule.get("Typography_Mood", default["typography_mood"]),
                "key_effects": rule.get("Key_Effects", default["key_effects"]),
                "anti_patterns": rule.get("Anti_Patterns", default["anti_patterns"]),
                "severity": rule.get("Severity", default["severity"]),
            }
    return default


def _select_best_match(results: list[dict[str, str]], priority_keywords: list[str]) -> dict[str, str]:
    if not results:
        return {}
    for priority in priority_keywords:
        priority_lower = priority.lower().strip()
        for result in results:
            style_name = result.get("Style Category", "").lower()
            if priority_lower in style_name or style_name in priority_lower:
                return result

    scored: list[tuple[int, dict[str, str]]] = []
    for result in results:
        result_text = json.dumps(result).lower()
        score = 0
        for keyword in priority_keywords:
            keyword_lower = keyword.lower().strip()
            if keyword_lower in result.get("Style Category", "").lower():
                score += 10
            elif keyword_lower in result.get("Keywords", "").lower():
                score += 3
            elif keyword_lower in result_text:
                score += 1
        scored.append((score, result))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1] if scored and scored[0][0] > 0 else results[0]


def _first_result(search_result: dict[str, object]) -> dict[str, str]:
    results = search_result.get("results", [])
    if isinstance(results, list) and results:
        return results[0]
    return {}


def _format_design_system_markdown(recommendation: dict[str, object]) -> str:
    pattern = recommendation["pattern"]
    style = recommendation["style"]
    colors = recommendation["colors"]
    typography = recommendation["typography"]
    if not isinstance(pattern, dict): raise TypeError("'pattern' must be a dict")
    if not isinstance(style, dict): raise TypeError("'style' must be a dict")
    if not isinstance(colors, dict): raise TypeError("'colors' must be a dict")
    if not isinstance(typography, dict): raise TypeError("'typography' must be a dict")

    lines = [
        f"## Design System: {recommendation['project_name']}",
        "",
        f"**Category:** {recommendation['category']}",
        "",
        "### Pattern",
        f"- **Name:** {pattern.get('name', '')}",
        f"- **Sections:** {pattern.get('sections', '')}",
        f"- **CTA Placement:** {pattern.get('cta_placement', '')}",
        f"- **Color Strategy:** {pattern.get('color_strategy', '')}",
        f"- **Conversion Focus:** {pattern.get('conversion', '')}",
        "",
        "### Style",
        f"- **Name:** {style.get('name', '')}",
        f"- **Type:** {style.get('type', '')}",
        f"- **Keywords:** {style.get('keywords', '')}",
        f"- **Best For:** {style.get('best_for', '')}",
        f"- **Performance:** {style.get('performance', '')}",
        f"- **Accessibility:** {style.get('accessibility', '')}",
        "",
        "### Colors",
        "| Role | Value |",
        "|---|---|",
    ]
    for role in [
        "primary",
        "on_primary",
        "secondary",
        "accent",
        "background",
        "foreground",
        "muted",
        "border",
        "destructive",
        "ring",
    ]:
        value = colors.get(role, "")
        if value:
            lines.append(f"| {role.replace('_', ' ').title()} | `{value}` |")
    if colors.get("notes"):
        lines.extend(["", f"*Notes:* {colors['notes']}"])

    lines.extend(
        [
            "",
            "### Typography",
            f"- **Heading:** {typography.get('heading', '')}",
            f"- **Body:** {typography.get('body', '')}",
            f"- **Mood:** {typography.get('mood', '')}",
            f"- **Best For:** {typography.get('best_for', '')}",
            f"- **Google Fonts:** {typography.get('google_fonts_url', '')}",
            "",
            "### Key Effects",
            str(recommendation["key_effects"]),
            "",
            "### Avoid",
            str(recommendation["anti_patterns"] or "No specific anti-patterns found."),
            "",
            "### Pre-Delivery Checklist",
            "- No emoji as icons; use SVG icon libraries where available.",
            "- Interactive controls have visible hover, pressed, disabled, loading, and focus states.",
            "- Text contrast meets WCAG AA and focus states are keyboard-visible.",
            "- Motion respects reduced-motion preferences.",
            "- Layout is checked at 375px, 768px, 1024px, and 1440px.",
        ]
    )
    return "\n".join(lines)


def _format_design_system_ascii(recommendation: dict[str, object]) -> str:
    style = recommendation["style"]
    colors = recommendation["colors"]
    typography = recommendation["typography"]
    if not isinstance(style, dict): raise TypeError("'style' must be a dict")
    if not isinstance(colors, dict): raise TypeError("'colors' must be a dict")
    if not isinstance(typography, dict): raise TypeError("'typography' must be a dict")

    return "\n".join(
        [
            f"DESIGN SYSTEM: {recommendation['project_name']}",
            f"Category: {recommendation['category']}",
            f"Style: {style.get('name', '')}",
            f"Colors: primary {colors.get('primary', '')}, accent {colors.get('accent', '')}, background {colors.get('background', '')}",
            f"Typography: {typography.get('heading', '')} / {typography.get('body', '')}",
            f"Effects: {recommendation['key_effects']}",
            f"Avoid: {recommendation['anti_patterns'] or 'No specific anti-patterns found.'}",
        ]
    )

"""Language-aware content compression helpers for token optimization."""


import re
from dataclasses import dataclass
from enum import Enum

from .token_filter import FilterLevel


class Language(Enum):
    """Supported language categories for source compression."""

    RUST = "rust"
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    C = "c"
    CPP = "cpp"
    JAVA = "java"
    RUBY = "ruby"
    SHELL = "shell"
    DATA = "data"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CommentPatterns:
    """Comment syntax for one language category."""

    line: str | None = None
    block_start: str | None = None
    block_end: str | None = None
    doc_line: str | None = None
    doc_block_start: str | None = None


_EXTENSION_MAP = {
    "rs": Language.RUST,
    "py": Language.PYTHON,
    "pyw": Language.PYTHON,
    "js": Language.JAVASCRIPT,
    "mjs": Language.JAVASCRIPT,
    "cjs": Language.JAVASCRIPT,
    "ts": Language.TYPESCRIPT,
    "tsx": Language.TYPESCRIPT,
    "go": Language.GO,
    "c": Language.C,
    "h": Language.C,
    "cpp": Language.CPP,
    "cc": Language.CPP,
    "cxx": Language.CPP,
    "hpp": Language.CPP,
    "java": Language.JAVA,
    "rb": Language.RUBY,
    "sh": Language.SHELL,
    "bash": Language.SHELL,
    "zsh": Language.SHELL,
    "json": Language.DATA,
    "jsonc": Language.DATA,
    "yaml": Language.DATA,
    "yml": Language.DATA,
    "toml": Language.DATA,
    "xml": Language.DATA,
    "csv": Language.DATA,
    "md": Language.DATA,
    "txt": Language.DATA,
    "lock": Language.DATA,
    "sql": Language.DATA,
    "env": Language.DATA,
}

_COMMENT_PATTERNS = {
    Language.RUST: CommentPatterns("//", "/*", "*/", "///", "/**"),
    Language.PYTHON: CommentPatterns("#", '"""', '"""', None, '"""'),
    Language.JAVASCRIPT: CommentPatterns("//", "/*", "*/", None, "/**"),
    Language.TYPESCRIPT: CommentPatterns("//", "/*", "*/", None, "/**"),
    Language.GO: CommentPatterns("//", "/*", "*/", None, "/**"),
    Language.C: CommentPatterns("//", "/*", "*/", None, "/**"),
    Language.CPP: CommentPatterns("//", "/*", "*/", None, "/**"),
    Language.JAVA: CommentPatterns("//", "/*", "*/", None, "/**"),
    Language.RUBY: CommentPatterns("#", "=begin", "=end", None, None),
    Language.SHELL: CommentPatterns("#", None, None, None, None),
    Language.DATA: CommentPatterns(),
    Language.UNKNOWN: CommentPatterns("//", "/*", "*/", None, None),
}

_MULTIPLE_BLANK_LINES = re.compile(r"\n{3,}")
_TRAILING_WHITESPACE = re.compile(r"[ \t]+$", re.MULTILINE)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_IMPORT_PATTERN = re.compile(r"^(use |import |from |require\(|#include)")
_FUNC_SIGNATURE = re.compile(
    r"^(pub\s+)?(async\s+)?"
    r"(fn|def|function|func|class|struct|enum|trait|interface|type)\s+\w+"
)
_CONSTANT_PREFIXES = (
    "const ",
    "static ",
    "let ",
    "pub const ",
    "pub static ",
    "export const ",
    "final ",
)


def detect_language(extension: str) -> Language:
    """Detect a language from a file extension or extension-like hint."""
    normalized = extension.lower().strip().lstrip(".")
    if "/" in normalized or "\\" in normalized:
        normalized = normalized.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if "." in normalized:
        normalized = normalized.rsplit(".", 1)[-1]
    return _EXTENSION_MAP.get(normalized, Language.UNKNOWN)


def minimal_filter(content: str, lang: Language) -> str:
    """Strip non-doc comments and collapse redundant whitespace."""
    if lang == Language.DATA:
        return normalize_whitespace(content)

    patterns = _COMMENT_PATTERNS.get(lang, _COMMENT_PATTERNS[Language.UNKNOWN])
    result: list[str] = []
    in_block_comment = False
    in_python_docstring = False

    for line in content.splitlines():
        trimmed = line.strip()

        if lang == Language.PYTHON and _starts_python_docstring(trimmed):
            in_python_docstring = not _is_single_line_python_docstring(trimmed)
            result.append(line)
            continue

        if lang == Language.PYTHON and in_python_docstring:
            result.append(line)
            if _ends_python_docstring(trimmed):
                in_python_docstring = False
            continue

        if patterns.block_start and patterns.block_end:
            if in_block_comment:
                if patterns.block_end in trimmed:
                    in_block_comment = False
                continue

            block_index = trimmed.find(patterns.block_start)
            if block_index >= 0:
                doc_start = patterns.doc_block_start
                is_doc_block = bool(doc_start and trimmed.startswith(doc_start))
                if not is_doc_block:
                    if patterns.block_end not in trimmed[block_index + len(patterns.block_start) :]:
                        in_block_comment = True
                    continue

        if patterns.line and trimmed.startswith(patterns.line):
            if patterns.doc_line and trimmed.startswith(patterns.doc_line):
                result.append(line)
            continue

        result.append(line)

    return normalize_whitespace("\n".join(result))


def aggressive_filter(content: str, lang: Language) -> str:
    """Keep imports, signatures, and constants while removing implementation bodies."""
    if lang == Language.DATA:
        return minimal_filter(content, lang)

    minimal = minimal_filter(content, lang)
    if lang == Language.PYTHON:
        return _aggressive_python_filter(minimal)
    return _aggressive_brace_filter(minimal)


def smart_truncate(content: str, max_lines: int, lang: Language) -> str:
    """Truncate content while prioritizing structurally important lines."""
    lines = content.splitlines()
    if len(lines) <= max_lines:
        return content

    result: list[str] = []
    kept_lines = 0
    target = max(1, max_lines - 1)
    early_line_budget = max(1, max_lines // 2)

    for line in lines:
        trimmed = line.strip()
        is_important = _is_structural_line(trimmed, lang)
        if is_important or kept_lines < early_line_budget:
            result.append(line)
            kept_lines += 1
        if kept_lines >= target:
            break

    result.append(f"[{len(lines) - kept_lines} more lines]")
    return "\n".join(result)


def normalize_whitespace(content: str) -> str:
    """Collapse redundant blank lines and strip trailing whitespace."""
    content = _TRAILING_WHITESPACE.sub("", content)
    content = _MULTIPLE_BLANK_LINES.sub("\n\n", content)
    return content.strip()


def deduplicate_lines(lines: list[str], max_repeats: int = 2) -> list[str]:
    """Collapse consecutive duplicate lines with a repeat-count marker."""
    if not lines:
        return lines

    max_repeats = max(1, max_repeats)
    result: list[str] = []
    current = lines[0]
    count = 1

    for line in lines[1:]:
        if line == current:
            count += 1
            continue
        _append_deduplicated_run(result, current, count, max_repeats)
        current = line
        count = 1

    _append_deduplicated_run(result, current, count, max_repeats)
    return result


def filter_markdown(content: str) -> str:
    """Conservatively compress markdown while preserving document content."""
    content = _HTML_COMMENT.sub("", content)
    return normalize_whitespace(content)


def filter_content(content: str, lang: Language, level: FilterLevel) -> str:
    """Apply a compression level to content."""
    if level == FilterLevel.NONE:
        return content
    if level == FilterLevel.MINIMAL:
        return minimal_filter(content, lang)
    return aggressive_filter(content, lang)


def _aggressive_python_filter(content: str) -> str:
    result: list[str] = []
    skipping_body = False
    body_indent = 0
    placeholder_added = False

    for line in content.splitlines():
        trimmed = line.strip()
        indent = len(line) - len(line.lstrip())

        if not trimmed:
            continue

        if skipping_body and indent > body_indent:
            if not placeholder_added:
                result.append("    # ... implementation")
                placeholder_added = True
            continue
        if skipping_body and indent <= body_indent:
            skipping_body = False
            placeholder_added = False

        if _IMPORT_PATTERN.match(trimmed) or trimmed.startswith("@"):
            result.append(line)
            continue
        if _FUNC_SIGNATURE.match(trimmed):
            result.append(line)
            if trimmed.endswith(":"):
                skipping_body = True
                body_indent = indent
                placeholder_added = False
            continue
        if _is_constant_line(trimmed):
            result.append(line)

    return "\n".join(result).strip()


def _aggressive_brace_filter(content: str) -> str:
    result: list[str] = []
    in_impl_body = False
    brace_depth = 0
    placeholder_added = False
    max_lines = 50000
    processed_lines = 0

    for line in content.splitlines():
        processed_lines += 1
        if processed_lines > max_lines:
            result.append("    # ... truncated (file too large)")
            break
        trimmed = line.strip()
        if not trimmed:
            continue

        if _IMPORT_PATTERN.match(trimmed):
            result.append(line)
            continue
        if _FUNC_SIGNATURE.match(trimmed):
            result.append(line)
            in_impl_body = "{" in trimmed or trimmed.endswith(";") is False
            brace_depth = max(0, trimmed.count("{") - trimmed.count("}"))
            placeholder_added = False
            continue
        if _is_constant_line(trimmed):
            result.append(line)
            continue

        if in_impl_body:
            brace_depth += trimmed.count("{") - trimmed.count("}")
            brace_depth = max(0, brace_depth)
            if trimmed in {"{", "}"}:
                result.append(line)
            elif not placeholder_added:
                result.append("    # ... implementation")
                placeholder_added = True
            if brace_depth <= 0:
                in_impl_body = False

    return "\n".join(result).strip()


def _is_structural_line(trimmed: str, lang: Language) -> bool:
    return (
        bool(_FUNC_SIGNATURE.match(trimmed))
        or bool(_IMPORT_PATTERN.match(trimmed))
        or _is_constant_line(trimmed)
        or trimmed.startswith("pub ")
        or trimmed.startswith("export ")
        or trimmed in {"}", "{"}
    )


def _is_constant_line(trimmed: str) -> bool:
    return trimmed.startswith(_CONSTANT_PREFIXES) or bool(
        re.match(r"^[A-Z][A-Z0-9_]*\s*=", trimmed)
    )


def _starts_python_docstring(trimmed: str) -> bool:
    if not (trimmed.startswith('"""') or trimmed.startswith("'''")):
        return False
    # Exclude assignments and expressions: result = """..."""
    before = trimmed.lstrip().split('"""')[0] if '"""' in trimmed else trimmed.lstrip().split("'''")[0]
    return not before or before.rstrip().endswith((":", "("))


def _ends_python_docstring(trimmed: str) -> bool:
    return trimmed.endswith('"""') or trimmed.endswith("'''")


def _is_single_line_python_docstring(trimmed: str) -> bool:
    if trimmed.startswith('"""'):
        return len(trimmed) > 3 and trimmed.endswith('"""')
    if trimmed.startswith("'''"):
        return len(trimmed) > 3 and trimmed.endswith("'''")
    return False


def _append_deduplicated_run(
    result: list[str], line: str, count: int, max_repeats: int
) -> None:
    kept = min(count, max_repeats)
    result.extend([line] * kept)
    omitted = count - kept
    if omitted > 0:
        result.append(f"  ... (repeated {omitted} more times)")

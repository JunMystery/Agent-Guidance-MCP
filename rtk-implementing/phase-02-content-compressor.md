# Phase 02: Content Compressor

Status: ⬜ Pending
Dependencies: Phase 01 (Core Filter Engine)

## Objective

Port RTK's **source code filtering** and **content compression** strategies into a Python module (`content_compressor.py`). This module provides language-aware content reduction — stripping comments, collapsing whitespace, extracting signatures, and deduplicating lines. These are the strategies that deliver RTK's 60-90% token savings.

## Background: RTK's Source Code Filters

RTK has **3 filter levels** (from `src/core/filter.rs`):

| Level | What it does | Token Savings |
|-------|-------------|---------------|
| `None` | Pass-through, no filtering | 0% |
| `Minimal` | Strip comments + collapse blank lines | ~40-60% |
| `Aggressive` | Keep only signatures + imports (strip function bodies) | ~70-90% |

### Language-Aware Comment Patterns

RTK detects language by file extension and applies appropriate comment stripping:

```
Rust:     // line, /* block */, /// doc, /** doc block */
Python:   # line, """ docstring """
JS/TS:    // line, /* block */, /** JSDoc */
Go/C/C++: // line, /* block */, /** doc */
Ruby:     # line, =begin/=end block
Shell:    # line
Data:     (no comment stripping — JSON, YAML, TOML, XML, CSV, etc.)
```

## What to Port

### 1. Language Detection
**RTK Source:** `src/core/filter.rs` lines 41-77

```python
from enum import Enum

class Language(Enum):
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
    DATA = "data"      # JSON, YAML, TOML, XML, CSV — no comment stripping
    UNKNOWN = "unknown"

_EXTENSION_MAP = {
    "rs": Language.RUST,
    "py": Language.PYTHON, "pyw": Language.PYTHON,
    "js": Language.JAVASCRIPT, "mjs": Language.JAVASCRIPT, "cjs": Language.JAVASCRIPT,
    "ts": Language.TYPESCRIPT, "tsx": Language.TYPESCRIPT,
    "go": Language.GO,
    "c": Language.C, "h": Language.C,
    "cpp": Language.CPP, "cc": Language.CPP, "cxx": Language.CPP, "hpp": Language.CPP,
    "java": Language.JAVA,
    "rb": Language.RUBY,
    "sh": Language.SHELL, "bash": Language.SHELL, "zsh": Language.SHELL,
    # Data formats — NO comment stripping (prevents JSON corruption, RTK bug #464)
    "json": Language.DATA, "jsonc": Language.DATA, "yaml": Language.DATA,
    "yml": Language.DATA, "toml": Language.DATA, "xml": Language.DATA,
    "csv": Language.DATA, "md": Language.DATA, "txt": Language.DATA,
    "lock": Language.DATA, "sql": Language.DATA, "env": Language.DATA,
}

def detect_language(extension: str) -> Language:
    """Detect language from file extension."""
    return _EXTENSION_MAP.get(extension.lower().lstrip('.'), Language.UNKNOWN)
```

### 2. Comment Pattern System
**RTK Source:** `src/core/filter.rs` lines 79-137

```python
@dataclass
class CommentPatterns:
    line: str | None = None          # e.g., "//" or "#"
    block_start: str | None = None   # e.g., "/*" or '"""'
    block_end: str | None = None     # e.g., "*/" or '"""'
    doc_line: str | None = None      # e.g., "///"
    doc_block_start: str | None = None  # e.g., "/**"

_COMMENT_PATTERNS: dict[Language, CommentPatterns] = {
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
    Language.DATA: CommentPatterns(None, None, None, None, None),
    Language.UNKNOWN: CommentPatterns("//", "/*", "*/", None, None),
}
```

### 3. Minimal Filter — Comment Stripping + Whitespace Collapse
**RTK Source:** `src/core/filter.rs` lines 156-231

This is the core content reducer. It:
1. Strips single-line comments (but keeps doc comments like `///`)
2. Strips block comments (but keeps Python docstrings in minimal mode)
3. Collapses 3+ consecutive blank lines to 2

```python
_MULTIPLE_BLANK_LINES = re.compile(r'\n{3,}')
_TRAILING_WHITESPACE = re.compile(r'[ \t]+$', re.MULTILINE)

def minimal_filter(content: str, lang: Language) -> str:
    """Strip comments and collapse whitespace. Preserves doc comments."""
    patterns = _COMMENT_PATTERNS.get(lang, _COMMENT_PATTERNS[Language.UNKNOWN])
    lines = content.splitlines()
    result = []
    in_block_comment = False
    in_docstring = False
    
    for line in lines:
        trimmed = line.strip()
        
        # Handle block comments
        if patterns.block_start and patterns.block_end:
            if not in_docstring and patterns.block_start in trimmed:
                doc_start = patterns.doc_block_start or "###"
                if not trimmed.startswith(doc_start):
                    in_block_comment = True
            if in_block_comment:
                if patterns.block_end in trimmed:
                    in_block_comment = False
                continue
        
        # Handle Python docstrings (keep in minimal mode)
        if lang == Language.PYTHON and trimmed.startswith('"""'):
            in_docstring = not in_docstring
            result.append(line)
            continue
        if in_docstring:
            result.append(line)
            continue
        
        # Skip single-line comments (keep doc comments)
        if patterns.line and trimmed.startswith(patterns.line):
            if patterns.doc_line and trimmed.startswith(patterns.doc_line):
                result.append(line)
            continue
        
        result.append(line)
    
    text = '\n'.join(result)
    text = _MULTIPLE_BLANK_LINES.sub('\n\n', text)
    return text.strip()
```

### 4. Aggressive Filter — Signatures Only
**RTK Source:** `src/core/filter.rs` lines 233-313

This is the most aggressive reducer. It:
1. Applies minimal filter first
2. Keeps only: imports, function/class signatures, type definitions, constants
3. Strips function bodies (replaces with `// ... implementation`)
4. Achieves 70-90% token reduction

```python
_IMPORT_PATTERN = re.compile(
    r'^(use |import |from |require\(|#include)'
)
_FUNC_SIGNATURE = re.compile(
    r'^(pub\s+)?(async\s+)?(fn|def|function|func|class|struct|enum|trait|interface|type)\s+\w+'
)

def aggressive_filter(content: str, lang: Language) -> str:
    """Keep only signatures + imports, strip function bodies."""
    # Data formats must NEVER be code-filtered (prevents JSON corruption)
    if lang == Language.DATA:
        return minimal_filter(content, lang)
    
    minimal = minimal_filter(content, lang)
    result = []
    brace_depth = 0
    in_impl_body = False
    
    for line in minimal.splitlines():
        trimmed = line.strip()
        
        # Always keep imports
        if _IMPORT_PATTERN.match(trimmed):
            result.append(line)
            continue
        
        # Always keep function/struct/class signatures
        if _FUNC_SIGNATURE.match(trimmed):
            result.append(line)
            in_impl_body = True
            brace_depth = 0
            continue
        
        # Track brace depth for implementation bodies
        open_braces = trimmed.count('{')
        close_braces = trimmed.count('}')
        
        if in_impl_body:
            brace_depth += open_braces - close_braces
            # Only keep opening/closing braces at top level
            if brace_depth <= 1 and trimmed in ('{', '}') or trimmed.endswith('{'):
                result.append(line)
            if brace_depth <= 0:
                in_impl_body = False
                if trimmed and trimmed != '}':
                    result.append("    # ... implementation")
            continue
        
        # Keep type definitions and constants
        if any(trimmed.startswith(prefix) for prefix in (
            'const ', 'static ', 'let ', 'pub const ', 'pub static '
        )):
            result.append(line)
    
    return '\n'.join(result).strip()
```

### 5. Smart Truncation — Structural Priority
**RTK Source:** `src/core/filter.rs` lines 323-362

Prioritizes structurally important lines (function signatures, imports, exports) when truncating:

```python
def smart_truncate(content: str, max_lines: int, lang: Language) -> str:
    """Truncate keeping structurally important lines (signatures, imports)."""
    lines = content.splitlines()
    if len(lines) <= max_lines:
        return content
    
    result = []
    kept_lines = 0
    
    for line in lines:
        trimmed = line.strip()
        is_important = (
            _FUNC_SIGNATURE.match(trimmed)
            or _IMPORT_PATTERN.match(trimmed)
            or trimmed.startswith('pub ')
            or trimmed.startswith('export ')
            or trimmed in ('}', '{')
        )
        
        if is_important or kept_lines < max_lines // 2:
            result.append(line)
            kept_lines += 1
        
        if kept_lines >= max_lines - 1:
            break
    
    # Clean end-of-output marker (not code syntax, unambiguous to AI)
    result.append(f"[{len(lines) - kept_lines} more lines]")
    return '\n'.join(result)
```

### 6. Whitespace Normalization (Additional to RTK)

For MCP content specifically (markdown documents, long text), additional compression:

```python
def normalize_whitespace(content: str) -> str:
    """Collapse redundant whitespace while preserving code blocks."""
    # Collapse multiple blank lines to max 1
    content = re.sub(r'\n{3,}', '\n\n', content)
    # Strip trailing whitespace from each line
    content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
    return content.strip()
```

### 7. Log/Output Deduplication (from RTK's log filter)
**RTK Source:** `src/cmds/system/log_cmd.rs`

Collapse repeated identical or near-identical lines with counts:

```python
def deduplicate_lines(lines: list[str], max_repeats: int = 2) -> list[str]:
    """Collapse consecutive duplicate lines with count markers."""
    if not lines:
        return lines
    
    result = []
    prev_line = None
    repeat_count = 0
    
    for line in lines:
        if line == prev_line:
            repeat_count += 1
        else:
            if repeat_count > max_repeats:
                result.append(f"  ... (repeated {repeat_count - max_repeats} more times)")
            prev_line = line
            repeat_count = 0
            result.append(line)
    
    if repeat_count > max_repeats:
        result.append(f"  ... (repeated {repeat_count - max_repeats} more times)")
    
    return result
```

### 8. Filter Level Dispatcher

```python
class FilterLevel(Enum):
    NONE = "none"
    MINIMAL = "minimal"
    AGGRESSIVE = "aggressive"

def filter_content(content: str, lang: Language, level: FilterLevel) -> str:
    """Apply the appropriate filter level to content."""
    if level == FilterLevel.NONE:
        return content
    if level == FilterLevel.MINIMAL:
        return minimal_filter(content, lang)
    return aggressive_filter(content, lang)
```

## Implementation Steps

1. [ ] Create `src/agent_guidance_mcp/content_compressor.py`
2. [ ] Implement `Language` enum and `detect_language()` with extension mapping
3. [ ] Implement `CommentPatterns` dataclass and pattern registry
4. [ ] Implement `minimal_filter()` — comment stripping + whitespace collapse
5. [ ] Implement `aggressive_filter()` — signatures-only extraction
6. [ ] Implement `smart_truncate()` — structure-aware truncation
7. [ ] Implement `normalize_whitespace()` — general text compression
8. [ ] Implement `deduplicate_lines()` — log/output dedup
9. [ ] Implement `FilterLevel` enum and `filter_content()` dispatcher
10. [ ] Implement `filter_markdown()` — markdown-specific compression for standards docs

## Files to Create/Modify

- `src/agent_guidance_mcp/content_compressor.py` — **[NEW]** Content compression engine
- `tests/test_content_compressor.py` — **[NEW]** Unit tests

## Test Criteria

- [ ] `detect_language()` correctly identifies all supported extensions
- [ ] `detect_language()` returns `DATA` for JSON/YAML/TOML (prevents corruption)
- [ ] `minimal_filter()` strips single-line comments but keeps doc comments
- [ ] `minimal_filter()` strips block comments correctly
- [ ] `minimal_filter()` preserves Python docstrings
- [ ] `minimal_filter()` does NOT strip comments from DATA languages (JSON bug #464)
- [ ] `aggressive_filter()` keeps only imports, signatures, constants
- [ ] `aggressive_filter()` strips function bodies
- [ ] `aggressive_filter()` falls back to minimal for DATA formats
- [ ] `smart_truncate()` prioritizes structural lines (signatures, imports)
- [ ] `deduplicate_lines()` collapses repeated lines with counts
- [ ] End-to-end: Python file reduced by >40% with minimal, >70% with aggressive

## Notes

- **JSON safety is critical**: RTK had bug #464 where `packages/*` in `package.json` was treated as a block comment start. The `DATA` language guard prevents this.
- **Python docstrings**: RTK explicitly preserves Python docstrings in minimal mode because they serve as API documentation. We replicate this behavior.
- **Brace tracking**: The aggressive filter tracks `{` and `}` depth for languages like Rust/JS/Java. Python uses indentation instead — aggressive mode for Python should use a different strategy (TODO: enhance in later phase).

---
Next Phase: [Phase 03 — Response Optimizer](./phase-03-response-optimizer.md)

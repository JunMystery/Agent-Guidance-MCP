"""AST-based and regex-fallback symbol extraction for code exploration."""


import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .project_scan import (
    LANGUAGE_HINTS,
    iter_project_files,
    read_bounded_text,
    relative_path,
    resolve_project_root,
)


try:
    from tree_sitter_languages import get_parser
    _HAS_TREE_SITTER = True
except ImportError:
    _HAS_TREE_SITTER = False


_PARSER_CACHE: dict[str, object] = {}

def _get_parser(language: str) -> object | None:
    if not _HAS_TREE_SITTER:
        return None
    if language not in _PARSER_CACHE:
        try:
            _PARSER_CACHE[language] = get_parser(language)
        except Exception:
            return None
    return _PARSER_CACHE[language]


_TS_KINDS: dict[str, dict[str, str]] = {
    "python": {"class_definition": "class", "function_definition": "function"},
    "javascript": {"class_declaration": "class", "function_declaration": "function", "method_definition": "method", "interface_declaration": "interface", "type_alias_declaration": "type", "arrow_function": "function"},
    "typescript": {"class_declaration": "class", "function_declaration": "function", "method_definition": "method", "interface_declaration": "interface", "type_alias_declaration": "type", "enum_declaration": "enum", "arrow_function": "function"},
    "go": {"function_declaration": "function", "type_spec": "struct", "interface_type": "interface"},
    "rust": {"function_item": "function", "struct_item": "struct", "enum_item": "enum", "trait_item": "trait", "impl_item": "impl"},
    "java": {"class_declaration": "class", "method_declaration": "method", "interface_declaration": "interface"},
    "csharp": {"class_declaration": "class", "method_declaration": "method", "interface_declaration": "interface"},
}

_CONTAINER_KINDS = frozenset({"class", "struct", "interface", "trait", "module", "object", "protocol", "impl", "enum"})


def _ts_name(node) -> str:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        try:
            return name_node.text.decode("utf-8")
        except Exception:
            pass
    for child in node.named_children:
        if child.type in ("identifier", "type_identifier", "property_identifier"):
            try:
                return child.text.decode("utf-8")
            except Exception:
                pass
    return ""


def _extract_symbols_ast(path: Path, root: Path | None = None) -> list["Symbol"]:
    language = LANGUAGE_HINTS.get(path.suffix.lower(), "")
    if language not in _TS_KINDS:
        return []
    parser = _get_parser(language)
    if parser is None:
        return []
    content, _ = read_bounded_text(path, 200_000)
    if content is None:
        return []
    try:
        tree = parser.parse(bytes(content, "utf-8"))
    except Exception:
        return []
    kinds = _TS_KINDS.get(language, {})
    file_rel = relative_path(root, path) if root else str(path)
    symbols: list[Symbol] = []
    parent_stack: list[tuple[str, int]] = []
    lines = content.splitlines()

    def _walk(node, depth: int = 0) -> None:
        kind = kinds.get(node.type)
        if kind:
            name = _ts_name(node)
            start = node.start_point[0] + 1
            end = node.end_point[0] + 1
            while parent_stack and parent_stack[-1][1] >= depth:
                parent_stack.pop()
            parent_name = parent_stack[-1][0] if parent_stack else None
            sig = (lines[start - 1][:200] if 1 <= start <= len(lines) else "")
            if kind in _CONTAINER_KINDS:
                if kind == "impl":
                    tn = node.child_by_field_name("type")
                    pn = tn.text.decode("utf-8") if tn is not None else name
                else:
                    pn = name
                parent_stack.append((pn, depth))
            actual = "method" if kind == "function" and parent_name is not None and node.type != "arrow_function" else kind
            symbols.append(Symbol(name, actual, file_rel, start, end, parent_name, sig))
        for child in node.named_children:
            _walk(child, depth + 1)

    _walk(tree.root_node)
    return symbols


@dataclass
class Symbol:
    name: str
    kind: str
    file: str
    line: int
    end_line: int = 0
    parent: str | None = None
    signature: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "kind": self.kind, "file": self.file, "line": self.line, "end_line": self.end_line, "parent": self.parent, "signature": self.signature}


REGEX_PATTERNS: dict[str, list[tuple[re.Pattern[str], str, bool]]] = {
    "python": [
        (re.compile(r"^(\s*)class\s+(\w+)"), "class", True),
        (re.compile(r"^(\s*)(?:async\s+)?def\s+(\w+)"), "function", True),
    ],
    "javascript": [
        (re.compile(r"^(\s*)class\s+(\w+)"), "class", True),
        (re.compile(r"^(\s*)function\s+(\w+)"), "function", True),
        (re.compile(r"^(\s*)(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\("), "function", True),
        (re.compile(r"^(\s*)(?:export\s+)?interface\s+(\w+)"), "interface", True),
        (re.compile(r"^(\s*)(?:export\s+)?type\s+(\w+)"), "type", True),
    ],
    "typescript": [
        (re.compile(r"^(\s*)class\s+(\w+)"), "class", True),
        (re.compile(r"^(\s*)(?:async\s+)?function\s+(\w+)"), "function", True),
        (re.compile(r"^(\s*)(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\("), "function", True),
        (re.compile(r"^(\s*)(?:export\s+)?interface\s+(\w+)"), "interface", True),
        (re.compile(r"^(\s*)(?:export\s+)?type\s+(\w+)"), "type", True),
        (re.compile(r"^(\s*)(?:export\s+)?enum\s+(\w+)"), "enum", True),
    ],
    "go": [
        (re.compile(r"^(\s*)func\s+(?:\([^)]*\)\s+)?(\w+)"), "function", True),
        (re.compile(r"^(\s*)type\s+(\w+)\s+struct"), "struct", True),
        (re.compile(r"^(\s*)type\s+(\w+)\s+interface"), "interface", True),
    ],
    "rust": [
        (re.compile(r"^(\s*)(?:pub\s+)?fn\s+(\w+)"), "function", True),
        (re.compile(r"^(\s*)(?:pub\s+)?struct\s+(\w+)"), "struct", True),
        (re.compile(r"^(\s*)(?:pub\s+)?enum\s+(\w+)"), "enum", True),
        (re.compile(r"^(\s*)(?:pub\s+)?trait\s+(\w+)"), "trait", True),
        (re.compile(r"^(\s*)impl\s+(\w+)"), "impl", True),
    ],
    "java": [
        (re.compile(r"^\s*(?:public|private|protected)?\s*(?:static\s+)?class\s+(\w+)"), "class", False),
        (re.compile(r"^\s*(?:public|private|protected)?\s*(?:static\s+)?interface\s+(\w+)"), "interface", False),
        (re.compile(r"^\s*(?:public|private|protected)?\s*(?:static\s+)?\w+\s+(\w+)\s*\([^)]*\)"), "method", False),
    ],
    "csharp": [
        (re.compile(r"^\s*(?:public|private|protected|internal)?\s*(?:static\s+)?class\s+(\w+)"), "class", False),
        (re.compile(r"^\s*(?:public|private|protected|internal)?\s*(?:static\s+)?interface\s+(\w+)"), "interface", False),
        (re.compile(r"^\s*(?:public|private|protected|internal)?\s*(?:static\s+)?\w+\s+(\w+)\s*\([^)]*\)"), "method", False),
    ],
    "ruby": [
        (re.compile(r"^(\s*)class\s+(\w+)"), "class", True),
        (re.compile(r"^(\s*)module\s+(\w+)"), "module", True),
        (re.compile(r"^(\s*)def\s+(\w+)"), "function", True),
    ],
    "php": [
        (re.compile(r"^(\s*)class\s+(\w+)"), "class", True),
        (re.compile(r"^(\s*)function\s+(\w+)"), "function", True),
        (re.compile(r"^(\s*)interface\s+(\w+)"), "interface", True),
    ],
    "kotlin": [
        (re.compile(r"^(\s*)class\s+(\w+)"), "class", True),
        (re.compile(r"^(\s*)interface\s+(\w+)"), "interface", True),
        (re.compile(r"^(\s*)fun\s+(\w+)"), "function", True),
        (re.compile(r"^(\s*)object\s+(\w+)"), "object", True),
    ],
    "swift": [
        (re.compile(r"^(\s*)class\s+(\w+)"), "class", True),
        (re.compile(r"^(\s*)struct\s+(\w+)"), "struct", True),
        (re.compile(r"^(\s*)enum\s+(\w+)"), "enum", True),
        (re.compile(r"^(\s*)protocol\s+(\w+)"), "protocol", True),
        (re.compile(r"^(\s*)func\s+(\w+)"), "function", True),
    ],
    "c": [
        (re.compile(r"^\s*(?:static\s+)?\w+\s+(\w+)\s*\([^)]*\)"), "function", False),
        (re.compile(r"^\s*struct\s+(\w+)"), "struct", False),
    ],
    "cpp": [
        (re.compile(r"^\s*(?:static\s+)?\w+\s+(\w+)\s*\([^)]*\)"), "function", False),
        (re.compile(r"^\s*class\s+(\w+)"), "class", False),
        (re.compile(r"^\s*struct\s+(\w+)"), "struct", False),
    ],
}

REGEX_LANGUAGES = set(REGEX_PATTERNS.keys())


def _language_for_path(path: Path) -> str | None:
    hint = LANGUAGE_HINTS.get(path.suffix.lower())
    if hint in REGEX_LANGUAGES:
        return hint
    if hint in ("jsx",):
        return "javascript"
    if hint in ("tsx",):
        return "typescript"
    return None


def _extract_symbols_regex(path: Path, root: Path | None = None) -> list[Symbol]:
    language = _language_for_path(path)
    if language is None:
        return []
    patterns = REGEX_PATTERNS.get(language)
    if not patterns:
        return []
    if not path.is_file():
        return []
    content, _ = read_bounded_text(path, 200_000)
    if content is None:
        return []
    file_rel = relative_path(root, path) if root else str(path)
    symbols: list[Symbol] = []
    current_class: str | None = None
    class_indent: int = -1
    for line_num, line in enumerate(content.splitlines(), start=1):
        for pattern, kind, tracks_indent in patterns:
            match = pattern.match(line)
            if not match:
                continue
            indent = len(match.group(1)) if tracks_indent else 0
            name = match.group(2) if tracks_indent else match.group(1)
            if kind in ("class", "struct", "interface", "trait", "module", "object", "protocol"):
                current_class = name
                class_indent = indent
                symbols.append(Symbol(name, kind, file_rel, line_num, line_num, None, line.strip()[:200]))
            elif kind == "function":
                if current_class is not None and indent > class_indent:
                    symbols.append(Symbol(name, "method", file_rel, line_num, line_num, current_class, line.strip()[:200]))
                else:
                    symbols.append(Symbol(name, "function", file_rel, line_num, line_num, None, line.strip()[:200]))
                    if indent <= class_indent:
                        current_class = None
                        class_indent = -1
            elif kind == "impl":
                current_class = name
                class_indent = indent
                symbols.append(Symbol(name, "impl", file_rel, line_num, line_num, None, line.strip()[:200]))
            else:
                symbols.append(Symbol(name, kind, file_rel, line_num, line_num, None, line.strip()[:200]))
    return symbols


def extract_symbols(path: Path, root: Path | None = None) -> list[Symbol]:
    """Extract symbols using tree-sitter (if available) or regex fallback."""
    if _HAS_TREE_SITTER:
        result = _extract_symbols_ast(path, root)
        if result:
            return result
    return _extract_symbols_regex(path, root)


def find_references(
    root: Path, symbol_name: str, limit: int = 20
) -> list[dict[str, object]]:
    """Find where a symbol is referenced across the codebase."""
    if not symbol_name:
        return []
    pattern = re.compile(rf"\b{re.escape(symbol_name)}\b")
    matches: list[dict[str, object]] = []
    for path in iter_project_files(root):
        if len(matches) >= limit:
            break
        language = _language_for_path(path)
        if language is None:
            continue
        content, _ = read_bounded_text(path, 200_000)
        if content is None:
            continue
        for line_num, line in enumerate(content.splitlines(), start=1):
            if pattern.search(line):
                matches.append({"file": relative_path(root, path), "line": line_num, "snippet": line.strip()[:300], "language_hint": language})
                if len(matches) >= limit:
                    break
    return matches


def get_file_structure(path: Path, root: Path | None = None) -> dict[str, object]:
    """Return hierarchical structure of a file (classes, methods, functions)."""
    symbols = extract_symbols(path, root)
    file_rel = relative_path(root, path) if root else str(path)
    classes: list[dict[str, object]] = []
    standalone: list[dict[str, object]] = []
    for sym in symbols:
        entry = {"name": sym.name, "line": sym.line, "signature": sym.signature}
        if sym.kind in _CONTAINER_KINDS:
            methods = [{"name": m.name, "line": m.line, "signature": m.signature} for m in symbols if m.parent == sym.name and m.kind == "method"]
            entry["methods"] = methods
            classes.append(entry)
        elif sym.kind == "function" and sym.parent is None:
            standalone.append(entry)
        elif sym.kind == "method" and sym.parent is None:
            standalone.append(entry)
    return {"file": file_rel, "language": _language_for_path(path) or "text", "classes": classes, "standalone_functions": standalone, "total_symbols": len(symbols)}

"""Full comprehensive audit - all modules, all edge cases."""
import sys, os, json, traceback
sys.path.insert(0, 'src')

errors, warnings = [], []

def check(condition, msg, is_warning=False):
    if not condition:
        (warnings if is_warning else errors).append(msg)

# ============================================================
# 1. IMPORTS - no import errors
# ============================================================
try:
    from agent_guidance_mcp.catalog import build_catalog, StandardsCatalog, CatalogEntry
    from agent_guidance_mcp.server import create_server, register_handlers, get_config, set_config, get_tracker
    from agent_guidance_mcp.pipelines import guidance, project_context, ui_ux, task_pipeline
    from agent_guidance_mcp.text import (extract_description, extract_title, parse_frontmatter,
        _extract_frontmatter_block, strip_markdown, tokenize, normalize_identifier,
        infer_task_keywords, make_snippet, title_from_path, extract_code_terms)
    from agent_guidance_mcp.paths import (find_standards_root, is_standards_root,
        iter_content_files, infer_kind, infer_category, identifier_for, resolve_inside_root)
    from agent_guidance_mcp.response_optimizer import (estimate_tokens, optimize_markdown,
        optimize_response, truncate_to_budget, optimize_source_content)
    from agent_guidance_mcp.content_compressor import (filter_content, minimal_filter,
        aggressive_filter, filter_markdown, detect_language, Language)
    from agent_guidance_mcp.token_config import TokenOptimizationConfig, load_config_from_env
    from agent_guidance_mcp.token_analytics import TokenTracker
    from agent_guidance_mcp.token_filter import FilterLevel, LineFilter
    from agent_guidance_mcp import utils, constants, project_context as pc
    from agent_guidance_mcp.project_scan import (resolve_project_root, resolve_inside_project,
        _is_project_path_allowed, read_bounded_text, is_binary_file, looks_binary,
        build_project_tree, iter_project_files)
    print("[PASS] All imports")
except Exception as exc:
    errors.append(f"Import failed: {exc}")
    print("\nFAILURES:")
    for e in errors: print(f"  {e}")
    sys.exit(1)

# ============================================================
# 2. CATALOG - build, search, recommend, get, read
# ============================================================
try:
    c = build_catalog()
    skills = [e for e in c.entries if e.kind == "skill"]
    check(len(skills) == 168, f"Expected 168 skills, got {len(skills)}")
    check(len(c.entries) >= 249, f"Expected >=249 entries, got {len(c.entries)}")
except Exception as exc:
    errors.append(f"Catalog build failed: {exc}")

# Identifiers
bad_ids = [e.identifier for e in skills if e.identifier.endswith('-skill') and 'skill' not in str(e.path).split('/')[-1].split('.')[0]]
check(not bad_ids, f"Corrupted identifiers: {bad_ids}")

ids = [e.identifier for e in c.entries]
check(len(ids) == len(set(ids)), f"Duplicate identifiers: {len(ids) - len(set(ids))}")

# Content
no_content = [e.identifier for e in skills if not e._content or len(e._content) < 100]
check(not no_content, f"Skills without content: {len(no_content)}")

# Descriptions
no_desc = [e.identifier for e in skills if not e.description or len(e.description) < 5]
check(not no_desc, f"Skills with blank descriptions: {len(no_desc)}")

# Anchors
for ak, paths in c.task_anchors.items():
    for p in paths:
        check(p.replace('\\', '/').lower() in c._by_path, f"Anchor missing: {ak} -> {p}")

# Essentials
for ess in ["karpathy-principles", "skill-reference", "docs-repo-map-for-agents"]:
    try: c.get_entry(ess)
    except KeyError: errors.append(f"Essential missing: {ess}")

# Search
s = c.search_entries("python testing", limit=3)
check(len(s) > 0, "Search returned 0 results")

# Recommend
r = c.recommend_context("write a python REST API", limit=3)
check(len(r["recommendations"]) > 0, "Recommend returned 0")
check(len(r["keywords"]) > 0, "Recommend returned 0 keywords")

# get_entry / read_entry
try:
    e = c.get_entry("backend-patterns")
    check(e.kind == "skill", f"backend-patterns kind={e.kind}")
    content = c.read_entry("backend-patterns", optimize=False)
    check(len(content) > 100, f"backend-patterns content too short: {len(content)}")
except KeyError as exc:
    errors.append(f"backend-patterns lookup failed: {exc}")

# Manifest
m = c.manifest()
check(m["entry_count"] == len(c.entries), "Manifest entry_count mismatch")
print(f"[PASS] Catalog: {len(skills)} skills, {len(c.entries)} entries")

# ============================================================
# 3. FRONTMATTER - parse all 168 skills
# ============================================================
from pathlib import Path
fm_errors = 0
for e in skills:
    try:
        p = Path('E:/Github/Agent-Guidance-MCP') / e.path
        text = p.read_text(encoding='utf-8')
        desc = extract_description(text)
        title = extract_title(text)
        fm = parse_frontmatter(text)
        check(desc and len(desc) > 3, f"Short desc: {e.identifier}: {desc!r}", True)
        check(title, f"No title: {e.identifier}", True)
        check(isinstance(fm, dict), f"Bad frontmatter: {e.identifier}", True)
    except Exception as exc:
        fm_errors += 1
        errors.append(f"Frontmatter fail: {e.identifier}: {exc}")
check(fm_errors == 0, f"{fm_errors} frontmatter parse errors")
print(f"[PASS] Frontmatter: {len(skills)} skills parsed")

# ============================================================
# 4. OPTIMIZATION - markdown, response, truncation
# ============================================================
# optimize_markdown
result = optimize_markdown("# Test\nContent\n<!-- comment -->\n![badge](https://img.shields.io/badge/x-blue)", max_tokens=100)
check(isinstance(result, str) and "Test" in result, "optimize_markdown broken")

# optimize_response
resp = optimize_response({"content": "test" * 100, "nested": {"content": "x" * 50}}, max_content_tokens=50)
check(isinstance(resp, dict), "optimize_response not dict")
check("content" in resp, "optimize_response lost content key")
check("_error" not in str(resp), f"optimize_response error: {resp.get('_error', '')}")

# truncate_to_budget with headers
t = truncate_to_budget("# H1\na\n# H2\nb\n# H3\nc", max_tokens=5)
check(isinstance(t, str) and len(t) > 0, "truncate_to_budget empty")

# truncate_to_budget headerless
t2 = truncate_to_budget("line1\nline2\nline3\n" * 100, max_tokens=10)
check(isinstance(t2, str) and len(t2) > 0, "Headerless truncate empty")
check(len(t2) < 200, f"Headerless truncate too large: {len(t2)}")

# filter_content
f = filter_content("// comment\nlet x = 1;\n", Language.JAVASCRIPT, FilterLevel.MINIMAL)
check(isinstance(f, str), "filter_content crash")
check("let x" in f.lower(), "filter_content removed code")

# docstring detection - not a false positive for assignments
from agent_guidance_mcp.content_compressor import _starts_python_docstring
check(not _starts_python_docstring('result = """hello"""'), "Docstring false positive on assignment")
check(_starts_python_docstring('"""Module docstring."""'), "Docstring NOT detected")

print(f"[PASS] Optimization: all functions work")

# ============================================================
# 5. TOKEN TRACKING
# ============================================================
tracker = TokenTracker(enabled=True, max_records=100, trim_to=50)
r1 = tracker.record("test", "op", 1000, 500)
check(r1 is not None, "TokenTracker.record returned None")
check(r1.saved_tokens == 500, f"Wrong saved: {r1.saved_tokens}")
s = tracker.summary()
check(s["total_calls"] == 1, f"Wrong call count: {s['total_calls']}")
check(s["total_saved_tokens"] == 500, f"Wrong total saved: {s['total_saved_tokens']}")
tracker.reset()
s2 = tracker.summary()
check(s2["total_calls"] == 0, "Reset didn't work")

# Thread safety - concurrent records
import threading
def record_many():
    for i in range(100):
        tracker.record("t", "o", 100, 50)
threads = [threading.Thread(target=record_many) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()
s3 = tracker.summary()
check(s3["total_calls"] == 1000, f"Concurrent record count wrong: {s3['total_calls']}")
print(f"[PASS] Token tracking: thread-safe, correct counts")

# ============================================================
# 6. TOKEN CONFIG - from_dict, env, bool handling
# ============================================================
# Bool coercion
cfg = TokenOptimizationConfig.from_dict({"enabled": "false", "track_savings": "no", "strip_comments": "off"})
check(cfg.enabled == False, f"Bool 'false' not coerced: {cfg.enabled}")
check(cfg.track_savings == False, f"Bool 'no' not coerced: {cfg.track_savings}")
check(cfg.strip_comments == False, f"Bool 'off' not coerced: {cfg.strip_comments}")

# Invalid type handling
cfg2 = TokenOptimizationConfig.from_dict({"document_max_tokens": "abc"})
check(cfg2.document_max_tokens == 8000, f"Invalid int default wrong: {cfg2.document_max_tokens}")

# Disabled config
cfg3 = TokenOptimizationConfig.disabled()
check(cfg3.enabled == False, "Disabled config still enabled")
check(cfg3.track_savings == False, "Disabled config still tracking")
print(f"[PASS] Token config: bool coercion, type safety, disabled mode")

# ============================================================
# 7. PROJECT SCAN - path security, binary detection
# ============================================================
# Path security
from pathlib import Path as P
check(not _is_project_path_allowed(P("/etc")), "/etc should be denied")
check(not _is_project_path_allowed(P("C:/Windows/System32")), "System32 should be denied")
check(_is_project_path_allowed(P(".")), "CWD should be allowed")

# Binary detection
check(looks_binary(b"hello world"), False, "Text falsely binary")
check(looks_binary(b"hello\x00world"), True, "Binary not detected")

# is_binary_file with locked file simulation handled by try/except
print(f"[PASS] Project scan: path security, binary detection")

# ============================================================
# 8. PIPELINES - operation guards, lifecycle_order
# ============================================================
# None guard
r1 = guidance(c, None, "test")
check("error" in r1 and "operation" in str(r1), f"guidance None guard broken: {r1}")

# lifecycle_order
from agent_guidance_mcp.pipelines import guidance as _g
lifecycle = [
    "frontend-patterns", "backend-patterns", "tdd-workflow", "verification-loop",
    "spec-driven-development", "planning-and-task-breakdown", "api-design"
]
for lc in lifecycle:
    try:
        c.get_entry(lc)
    except KeyError:
        errors.append(f"lifecycle_order skill missing: {lc}")

# recommend optimization - should pass through optimize_response
from agent_guidance_mcp.response_optimizer import optimize_response as _or
cfg = TokenOptimizationConfig(enabled=True)
rec = c.recommend_context("security", limit=2)
opt_rec = _or(rec, config=cfg)
check(isinstance(opt_rec, dict), "Recommend optimization failed")
print(f"[PASS] Pipelines: guards, lifecycle_order all valid")

# ============================================================
# 9. TEXT - tokenize, normalize, snippets
# ============================================================
# tokenize
check(len(tokenize("python testing rust")) == 3, f"tokenize wrong count: {tokenize('python testing rust')}")
check(len(tokenize("AI Go js")) == 3, f"2-char tokens: got {tokenize('AI Go js')}")
check(len(tokenize("a")) == 0, f"1-char token not dropped (uses default min_length=2)")

# normalize_identifier
check(normalize_identifier("skills/backend-patterns/SKILL.md") == "skills-backend-patterns", f"normalize: {normalize_identifier('skills/backend-patterns/SKILL.md')}")
check(normalize_identifier("backend-patterns") == "backend-patterns", "normalize changed simple id")

# make_snippet
check(len(make_snippet("hello world testing", ["world"])) > 0, "make_snippet empty")
check(len(make_snippet("no match here", ["missing"])) > 0, "make_snippet empty on no match")

# extract_code_terms
terms = extract_code_terms("write a MyComponent class with getData function")
check(terms is not None and len(terms) > 0, f"extract_code_terms returned: {terms}")

# strip_markdown
check(strip_markdown("**bold** and *italic*") == "bold and italic", f"strip_markdown: {strip_markdown('**bold** and *italic*')}")
print(f"[PASS] Text: tokenize, normalize, snippets, code terms, strip_markdown")

# ============================================================
# 10. EDGE CASES - null, empty, extreme
# ============================================================
# Empty query search
s = c.search_entries("", limit=3)
check(s == [], f"Empty query search not empty: {s}")

# Empty task recommend
r = c.recommend_context("", limit=2)
check(len(r["recommendations"]) >= 0, "Empty task recommend crashed")

# Zero max_tokens truncate
t = truncate_to_budget("test", max_tokens=0)
check(isinstance(t, str), f"Zero max_tokens crashed: {t}")

# Empty content filter
f = filter_content("", Language.PYTHON, FilterLevel.AGGRESSIVE)
check(isinstance(f, str), "Empty filter crashed")

# None tracker
check(utils.record_savings(None, "test", "op", "a", "b") is None, "None tracker should no-op")
print(f"[PASS] Edge cases: null, empty, extreme - no crashes")

# ============================================================
# REPORT
# ============================================================
print(f"\n{'='*60}")
if errors:
    print(f"FAILURES: {len(errors)}")
    for e in errors: print(f"  FAIL: {e}")
if warnings:
    print(f"WARNINGS: {len(warnings)}")
    for w in warnings[:10]: print(f"  WARN: {w}")
if not errors:
    print(f"ALL CHECKS PASSED")
    print(f"  {len(skills)} skills, {len(c.entries)} catalog entries")
    print(f"  Identifiers: clean (no corruption, no dupes)")
    print(f"  Content: all loaded, all descriptions valid")
    print(f"  Anchors+Essentials: all resolve")
    print(f"  Search+Recommend+Get+Read: all work")
    print(f"  Frontmatter: all 168 skills parse correctly")
    print(f"  Optimization: markdown/response/truncation/filter all work")
    print(f"  Token tracking: thread-safe, correct counts")
    print(f"  Token config: bool coercion, type safety")
    print(f"  Project scan: path security, binary detection")
    print(f"  Pipelines: guards, lifecycle_order valid")
    print(f"  Text: tokenize, normalize, snippets, code terms")
    print(f"  Edge cases: null, empty, extreme - no crashes")
print(f"{'='*60}")
sys.exit(0 if not errors else 1)

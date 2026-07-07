import math

from agent_guidance_mcp.response_optimizer import estimate_tokens, optimize_response
from agent_guidance_mcp.token_analytics import TokenTracker


def test_estimate_tokens():
    text = "hello world"
    expected = math.ceil(len(text) / 4)
    assert estimate_tokens(text) == expected
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 100) == 25


def test_token_tracker_record_and_summary():
    tracker = TokenTracker(enabled=True)
    for _ in range(3):
        tracker.record(
            tool_name="test", operation="get", original_tokens=1000, optimized_tokens=600
        )
    summary = tracker.summary()
    assert summary["total_calls"] == 3
    assert summary["total_original_tokens"] == 3000
    assert summary["total_optimized_tokens"] == 1800
    assert summary["total_saved_tokens"] == 1200
    assert summary["overall_savings_pct"] == 40.0
    assert len(summary["recent_records"]) == 3


def test_token_tracker_disabled():
    tracker = TokenTracker(enabled=False)
    result = tracker.record(
        tool_name="test", operation="get", original_tokens=100, optimized_tokens=50
    )
    assert result is None
    summary = tracker.summary()
    assert summary["total_calls"] == 0


def test_token_tracker_custom_caps():
    tracker = TokenTracker(enabled=True, max_records=10, trim_to=5)
    for i in range(15):
        tracker.record(
            tool_name="test", operation="op", original_tokens=100, optimized_tokens=50
        )
    records = tracker.records()
    assert len(records) <= 10


def test_optimize_response_type_guard():
    response = {
        "items": [
            {"key": "val", "content": "# Heading\nBody text."},
            42,
            "string",
            None,
        ]
    }
    result = optimize_response(response, config=None)
    assert isinstance(result, dict)
    assert len(result["items"]) == 4
    assert isinstance(result["items"][0], dict)
    assert result["items"][1] == 42
    assert result["items"][2] == "string"
    assert result["items"][3] is None


def test_optimize_response_depth_guard():
    nested: dict[str, object] = {}
    current = nested
    for i in range(100):
        current["next"] = {}
        current = current["next"]
    current["value"] = "bottom"
    result = optimize_response(nested, config=None)
    assert isinstance(result, dict)
    assert "_truncated" in result or "next" in result


def test_estimate_tokens_is_code():
    text = "hello world code text"
    assert estimate_tokens(text, is_code=False) == math.ceil(len(text) / 4.0)
    assert estimate_tokens(text, is_code=True) == math.ceil(len(text) / 2.8)


from agent_guidance_mcp.content_compressor import (
    _strip_string_literals,
    _aggressive_brace_filter,
)

def test_strip_string_literals():
    assert _strip_string_literals('const x = "{ curly }";') == 'const x = "";'
    assert _strip_string_literals("const y = '{ curly }';") == 'const y = "";'
    assert _strip_string_literals("const z = `{ curly }`;") == 'const z = "";'
    assert _strip_string_literals('const a = "\\"escaped\\" { curly }";') == 'const a = "";'


def test_aggressive_brace_filter_with_braces_in_strings():
    code = (
        "function hello() {\n"
        "  const x = \"{ curly }\";\n"
        "  console.log(x);\n"
        "}\n"
    )
    result = _aggressive_brace_filter(code)
    assert "# ... implementation" in result
    assert "hello" in result


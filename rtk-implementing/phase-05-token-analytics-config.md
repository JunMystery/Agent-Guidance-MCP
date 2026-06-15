# Phase 05: Token Analytics & Configuration

Status: ⬜ Pending
Dependencies: Phase 04 (MCP Pipeline Integration)

## Objective

Port RTK's **token tracking analytics** and create a **configuration system** that allows tuning token budgets, filter levels, and optimization behavior. This phase adds observability — you can see how many tokens are being saved per request.

## Background: RTK's Analytics System

RTK tracks every command in a SQLite database (`src/core/tracking.rs`):
- `commands` table: timestamp, original_cmd, rtk_cmd, input_tokens, output_tokens, saved_tokens, savings_pct, exec_time_ms, project_path
- Token estimation: `ceil(chars / 4)` (~4 chars per token)
- Reporting: `rtk gain` shows daily/weekly/monthly breakdowns with ASCII graphs

For the MCP server, we adapt this to track per-tool-call savings.

## What to Build

### 1. Token Tracker

A lightweight in-memory tracker (no SQLite needed for MCP — simpler is better):

```python
from dataclasses import dataclass, field
from datetime import datetime
import threading

@dataclass
class TokenSavingsRecord:
    """Record of token savings for a single MCP tool call."""
    timestamp: str
    tool_name: str
    operation: str
    original_tokens: int
    optimized_tokens: int
    saved_tokens: int
    savings_pct: float

class TokenTracker:
    """Track token savings across MCP tool calls.
    
    Thread-safe in-memory tracker with summary statistics.
    Inspired by RTK's tracking.rs but simplified for MCP use.
    """
    
    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._records: list[TokenSavingsRecord] = []
        self._lock = threading.Lock()
        self._total_original = 0
        self._total_optimized = 0
        self._call_count = 0
    
    def record(self, tool_name: str, operation: str,
               original_tokens: int, optimized_tokens: int) -> TokenSavingsRecord:
        """Record a token savings event."""
        if not self._enabled:
            return None
        
        saved = original_tokens - optimized_tokens
        pct = round((saved / max(1, original_tokens)) * 100, 1)
        
        record = TokenSavingsRecord(
            timestamp=datetime.utcnow().isoformat() + "Z",
            tool_name=tool_name,
            operation=operation,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            saved_tokens=saved,
            savings_pct=pct,
        )
        
        with self._lock:
            self._records.append(record)
            self._total_original += original_tokens
            self._total_optimized += optimized_tokens
            self._call_count += 1
            
            # Keep last 1000 records to bound memory
            if len(self._records) > 1000:
                self._records = self._records[-500:]
        
        return record
    
    def summary(self) -> dict[str, object]:
        """Return aggregate savings summary."""
        with self._lock:
            total_saved = self._total_original - self._total_optimized
            pct = round((total_saved / max(1, self._total_original)) * 100, 1)
            return {
                "total_calls": self._call_count,
                "total_original_tokens": self._total_original,
                "total_optimized_tokens": self._total_optimized,
                "total_saved_tokens": total_saved,
                "overall_savings_pct": pct,
                "recent_records": [
                    {
                        "tool": r.tool_name,
                        "operation": r.operation,
                        "saved": r.saved_tokens,
                        "pct": r.savings_pct,
                    }
                    for r in self._records[-10:]
                ],
            }
    
    def reset(self) -> None:
        """Reset all tracking data."""
        with self._lock:
            self._records.clear()
            self._total_original = 0
            self._total_optimized = 0
            self._call_count = 0
```

### 2. Configuration System

A simple config dataclass that controls optimization behavior:

```python
from dataclasses import dataclass

@dataclass
class TokenOptimizationConfig:
    """Configuration for token optimization behavior.
    
    All values have sensible defaults. Override per-project or per-call.
    """
    
    # Master switch
    enabled: bool = True
    
    # Filter levels per content type
    source_filter_level: str = "minimal"     # none | minimal | aggressive
    markdown_filter_level: str = "minimal"   # none | minimal
    
    # Token budgets (0 = unlimited)
    document_max_tokens: int = 4_000
    skill_max_tokens: int = 6_000
    workflow_max_tokens: int = 8_000
    source_file_max_tokens: int = 3_000
    snapshot_total_max_tokens: int = 50_000
    snapshot_per_file_max_tokens: int = 2_000
    task_pipeline_max_tokens: int = 12_000
    guidance_content_max_tokens: int = 4_000
    
    # Analytics
    track_savings: bool = True
    
    # Feature flags
    strip_comments: bool = True
    collapse_whitespace: bool = True
    deduplicate_lines: bool = True
    strip_html_comments: bool = True
    strip_badge_images: bool = True
    
    @classmethod
    def from_dict(cls, data: dict) -> "TokenOptimizationConfig":
        """Create config from a dictionary (e.g., from env vars or JSON)."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
    
    @classmethod
    def disabled(cls) -> "TokenOptimizationConfig":
        """Create a config with all optimization disabled."""
        return cls(enabled=False, track_savings=False)
    
    @classmethod  
    def aggressive(cls) -> "TokenOptimizationConfig":
        """Create a config with aggressive optimization."""
        return cls(
            source_filter_level="aggressive",
            document_max_tokens=2_000,
            skill_max_tokens=3_000,
            source_file_max_tokens=1_500,
            snapshot_total_max_tokens=25_000,
        )
```

### 3. Environment Variable Support

```python
import os

def load_config_from_env() -> TokenOptimizationConfig:
    """Load optimization config from environment variables.
    
    Environment variables (all optional):
        AGENT_GUIDANCE_TOKEN_OPT=0|1          - Enable/disable optimization
        AGENT_GUIDANCE_FILTER_LEVEL=none|minimal|aggressive
        AGENT_GUIDANCE_DOC_MAX_TOKENS=4000
        AGENT_GUIDANCE_TRACK_SAVINGS=0|1
    """
    config = {}
    
    if os.environ.get("AGENT_GUIDANCE_TOKEN_OPT") == "0":
        return TokenOptimizationConfig.disabled()
    
    env_mapping = {
        "AGENT_GUIDANCE_FILTER_LEVEL": "source_filter_level",
        "AGENT_GUIDANCE_DOC_MAX_TOKENS": ("document_max_tokens", int),
        "AGENT_GUIDANCE_SKILL_MAX_TOKENS": ("skill_max_tokens", int),
        "AGENT_GUIDANCE_TRACK_SAVINGS": ("track_savings", lambda v: v != "0"),
    }
    
    for env_key, config_spec in env_mapping.items():
        value = os.environ.get(env_key)
        if value is not None:
            if isinstance(config_spec, tuple):
                field_name, converter = config_spec
                config[field_name] = converter(value)
            else:
                config[config_spec] = value
    
    return TokenOptimizationConfig.from_dict(config)
```

### 4. Global State Management

Wire the config and tracker into the server lifecycle:

```python
# In server.py create_server():

_global_tracker = None
_global_config = None

def get_tracker() -> TokenTracker:
    global _global_tracker
    if _global_tracker is None:
        config = get_config()
        _global_tracker = TokenTracker(enabled=config.track_savings)
    return _global_tracker

def get_config() -> TokenOptimizationConfig:
    global _global_config
    if _global_config is None:
        _global_config = load_config_from_env()
    return _global_config
```

### 5. Token Stats MCP Tool (Optional)

Add a new MCP tool to expose token savings analytics:

```python
@mcp.tool()
def token_stats() -> dict[str, object]:
    """Return token optimization statistics for this session."""
    return get_tracker().summary()
```

## Implementation Steps

1. [ ] Create `src/agent_guidance_mcp/token_analytics.py` with `TokenTracker` and `TokenSavingsRecord`
2. [ ] Create `src/agent_guidance_mcp/token_config.py` with `TokenOptimizationConfig`
3. [ ] Implement `load_config_from_env()` for environment variable configuration
4. [ ] Add config/tracker initialization to `server.py:create_server()`
5. [ ] Wire `TokenTracker.record()` calls into pipeline integration points
6. [ ] Add optional `token_stats` MCP tool
7. [ ] Update `__main__.py` with `--no-optimize` CLI flag

## Files to Create/Modify

- `src/agent_guidance_mcp/token_analytics.py` — **[NEW]** Token savings tracker
- `src/agent_guidance_mcp/token_config.py` — **[NEW]** Configuration system
- `src/agent_guidance_mcp/server.py` — **[MODIFY]** Wire config/tracker + optional token_stats tool
- `src/agent_guidance_mcp/__main__.py` — **[MODIFY]** Add `--no-optimize` CLI flag
- `tests/test_token_analytics.py` — **[NEW]** Analytics tests
- `tests/test_token_config.py` — **[NEW]** Config tests

## Test Criteria

- [ ] `TokenTracker.record()` correctly tracks savings
- [ ] `TokenTracker.summary()` returns accurate aggregates
- [ ] `TokenTracker` is thread-safe (concurrent record calls)
- [ ] `TokenTracker` bounds memory at 1000 records
- [ ] `TokenOptimizationConfig.from_dict()` creates valid config
- [ ] `TokenOptimizationConfig.disabled()` turns off all optimization
- [ ] `TokenOptimizationConfig.aggressive()` uses lower budgets
- [ ] `load_config_from_env()` reads environment variables correctly
- [ ] `AGENT_GUIDANCE_TOKEN_OPT=0` disables all optimization
- [ ] Token stats tool returns valid JSON response

## Notes

- **No SQLite**: Unlike RTK, the MCP server uses in-memory tracking. MCP servers are typically short-lived (per-session), so persistent storage adds complexity without value.
- **Thread safety**: `TokenTracker` uses a threading lock because MCP servers may handle concurrent requests.
- **Memory bounded**: Records are capped at 1000 entries to prevent memory leaks in long-running sessions.

---
Next Phase: [Phase 06 — Testing & Verification](./phase-06-testing-verification.md)

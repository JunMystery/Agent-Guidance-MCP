"""MCP server package for Agent Guidance MCP."""

__version__ = "1.0.4"

from .catalog import CatalogEntry, StandardsCatalog, build_catalog, find_standards_root
from .content_compressor import Language
from .response_optimizer import TokenBudget, estimate_tokens, optimize_response
from .server import get_config, get_tracker, get_usage, reset_tracker, set_config
from .token_analytics import TokenSavingsRecord, TokenTracker
from .token_config import TokenOptimizationConfig
from .token_filter import FilterLevel
from .usage import UsageTracker

__all__ = [
    "__version__",
    "CatalogEntry",
    "FilterLevel",
    "Language",
    "StandardsCatalog",
    "TokenBudget",
    "TokenOptimizationConfig",
    "TokenSavingsRecord",
    "TokenTracker",
    "UsageTracker",
    "build_catalog",
    "estimate_tokens",
    "find_standards_root",
    "get_config",
    "get_tracker",
    "get_usage",
    "optimize_response",
    "reset_tracker",
    "set_config",
]

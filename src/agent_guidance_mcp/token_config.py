"""Token optimization configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class TokenOptimizationConfig:
    """Configuration for token optimization behavior."""

    enabled: bool = True

    source_filter_level: str = "minimal"
    markdown_filter_level: str = "minimal"

    document_max_tokens: int = 4_000
    skill_max_tokens: int = 6_000
    workflow_max_tokens: int = 8_000
    source_file_max_tokens: int = 3_000
    snapshot_total_max_tokens: int = 50_000
    snapshot_per_file_max_tokens: int = 2_000
    task_pipeline_max_tokens: int = 12_000
    guidance_content_max_tokens: int = 4_000

    track_savings: bool = True

    strip_comments: bool = True
    collapse_whitespace: bool = True
    deduplicate_lines: bool = True
    strip_html_comments: bool = True
    strip_badge_images: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "TokenOptimizationConfig":
        """Create config from a dictionary, ignoring unknown keys."""
        valid_fields = {field.name for field in fields(cls)}
        filtered = {key: value for key, value in data.items() if key in valid_fields}
        return cls(**filtered)

    @classmethod
    def disabled(cls) -> "TokenOptimizationConfig":
        """Create a config with optimization and tracking disabled."""
        return cls(enabled=False, track_savings=False)

    @classmethod
    def aggressive(cls) -> "TokenOptimizationConfig":
        """Create a config with aggressive optimization defaults."""
        return cls(
            source_filter_level="aggressive",
            document_max_tokens=2_000,
            skill_max_tokens=3_000,
            source_file_max_tokens=1_500,
            snapshot_total_max_tokens=25_000,
        )


def load_config_from_env() -> TokenOptimizationConfig:
    """Load token optimization configuration from environment variables."""
    if os.environ.get("AGENT_GUIDANCE_TOKEN_OPT") == "0":
        return TokenOptimizationConfig.disabled()

    config: dict[str, object] = {}
    env_mapping = {
        "AGENT_GUIDANCE_FILTER_LEVEL": ("source_filter_level", str),
        "AGENT_GUIDANCE_DOC_MAX_TOKENS": ("document_max_tokens", int),
        "AGENT_GUIDANCE_SKILL_MAX_TOKENS": ("skill_max_tokens", int),
        "AGENT_GUIDANCE_TRACK_SAVINGS": ("track_savings", _env_bool),
    }

    for env_key, (field_name, converter) in env_mapping.items():
        value = os.environ.get(env_key)
        if value is not None:
            config[field_name] = converter(value)

    return TokenOptimizationConfig.from_dict(config)


def _env_bool(value: str) -> bool:
    return value not in {"0", "false", "False", "no", "NO"}

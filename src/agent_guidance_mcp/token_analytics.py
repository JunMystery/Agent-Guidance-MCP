"""In-memory token savings analytics."""


import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class TokenSavingsRecord:
    """Record of token savings for one optimized response."""

    timestamp: str
    tool_name: str
    operation: str
    original_tokens: int
    optimized_tokens: int
    saved_tokens: int
    savings_pct: float
    backend: str = "mcp"  # "mcp" or "rtk"


class TokenTracker:
    """Thread-safe in-memory token savings tracker.

    Maintains a sliding window of recent records. When total records exceed
    `max_records`, the list is trimmed to keep only the most recent `trim_to`
    entries to bound memory usage.
    """

    def __init__(self, enabled: bool = True, max_records: int = 1000, trim_to: int = 500) -> None:
        self._enabled = enabled
        self._records: list[TokenSavingsRecord] = []
        self._lock = threading.Lock()
        self._total_original = 0
        self._total_optimized = 0
        self._call_count = 0
        self._max_records = max(1, max_records)
        self._trim_to = max(1, min(trim_to, self._max_records))

    def record(
        self,
        tool_name: str,
        operation: str,
        original_tokens: int,
        optimized_tokens: int,
    ) -> TokenSavingsRecord | None:
        """Record one token savings event."""
        if not self._enabled:
            return None

        saved = original_tokens - optimized_tokens
        pct = round((saved / max(1, original_tokens)) * 100, 1)
        record = TokenSavingsRecord(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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
            if len(self._records) > self._max_records:
                self._records = self._records[-self._trim_to:]

        return record

    def summary(self) -> dict[str, object]:
        """Return aggregate savings data."""
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
                        "tool": record.tool_name,
                        "operation": record.operation,
                        "saved": record.saved_tokens,
                        "pct": record.savings_pct,
                    }
                    for record in self._records[-10:]
                ],
            }

    def reset(self) -> None:
        """Reset all tracked savings data."""
        with self._lock:
            self._records.clear()
            self._total_original = 0
            self._total_optimized = 0
            self._call_count = 0

    def records(self) -> list[dict[str, object]]:
        """Return all retained records as dictionaries."""
        with self._lock:
            return [asdict(record) for record in self._records]

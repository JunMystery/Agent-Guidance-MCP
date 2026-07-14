"""Internal parallelism helpers for I/O-bound project scanning."""


import os
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def _default_workers() -> int:
    return min(8, os.cpu_count() or 4)


def parallel_map(
    fn: Callable[[T], R | None],
    items: Iterable[T],
    max_workers: int | None = None,
) -> list[R]:
    """Run fn over items in parallel, preserving input order.

    Items where fn returns None are filtered out.
    """
    if max_workers is None:
        max_workers = _default_workers()
    materialized = list(items)
    if not materialized:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(fn, materialized))
    return [r for r in results if r is not None]


def parallel_filter_map(
    fn: Callable[[T], tuple[bool, R | None]],
    items: Iterable[T],
    max_workers: int | None = None,
) -> list[R]:
    """Run fn over items in parallel, keeping only items where fn returns (True, value)."""
    if max_workers is None:
        max_workers = _default_workers()
    materialized = list(items)
    if not materialized:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(fn, materialized))
    return [value for keep, value in results if keep and value is not None]


def parallel_run(
    tasks: dict[str, Callable[[], R]],
    max_workers: int | None = None,
    timeout: float | None = None,
) -> dict[str, R]:
    """Run named callables concurrently, returning results keyed by name.

    Each value in tasks must be a zero-argument callable. Results preserve
    the keys from the input dict.

    timeout applies per-task, not total wall-clock. If any task exceeds
    the timeout, its result is stored as a TimeoutError in the output dict.
    """
    if max_workers is None:
        max_workers = _default_workers()
    if not tasks:
        return {}
    keys = list(tasks.keys())
    callables = [tasks[k] for k in keys]
    with ThreadPoolExecutor(max_workers=min(max_workers, len(keys))) as pool:
        futures = {pool.submit(fn): key for fn, key in zip(callables, keys)}
        results_map: dict[str, R | BaseException] = {}
        for future in futures:
            key = futures[future]
            try:
                results_map[key] = future.result(timeout=timeout)
            except TimeoutError as exc:
                results_map[key] = exc
            except Exception as exc:
                results_map[key] = exc
    return dict(zip(keys, [results_map[k] for k in keys]))

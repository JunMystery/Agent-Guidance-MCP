"""Context7 API client for retrieving live library documentation."""


import os
import json
import time
import re
import urllib.request
import urllib.parse
import functools
from typing import Any, Optional, Tuple

from .response_optimizer import TokenBudget, optimize_source_content
from .token_analytics import TokenTracker
from .token_config import TokenOptimizationConfig, load_config_from_env

API_BASE = "https://context7.com/api/v2"

CONTEXT7_ID_PATTERN = re.compile(r"^/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+")
def _get_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "agent-guidance-mcp/1.0"
    }
    api_key = os.environ.get("CONTEXT7_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers

def _url_open_with_retry(req: urllib.request.Request, timeout: int, retries: int = 2) -> bytes:
    """Execute HTTP request with exponential backoff retry."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(2 ** attempt)
    raise last_err or RuntimeError("Request failed after retries")

@functools.lru_cache(maxsize=128)
def _resolve_library_id(library_name: str, query: str, api_key: str | None) -> tuple[str | None, Any]:
    """Helper cached by library name and query to find libraryId."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "agent-guidance-mcp/1.0"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    search_params = urllib.parse.urlencode({
        "libraryName": library_name,
        "query": query
    })
    search_url = f"{API_BASE}/libs/search?{search_params}"
    
    req = urllib.request.Request(search_url, headers=headers)
    try:
        data_bytes = _url_open_with_retry(req, timeout=10)
        data = json.loads(data_bytes.decode("utf-8"))
    except Exception as e:
        return None, f"Failed to search library '{library_name}' in Context7: {e}"

    library_id = None
    if isinstance(data, list) and len(data) > 0:
        library_id = data[0].get("id")
    elif isinstance(data, dict):
        results = data.get("results") or data.get("libs") or []
        if results and len(results) > 0:
            library_id = results[0].get("id")

    return library_id, data

def normalize_identifier(
    identifier: str,
    query: str,
) -> Tuple[str, Optional[str]]:
    """Resolve a Context7 library identifier from user input.

    Returns (resolved_id, error_message). If `identifier` already matches the
    `/org/project` form it is returned unchanged with no error. Otherwise the
    identifier is treated as a library name and searched via Context7; the first
    match's id is returned, or an error message with a usage hint.
    """
    api_key = os.environ.get("CONTEXT7_API_KEY")
    if CONTEXT7_ID_PATTERN.match(identifier or ""):
        return identifier, None

    library_id, _search = _resolve_library_id(identifier, query, api_key)
    if library_id:
        return library_id, None

    return (
        identifier,
        (
            f"Could not resolve Context7 library ID for '{identifier}'. "
            f"Use the '/org/project' form (e.g. '/expressjs/express'), or run "
            f"guidance(operation='search', query='{identifier} docs') to discover it."
        ),
    )


def query_library_docs(
    library_name: str,
    query: str,
    config: TokenOptimizationConfig | None = None,
    tracker: TokenTracker | None = None,
) -> dict[str, Any]:
    """Retrieve documentation from Context7 for the given library and query."""
    config = config or load_config_from_env()
    headers = _get_headers()
    api_key = os.environ.get("CONTEXT7_API_KEY")

    resolved_id, resolve_error = normalize_identifier(library_name, query)
    if resolve_error:
        return {"error": resolve_error}

    # Step 1: Resolve libraryId
    library_id, search_result = _resolve_library_id(resolved_id, query, api_key)
    if not library_id:
        if isinstance(search_result, str):
            return {"error": search_result}
        return {
            "error": f"Could not resolve library ID for '{library_name}'.",
            "search_response": search_result
        }

    # Step 2: Get Context
    context_params = urllib.parse.urlencode({
        "libraryId": library_id,
        "query": query,
        "type": "json"
    })
    context_url = f"{API_BASE}/context?{context_params}"
    
    req = urllib.request.Request(context_url, headers=headers)
    try:
        res_bytes = _url_open_with_retry(req, timeout=15)
        res_data = json.loads(res_bytes.decode("utf-8"))
    except Exception as e:
        return {"error": f"Failed to fetch context for library ID '{library_id}': {e}"}

    # Step 3: Optimize Response
    content = ""
    if isinstance(res_data, dict):
        content = res_data.get("context") or res_data.get("content") or json.dumps(res_data)
    else:
        content = str(res_data)

    original_len = len(content)
    if config.enabled:
        optimized, _ = optimize_source_content(content, "markdown", config=config)
    else:
        optimized = content

    from .utils import record_savings
    record_savings(tracker, "guidance", "docs", content, optimized)

    return {
        "library_name": library_name,
        "library_id": library_id,
        "query": query,
        "documentation": optimized,
        "original_length": original_len,
        "optimized_length": len(optimized)
    }


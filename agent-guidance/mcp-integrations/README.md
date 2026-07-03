# Agent Guidance MCP: Custom Integrations & Maintenance Guide

This directory documents the custom integrations built into the `agent-guidance-mcp` server. If you are starting a new AI session, refer to this guide to understand how the codebase is structured and how to update or sync these integrations with upstream releases.

---

## 1. CodeGraph-like Semantic Indexing

To avoid relying on external CodeGraph daemons, we built local-first semantic indexing directly into this MCP.

### Architecture & Files
- **Database Backend:** [database.py](file:///e:/Github/Agent-Guidance-MCP/src/agent_guidance_mcp/database.py)
  - Uses SQLite stored at `.agent-context/codegraph.db`.
  - Tracks files, extracts AST symbols, and manages reference call edges (call graphs).
  - Uses triggers to sync symbols with a SQLite FTS5 virtual table (`symbols_fts`) for rapid full-text searching.
- **Incremental Indexer:** [indexer.py](file:///e:/Github/Agent-Guidance-MCP/src/agent_guidance_mcp/indexer.py)
  - Uses file size/mtime and MD5 content hashing to detect changes.
  - Re-indexes modified files using `tree-sitter` (AST extraction) with a regex-based graceful fallback in [symbols.py](file:///e:/Github/Agent-Guidance-MCP/src/agent_guidance_mcp/symbols.py).
  - Resolves callers/callees relationships dynamically based on reference matches.
- **Auto-run:** Creates the index automatically in `create_server` inside [server.py](file:///e:/Github/Agent-Guidance-MCP/src/agent_guidance_mcp/server.py).

### How to Maintain & Sync with Upstream CodeGraph
- **Database Schema Upgrades:** If the upstream CodeGraph database schema changes, update the schema in `_init_db()` inside `database.py`. The `schema_versions` table tracks schema migrations.
- **Grammar Updates:** AST node mappings and types are mapped in `_TS_KINDS` in [symbols.py](file:///e:/Github/Agent-Guidance-MCP/src/agent_guidance_mcp/symbols.py). Add or update language kinds there if new syntaxes roll out.

---

## 2. Context7 Documentation Search

We integrated Context7 live documentation lookup directly into the MCP `guidance` tool under the `"docs"` operation.

### Architecture & Files
- **API Client:** [docs.py](file:///e:/Github/Agent-Guidance-MCP/src/agent_guidance_mcp/docs.py)
  - Connects to Context7 GET endpoints: `/libs/search` (resolving library names to IDs) and `/context` (fetching docs context).
  - Authorization header format: `Bearer {CONTEXT7_API_KEY}`. Fallback to anonymous queries if the env var is missing.
- **Pipeline Dispatcher:** Registered in [pipelines.py](file:///e:/Github/Agent-Guidance-MCP/src/agent_guidance_mcp/pipelines.py) under `GUIDANCE_OPERATIONS = ("list", "get", "search", "recommend", "reason", "docs")`.

### How to Maintain & Sync with Upstream Context7
- **API Version Upgrades:** If Context7 updates their API base from `v2` (currently `https://context7.com/api/v2`), update the `API_BASE` constant in `docs.py`.
- **Response Layout Changes:** If Upstash changes the JSON structure returned from the `/context` or `/libs/search` endpoints, update the parsing logic in `query_library_docs` inside `docs.py`.

---

## 3. UI/UX Pro Max Skill

The UI/UX styling, palettes, landing patterns, and slide guidance are sourced from `ui-ux-pro-max-skill`.

### Architecture & Files
- **Search Logic:** [ui_ux.py](file:///e:/Github/Agent-Guidance-MCP/src/agent_guidance_mcp/ui_ux.py)
  - Loads CSV configuration from `skills/ui-ux-pro-max/data/`.
  - Performs BM25-based keyword ranking on styling metadata.
- **Skill Updater:** [update_ui_ux.py](file:///e:/Github/Agent-Guidance-MCP/scripts/update_ui_ux.py)
  - Downloads, extracts, and deploys the latest skill files directly from `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill`.

### How to Maintain & Sync with Upstream
- Run the python updater script to fetch the latest CSV database:
  ```bash
  python scripts/update_ui_ux.py
  ```

---

## 4. ECC Skills Library

The main engineering standards and developer skills collection is sourced from the official ECC repository.

### Architecture & Files
- **Skills Folder:** `skills/` (e.g. `skills/android-cli/`, `skills/spec-driven-development/`, etc.)
  - Stores standard workflow descriptions (`SKILL.md`) and companion scripts/resources.
- **Skills Updater:** [update_ecc.py](file:///e:/Github/Agent-Guidance-MCP/scripts/update_ecc.py)
  - Downloads the latest snapshot of all official skills from the `affaan-m/ECC` repository.

### How to Maintain & Sync with Upstream
- Run the python updater script to fetch new and updated skills:
  ```bash
  python scripts/update_ecc.py
  ```

---

## Maintenance Commands & Rebuild
- **Rebuild CodeGraph DB:** If you encounter database locks or corrupted indexes, delete the database file to trigger a clean re-index on next server startup:
  ```bash
  rm .agent-context/codegraph.db
  ```
- **Update UI/UX Skill:** Run the python script to download the latest skill CSV data from GitHub:
  ```bash
  python scripts/update_ui_ux.py
  ```
- **Update ECC Skills:** Run the python script to download the latest skills suite from GitHub:
  ```bash
  python scripts/update_ecc.py
  ```

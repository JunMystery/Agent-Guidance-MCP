# Integrated Repositories

Third-party repositories and projects integrated into the Agent Guidance MCP codebase.

---

## Bundled Content (shipped in the MCP server)

| Repository | Role | License |
|---|---|---|
| [ECC v2.0.0](https://github.com/affaan-m/ECC) | 168-skill catalog — backend, frontend, testing, security, DevOps, data, research, and 12+ language ecosystems. Synced via `scripts/update_ecc.py`. | MIT |
| [andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) | 6 core coding principles (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution, DRY, Code Organization). Bundled in `karpathy/`. | MIT |
| [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | UI/UX design data — palettes, fonts, landing patterns, charts, slide strategies. Synced via `scripts/update_ui_ux.py`. | MIT |
| [anthropics/skills](https://github.com/anthropics/skills) | 17+ skill catalog — creative & design, development & technical, enterprise & communication. Synced via `scripts/update_anthropic_skills.py`. | Apache 2.0 |
| [rtk — Rust Token Killer](https://github.com/rtk-ai/rtk) | CLI proxy that filters/compresses command output, saving 60–90% tokens for LLM context. Bundled as a subproject in `rtk/`. | Apache 2.0 |

## Python Dependencies

| Package | Role |
|---|---|
| [mcp](https://github.com/modelcontextprotocol/python-sdk) | MCP protocol SDK — FastMCP server, stdio transport, tool/resource/prompt registration |
| [pydantic](https://github.com/pydantic/pydantic) | Data validation and JSON serialization |
| [anyio](https://github.com/agronholm/anyio) | Async I/O backend (asyncio) |

## Runtime Integrations

| Integration | Role |
|---|---|
| [Context7](https://context7.com) | Live library/framework documentation lookup. Integrated via `guidance(operation="docs")`. |
| [HeadRoom](https://github.com/headroom) | Token compression MCP — shrinks tool outputs before they enter the LLM context. |
| [oh-my-openagent](https://github.com/oh-my-openagent) | OpenCode plugin — production-grade engineering skills and agent configurations. |

---

*For maintenance and sync procedures, see the [MCP Integrations Guide](../agent-guidance/mcp-integrations/README.md).*

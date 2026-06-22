---
name: data-scraper-agent
description: Build a fully automated AI-powered data collection agent for any public source — job boards, prices, news, GitHub, sports, anything. Scrapes on a schedule, enriches data with a free LLM (Gemini Flash), stores results in Notion/Sheets/Supabase, and learns from user feedback. Runs 100% free on GitHub Actions. Use when the user wants to monitor, collect, or track any public data automatically.
origin: community
---

# Data Scraper Agent

Build a production-ready, AI-powered data collection agent for any public data source.
Runs on a schedule, enriches results with a free LLM, stores to a database, and improves over time.

**Stack: Python · Gemini Flash (free) · GitHub Actions (free) · Notion / Sheets / Supabase**

## When to Activate

- User wants to scrape or monitor any public website or API
- User says "build a bot that checks...", "monitor X for me", "collect data from..."
- User wants to track jobs, prices, news, repos, sports scores, events, listings
- User asks how to automate data collection without paying for hosting
- User wants an agent that gets smarter over time based on their decisions

## Core Concepts

### The Three Layers

Every data scraper agent has three layers:

```
COLLECT → ENRICH → STORE
  │           │        │
Scraper    AI (LLM)  Database
runs on    scores/   Notion /
schedule   summarises Sheets /
           & classifies Supabase
```

### Free Stack

| Layer | Tool | Why |
|---|---|---|
| **Scraping** | `requests` + `BeautifulSoup` | No cost, covers 80% of public sites |
| **JS-rendered sites** | `playwright` (free) | When HTML scraping fails |
| **AI enrichment** | Gemini Flash via REST API | 500 req/day, 1M tokens/day — free |
| **Storage** | Notion API | Free tier, great UI for review |
| **Schedule** | GitHub Actions cron | Free for public repos |
| **Learning** | JSON feedback file in repo | Zero infra, persists in git |

### AI Model Fallback Chain

Build agents to auto-fallback across Gemini models on quota exhaustion:

```
gemini-2.0-flash-lite (30 RPM) →
gemini-2.0-flash (15 RPM) →
gemini-2.5-flash (10 RPM) →
gemini-flash-lite-latest (fallback)
```

### Batch API Calls for Efficiency

Never call the LLM once per item. Always batch:

```python
# BAD: 33 API calls for 33 items
for item in items:
    result = call_ai(item)  # 33 calls → hits rate limit

# GOOD: 7 API calls for 33 items (batch size 5)
for batch in chunks(items, size=5):
    results = call_ai(batch)  # 7 calls → stays within free tier
```

---

## Reference Material

The following reference files contain detailed code and reference material loaded on demand:

| File | Contents |
|---|---|
| [`reference/workflow.md`](reference/workflow.md) | Step-by-step agent build: understand goal, design architecture, build scraper, AI client, AI pipeline, feedback learning, storage, orchestration, GitHub Actions, config template |
| [`reference/patterns-and-reference.md`](reference/patterns-and-reference.md) | Common scraping patterns (REST, HTML, RSS, paginated, Playwright), anti-patterns, free tier limits, requirements template, quality checklist, real-world examples |

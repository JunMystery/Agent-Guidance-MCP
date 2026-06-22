## Common Scraping Patterns

### Pattern 1: REST API (easiest)
```python
resp = requests.get(url, params={"q": query}, headers=HEADERS, timeout=15)
items = resp.json().get("results", [])
```

### Pattern 2: HTML Scraping
```python
soup = BeautifulSoup(resp.text, "lxml")
for card in soup.select(".listing-card"):
    title = card.select_one("h2").get_text(strip=True)
    href = card.select_one("a")["href"]
```

### Pattern 3: RSS Feed
```python
import xml.etree.ElementTree as ET
root = ET.fromstring(resp.text)
for item in root.findall(".//item"):
    title = item.findtext("title", "")
    link = item.findtext("link", "")
    pub_date = item.findtext("pubDate", "")
```

### Pattern 4: Paginated API
```python
page = 1
while True:
    resp = requests.get(url, params={"page": page, "limit": 50}, timeout=15)
    data = resp.json()
    items = data.get("results", [])
    if not items:
        break
    for item in items:
        results.append(_normalise(item))
    if not data.get("has_more"):
        break
    page += 1
```

### Pattern 5: JS-Rendered Pages (Playwright)
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url)
    page.wait_for_selector(".listing")
    html = page.content()
    browser.close()

soup = BeautifulSoup(html, "lxml")
```

---

## Anti-Patterns to Avoid

| Anti-pattern | Problem | Fix |
|---|---|---|
| One LLM call per item | Hits rate limits instantly | Batch 5 items per call |
| Hardcoded keywords in code | Not reusable | Move all config to `config.yaml` |
| Scraping without rate limit | IP ban | Add `time.sleep(1)` between requests |
| Storing secrets in code | Security risk | Always use `.env` + GitHub Secrets |
| No deduplication | Duplicate rows pile up | Always check URL before pushing |
| Ignoring `robots.txt` | Legal/ethical risk | Respect crawl rules; use public APIs when available |
| JS-rendered sites with `requests` | Empty response | Use Playwright or look for the underlying API |
| `maxOutputTokens` too low | Truncated JSON, parse error | Use 2048+ for batch responses |

---

## Free Tier Limits Reference

| Service | Free Limit | Typical Usage |
|---|---|---|
| Gemini Flash Lite | 30 RPM, 1500 RPD | ~56 req/day at 3-hr intervals |
| Gemini 2.0 Flash | 15 RPM, 1500 RPD | Good fallback |
| Gemini 2.5 Flash | 10 RPM, 500 RPD | Use sparingly |
| GitHub Actions | Unlimited (public repos) | ~20 min/day |
| Notion API | Unlimited | ~200 writes/day |
| Supabase | 500MB DB, 2GB transfer | Fine for most agents |
| Google Sheets API | 300 req/min | Works for small agents |

---

## Requirements Template

```
requests==2.31.0
beautifulsoup4==4.12.3
lxml==5.1.0
python-dotenv==1.0.1
pyyaml==6.0.2
notion-client==2.2.1   # if using Notion
# playwright==1.40.0   # uncomment for JS-rendered sites
```

---

## Quality Checklist

Before marking the agent complete:

- [ ] `config.yaml` controls all user-facing settings — no hardcoded values
- [ ] `profile/context.md` holds user-specific context for AI matching
- [ ] Deduplication by URL before every storage push
- [ ] Gemini client has model fallback chain (4 models)
- [ ] Batch size ≤ 5 items per API call
- [ ] `maxOutputTokens` ≥ 2048
- [ ] `.env` is in `.gitignore`
- [ ] `.env.example` provided for onboarding
- [ ] `setup.py` creates DB schema on first run
- [ ] `enrich_existing.py` backfills AI scores on old rows
- [ ] GitHub Actions workflow commits `feedback.json` after each run
- [ ] README covers: setup in < 5 minutes, required secrets, customisation

---

## Real-World Examples

```
"Build me an agent that monitors Hacker News for AI startup funding news"
"Scrape product prices from 3 e-commerce sites and alert when they drop"
"Track new GitHub repos tagged with 'llm' or 'agents' — summarise each one"
"Collect Chief of Staff job listings from LinkedIn and Cutshort into Notion"
"Monitor a subreddit for posts mentioning my company — classify sentiment"
"Scrape new academic papers from arXiv on a topic I care about daily"
"Track sports fixture results and keep a running table in Google Sheets"
"Build a real estate listing watcher — alert on new properties under ₹1 Cr"
```

---

## Reference Implementation

A complete working agent built with this exact architecture would scrape 4+ sources,
batch Gemini calls, learn from Applied/Rejected decisions stored in Notion, and run
100% free on GitHub Actions. Follow Steps 1–9 above to build your own.

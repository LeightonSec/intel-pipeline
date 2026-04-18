# CLAUDE.md — Intel Pipeline

## What This Is
An automated intelligence pipeline that monitors security news, AI 
research, BSV/Bastion developments and CVE feeds. Filters by keywords, 
summarises with Claude API, and delivers structured reports to Obsidian 
twice daily. Built as part of the LeightonSec SOC Toolkit.

## SOC Toolkit Position
- **Layer:** Ingestion
- **Receives from:** External RSS feeds, CVE databases
- **Feeds into:** Analyst (Obsidian inbox), future Unified Dashboard
- **Gap it fills:** Automated threat intelligence and research ingestion

## Architecture
- `pipeline.py` — Main orchestrator, keyword filtering, report generation
- `fetcher.py` — RSS ingestion, domain whitelist, rate limiting
- `summariser.py` — Claude API summarisation, prompt injection hardened
- `deduplicator.py` — Cross-run deduplication, 1-day expiry window
- `scheduler.py` — Twice daily automation (07:00 and 19:00)
- `run.sh` — Shell wrapper for launchd auto-scheduler
- `logs/seen_urls.json` — Dedup cache (gitignored)
- `reports/` — Local report storage (gitignored)

## Current Status
✅ Complete and live — LeightonSec/intel-pipeline
✅ Four feed categories: security, ai_research, bsv_bastion, cve
✅ Domain whitelist security layer
✅ Rate limiting between requests
✅ Keyword filtering and deduplication (1-day window)
✅ Claude API summarisation with prompt injection protection
✅ Obsidian inbox delivery
✅ launchd auto-scheduler via run.sh wrapper
⚠️ arxiv AI research feed returning 0 items — needs investigation
🔄 v2 multi-agent LangGraph architecture — designed, not yet integrated

## Next Steps
- [ ] Fix arxiv feed returning 0 items
- [ ] Build v2 multi-agent pipeline (pipeline_v2.py) — LangGraph, 6 agents
- [ ] Add feedback loop — rate articles, pipeline learns from ratings
- [ ] Slack/email alert for critical HIGH severity items
- [ ] Integration with Unified Dashboard

## v2 Architecture (LangGraph — not yet built)
Six agents: FetcherAgent → FilterAgent → DeduplicatorAgent → 
EnricherAgent (severity scoring) → SummariserAgent → ReporterAgent
Conditional routing — skip summarisation if no new items

## Tech Stack
- Python, feedparser, requests, beautifulsoup4
- Anthropic Claude API (claude-haiku-4-5-20251001)
- LangGraph (installed, v2 not yet integrated)
- schedule, python-dotenv

## Security Rules
- API key in .env — never committed
- .env, logs/, reports/, venv/ all gitignored
- Domain whitelist — only approved sources fetched
- Rate limiting between all requests
- Claude system prompt hardened against RSS prompt injection
- Outbound only — nothing external reaches Obsidian

## Conventions
- All feed sources defined in RSS_FEEDS dict in fetcher.py
- Keywords defined in USER_KEYWORDS list in pipeline.py
- Obsidian path set in OBSIDIAN_PATH in pipeline.py
- Reports always named Intel-YYYY-MM-DD-AM/PM.md
- Never reduce dedup expiry below 1 day
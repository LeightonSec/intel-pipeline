# 🛡️ Intel Pipeline — Automated Intelligence System

A personal intelligence pipeline that automatically monitors security news, AI research, BSV/Bastion developments and custom topics — summarising and delivering structured briefings directly to Obsidian twice daily.

---

## What It Does

Staying on top of the threat landscape, AI developments and niche research areas is a full time job. This tool automates that process — fetching from trusted sources every 12 hours, filtering by relevance, summarising with Claude AI, and dropping a structured report into your Obsidian vault inbox before you start your day.

---

## Features

- **Automated scheduling** — runs at 07:00 and 19:00 daily
- **Multi-source ingestion** — security news, AI research papers, BSV/blockchain feeds
- **Keyword filtering** — only surfaces content relevant to your defined interests
- **Claude API summarisation** — each item summarised with: what happened, why it matters, action items
- **Prompt injection protection** — system prompt hardened against malicious RSS content
- **Domain whitelist** — only fetches from approved, trusted sources
- **Rate limiting** — respectful scraping, no hammering of external sites
- **Obsidian integration** — reports drop directly into your vault inbox as structured Markdown
- **Local backup** — all reports saved locally in `/reports`

---

## Report Structure

Each report is categorised and structured for fast consumption:

Each item includes a one sentence summary, why it matters, and action items where relevant.

---

## Security Design

- API key stored in `.env` — never committed to version control
- Reports excluded from GitHub via `.gitignore`
- Domain whitelist prevents fetching from untrusted sources
- Rate limiting between requests prevents abusive scraping
- Claude system prompt hardened against prompt injection from RSS content
- Outbound only — nothing external can reach your Obsidian vault

---

## Setup

**Requirements:** Python 3.x, Anthropic API key

```bash
# Clone the repo
git clone git@github.com:LeightonSec/intel-pipeline.git
cd intel-pipeline

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add your API key
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# Run once manually
python3 pipeline.py

# Run on schedule (07:00 and 19:00 daily)
python3 scheduler.py
```

---

## Configuration

Edit `pipeline.py` to customise:

- `USER_KEYWORDS` — add your own topics and interests
- `OBSIDIAN_PATH` — point to your vault inbox
- `RSS_FEEDS` in `fetcher.py` — add or remove sources
- Schedule times in `scheduler.py`

---

## Project Structure

intel-pipeline/
├── pipeline.py      # Main orchestrator
├── fetcher.py       # RSS ingestion, whitelist, rate limiting
├── summariser.py    # Claude API summarisation
├── scheduler.py     # Twice daily automation
├── requirements.txt
├── reports/         # Local report storage (gitignored)
└── .env             # API key (never committed)

---

## Roadmap

- [ ] Web dashboard to view reports in browser
- [ ] Slack/email alert for critical security items
- [ ] CVE feed integration
- [ ] GitHub trending repos monitoring
- [ ] Custom source addition via config file

---

## Author

**Leighton Wilson** — IT Deployment Engineer transitioning into Cybersecurity  
[LeightonSec GitHub](https://github.com/LeightonSec)

---

*Built as part of a hands-on cybersecurity portfolio. Part of the LeightonSec security toolkit.*
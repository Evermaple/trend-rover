---
title: trend-rover
app_file: trend_rover/dashboard/app.py
sdk: gradio
sdk_version: 6.14.0
---
<p align="center">
  <h1 align="center">Trend Rover</h1>
  <p align="center">
    Track brand keyword trends across YouTube and X (Twitter)
    <br />
    <a href="./README_CN.md">中文文档</a> · <a href="#quick-start">Quick Start</a> · <a href="#contributing">Contributing</a>
  </p>
</p>

---

**Trend Rover** scrapes YouTube and X in real time, collects engagement metrics (views, likes, comments, shares, bookmarks), detects brand logos in video thumbnails, and exports clean summary reports — all from a single CLI command.

Built for marketing teams who need to answer: *"How is our brand performing on social media this week?"*

## Features

- **Multi-platform search** — YouTube and X, unified keyword search with date ranges
- **Engagement tracking** — Views, likes, comments, shares, bookmarks per post
- **Logo detection** — Finds your brand logo in YouTube thumbnails via OpenCV or LLM (Claude / OpenAI)
- **YouTube filters** — Filter by video type (video / shorts / live), duration, sort order
- **Gradio dashboard** — 4-tab web UI: Search, Stats, Detail, Export
- **CSV export** — One-command summary reports, ready for spreadsheets
- **Claude Code skill** — Use `/trend-rover` in Claude Code for natural language queries
- **SQLite storage** — Local database with automatic deduplication

## Quick Start

### Install

```bash
# Requires Python 3.11+
pip install trend-rover
playwright install chromium
```

### Search

```bash
# Search YouTube and X for "Pokekara" in April 2026
trend-rover search "Pokekara" \
  --platform youtube x \
  --since 2026-04-01 \
  --until 2026-04-30

# YouTube only, shorts, sorted by views
trend-rover search "Pokekara" \
  --platform youtube \
  --since 2026-04-01 \
  --until 2026-04-30 \
  --type shorts \
  --sort-by views
```

### Logo detection

```bash
# Find videos containing your brand logo in thumbnails
trend-rover search "Pokekara" \
  --platform youtube \
  --since 2026-04-01 \
  --until 2026-04-30 \
  --logo ./brand-logo.png \
  --vision-engine opencv
```

### Stats & Export

```bash
# View aggregated stats
trend-rover stats "Pokekara" \
  --platform youtube x \
  --since 2026-04-01 \
  --until 2026-04-30

# Export summary CSV
trend-rover export "Pokekara" \
  --platform youtube x \
  --date 20260426 \
  --output ./report.csv
```

### Dashboard

```bash
trend-rover dashboard --port 7860
```

Opens a Gradio web UI at `http://localhost:7860` with four tabs:

| Tab | What it does |
|-----|-------------|
| **Search** | Search by keyword, platform, date range, filters, and logo |
| **Stats** | View aggregated engagement metrics |
| **Detail** | Browse individual posts with metadata |
| **Export** | Download summary CSV |

### Claude Code

If you have [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed:

```
/trend-rover
> Search YouTube for Pokekara videos from last month
```

## Architecture

```
trend_rover/
├── cli.py              # argparse entry point
├── orchestrator.py     # Search pipeline: scrape → detect → store
├── models.py           # Feed dataclass
├── config.py           # TOML config loader
├── scrapers/
│   ├── youtube.py      # Playwright + XHR intercept
│   ├── x.py            # Playwright + scroll + cookie auth
│   └── _utils.py       # UA rotation, retry, delay
├── vision/
│   ├── opencv.py       # Multi-scale template matching
│   └── llm.py          # Claude / OpenAI vision API
├── storage/
│   ├── db.py           # SQLite with upsert
│   └── export.py       # Transposed CSV export
├── dashboard/
│   └── app.py          # Gradio 4-tab UI
└── skill/
    └── trend-rover.md  # Claude Code skill
```

## Configuration

Create `trend_rover.toml` in your project root:

```toml
[scraper]
min_delay = 2.0
max_delay = 5.0
max_retries = 3

[vision]
engine = "opencv"        # "opencv" or "llm"
threshold = 0.8

[llm]
provider = "claude"      # "claude" or "openai"
api_key = "sk-..."
model = "claude-sonnet-4-6"

[x]
cookies_file = "./x_cookies.json"
```

## Development

```bash
git clone https://github.com/user/trend-rover.git
cd trend-rover
python -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium

# Run tests (62 tests)
pytest tests/ -v
```

## Contributing

We welcome contributions! Here are some ways to get involved:

- **Add a new platform** — Instagram, TikTok, Reddit, LinkedIn
- **Improve scrapers** — Better anti-detection, proxy support, rate limiting
- **Enhance logo detection** — YOLO/CLIP models, batch processing
- **Dashboard features** — Charts, trend visualization, comparison views
- **Internationalization** — More languages for UI and reports
- **Documentation** — Tutorials, examples, deployment guides

### How to contribute

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/add-instagram`)
3. Write tests first (we use TDD)
4. Make your changes
5. Run `pytest tests/ -v` to ensure all tests pass
6. Submit a PR

## License

MIT

## Star History

If this tool helps your marketing team, please give it a star! It helps others discover the project.

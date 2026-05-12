# Trend Rover Plan 6: Gradio Dashboard + Claude Code Skill

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Gradio Dashboard with four tabs (Search, Stats, Detail, Export), and write the Claude Code Skill definition file that lets users run trend-rover via natural language in Claude Code.

**Architecture:** Gradio `Blocks` layout with four `Tab` components. Each tab calls the same orchestrator functions as the CLI. The Skill file is a markdown document in `trend_rover/skill/trend-rover.md` that Claude Code loads as a `/trend-rover` skill.

**Tech Stack:** Python 3.11+, Gradio 4.x, pytest

**Prerequisites:** Plans 1–5 complete.

---

## File Map

| File | Responsibility |
|------|---------------|
| `trend_rover/dashboard/app.py` | Gradio UI — all four tabs |
| `trend_rover/skill/trend-rover.md` | Claude Code Skill definition |
| `tests/test_dashboard.py` | Smoke tests for dashboard helper functions |

---

### Task 1: Dashboard Helper Functions

Extract pure functions from the dashboard that can be tested without launching Gradio.

**Files:**
- Create: `trend_rover/dashboard/app.py` (helpers only, no UI yet)
- Create: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing tests**

`tests/test_dashboard.py`:
```python
import pytest
from datetime import date
from trend_rover.dashboard.app import (
    format_stats_for_display,
    validate_date_range,
    platforms_from_checkboxes,
)


def test_format_stats_for_display():
    platform_totals = {
        "youtube": {"count": 20, "views": 10000, "likes": 300, "comments": 50, "shares": 20, "bookmarks": 10},
        "x": {"count": 11, "views": 2000, "likes": 100, "comments": 10, "shares": 5, "bookmarks": 3},
    }
    rows = format_stats_for_display(platform_totals, platforms=["youtube", "x"])
    assert len(rows) > 0
    # first row should be count row
    assert rows[0][0] == "帖子数量"
    assert rows[0][1] == 20
    assert rows[0][2] == 11


def test_validate_date_range_valid():
    error = validate_date_range("2026-04-01", "2026-05-12")
    assert error is None


def test_validate_date_range_end_before_start():
    error = validate_date_range("2026-05-12", "2026-04-01")
    assert error is not None
    assert "end" in error.lower() or "after" in error.lower() or "before" in error.lower()


def test_validate_date_range_invalid_format():
    error = validate_date_range("not-a-date", "2026-05-12")
    assert error is not None


def test_platforms_from_checkboxes():
    result = platforms_from_checkboxes(["YouTube", "X"])
    assert result == ["youtube", "x"]


def test_platforms_from_checkboxes_single():
    result = platforms_from_checkboxes(["YouTube"])
    assert result == ["youtube"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_dashboard.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement helper functions**

`trend_rover/dashboard/app.py`:
```python
from datetime import date
from typing import Optional


_PLATFORM_DISPLAY_TO_KEY = {"YouTube": "youtube", "X": "x"}

_STAT_ROWS = [
    ("帖子数量", "count"),
    ("查看次数", "views"),
    ("点赞", "likes"),
    ("评论", "comments"),
    ("转发", "shares"),
    ("收藏", "bookmarks"),
]


def format_stats_for_display(
    platform_totals: dict,
    platforms: list[str],
) -> list[list]:
    rows = []
    for label, key in _STAT_ROWS:
        row = [label]
        for platform in platforms:
            row.append(platform_totals.get(platform, {}).get(key, 0))
        rows.append(row)
    return rows


def validate_date_range(since: str, until: str) -> Optional[str]:
    try:
        start = date.fromisoformat(since)
        end = date.fromisoformat(until)
    except (ValueError, TypeError):
        return "Invalid date format. Use YYYY-MM-DD."
    if end < start:
        return "End date must be after or equal to start date."
    return None


def platforms_from_checkboxes(selected: list[str]) -> list[str]:
    return [_PLATFORM_DISPLAY_TO_KEY[s] for s in selected if s in _PLATFORM_DISPLAY_TO_KEY]


def launch(port: int = 7860) -> None:
    import gradio as gr
    from datetime import datetime
    from trend_rover.orchestrator import run_search, run_stats, run_export, SearchResult

    today = datetime.now().strftime("%Y-%m-%d")
    month_ago = datetime.now().replace(day=1).strftime("%Y-%m-%d")

    with gr.Blocks(title="Trend Rover") as demo:
        gr.Markdown("# Trend Rover\nTrack brand keyword trends across YouTube and X")

        with gr.Tab("Search"):
            with gr.Row():
                search_keyword = gr.Textbox(label="Keyword", placeholder="e.g. Pokekara")
                search_platforms = gr.CheckboxGroup(["YouTube", "X"], value=["YouTube", "X"], label="Platforms")
            with gr.Row():
                search_since = gr.Textbox(label="Since (YYYY-MM-DD)", value=month_ago)
                search_until = gr.Textbox(label="Until (YYYY-MM-DD)", value=today)
            with gr.Accordion("YouTube Filters", open=False):
                yt_type = gr.Dropdown(["", "video", "shorts", "live"], label="Type", value="")
                yt_duration = gr.Dropdown(["", "short", "medium", "long"], label="Duration", value="")
                yt_sort = gr.Dropdown(["relevance", "upload_date", "views", "rating"], label="Sort By", value="relevance")
                yt_limit = gr.Slider(10, 500, value=50, step=10, label="Limit per platform")
            with gr.Accordion("Logo Detection (YouTube)", open=False):
                logo_file = gr.File(label="Upload Logo Image", file_types=["image"])
                vision_engine = gr.Radio(["opencv", "llm"], value="opencv", label="Detection Engine")
            search_btn = gr.Button("Search & Store", variant="primary")
            search_status = gr.Textbox(label="Status", interactive=False)
            search_result_table = gr.Dataframe(headers=["Platform", "Found"], label="Results")

            def do_search(keyword, platforms_sel, since, until, type_, duration, sort_by, limit, logo, engine):
                error = validate_date_range(since, until)
                if error:
                    return error, []
                if not keyword.strip():
                    return "Please enter a keyword.", []
                platforms = platforms_from_checkboxes(platforms_sel)
                logo_path = logo.name if logo else None
                try:
                    result: SearchResult = run_search(
                        keyword=keyword,
                        platforms=platforms,
                        start_date=date.fromisoformat(since),
                        end_date=date.fromisoformat(until),
                        logo_path=logo_path,
                        vision_engine=engine if logo_path else None,
                        limit=int(limit),
                        video_type=type_ or None,
                        duration=duration or None,
                        sort_by=sort_by if sort_by != "relevance" else None,
                    )
                    rows = [[p.upper(), c] for p, c in result.by_platform.items()]
                    return f"Done. {result.total} feeds stored.", rows
                except Exception as e:
                    return f"Error: {e}", []

            search_btn.click(
                do_search,
                inputs=[search_keyword, search_platforms, search_since, search_until,
                        yt_type, yt_duration, yt_sort, yt_limit, logo_file, vision_engine],
                outputs=[search_status, search_result_table],
            )

        with gr.Tab("Stats"):
            with gr.Row():
                stats_keyword = gr.Textbox(label="Keyword")
                stats_platforms = gr.CheckboxGroup(["YouTube", "X"], value=["YouTube", "X"], label="Platforms")
            with gr.Row():
                stats_since = gr.Textbox(label="Since (YYYY-MM-DD)", value=month_ago)
                stats_until = gr.Textbox(label="Until (YYYY-MM-DD)", value=today)
            stats_btn = gr.Button("Get Stats", variant="primary")
            stats_table = gr.Dataframe(label="Aggregated Stats")

            def do_stats(keyword, platforms_sel, since, until):
                error = validate_date_range(since, until)
                if error:
                    return [[error]]
                platforms = platforms_from_checkboxes(platforms_sel)
                result = run_stats(
                    keyword=keyword,
                    platforms=platforms,
                    start_date=date.fromisoformat(since) if since else None,
                    end_date=date.fromisoformat(until) if until else None,
                )
                headers = ["指标"] + [p.upper() for p in platforms]
                rows = format_stats_for_display(result.platform_totals, platforms)
                return gr.Dataframe(value=rows, headers=headers)

            stats_btn.click(do_stats, inputs=[stats_keyword, stats_platforms, stats_since, stats_until], outputs=[stats_table])

        with gr.Tab("Detail"):
            with gr.Row():
                detail_keyword = gr.Textbox(label="Keyword")
                detail_platform = gr.Dropdown(["youtube", "x"], label="Platform", value="youtube")
            detail_btn = gr.Button("Load Feeds")
            detail_table = gr.Dataframe(
                headers=["ID", "Title", "Author", "Published", "Views", "Likes", "Comments", "Shares", "Logo"],
                label="Feed List",
            )

            def do_detail(keyword, platform):
                from trend_rover.storage.db import Database
                db = Database()
                feeds = db.query(keyword=keyword, platform=platform)
                db.close()
                rows = [
                    [f.feed_id, f.title[:60], f.author, f.published_at.strftime("%Y-%m-%d"),
                     f.views, f.likes, f.comments, f.shares, "✓" if f.logo_matched else ""]
                    for f in feeds
                ]
                return rows

            detail_btn.click(do_detail, inputs=[detail_keyword, detail_platform], outputs=[detail_table])

        with gr.Tab("Export"):
            with gr.Row():
                export_keyword = gr.Textbox(label="Keyword")
                export_platforms = gr.CheckboxGroup(["YouTube", "X"], value=["YouTube", "X"], label="Platforms")
            export_date = gr.Textbox(label="Date (YYYYMMDD)", placeholder="20260426")
            export_btn = gr.Button("Export CSV", variant="primary")
            export_file = gr.File(label="Download CSV")

            def do_export(keyword, platforms_sel, date_str):
                import tempfile, os
                platforms = platforms_from_checkboxes(platforms_sel)
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8") as f:
                    path = f.name
                run_export(keyword=keyword, platforms=platforms, date_str=date_str, output_path=path)
                return path

            export_btn.click(do_export, inputs=[export_keyword, export_platforms, export_date], outputs=[export_file])

    demo.launch(server_port=port)
```

- [ ] **Step 4: Run dashboard helper tests**

```bash
pytest tests/test_dashboard.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add trend_rover/dashboard/app.py tests/test_dashboard.py
git commit -m "feat: Gradio dashboard with search, stats, detail, export tabs"
```

---

### Task 2: Claude Code Skill Definition

**Files:**
- Create: `trend_rover/skill/trend-rover.md`
- Create: `trend_rover/skill/__init__.py`

- [ ] **Step 1: Create skill directory and init**

```bash
mkdir -p trend_rover/skill
touch trend_rover/skill/__init__.py
```

- [ ] **Step 2: Write the Skill definition**

`trend_rover/skill/trend-rover.md`:
```markdown
---
name: trend-rover
description: Track brand keyword trends across YouTube and X (Twitter). Search for feeds, view engagement stats, detect logo appearances in thumbnails, and export summary reports.
---

# Trend Rover Skill

You help users track brand keyword trends across social media using the `trend-rover` CLI tool.

## What you can do

- Search YouTube and X for feeds containing a keyword in a date range
- Show aggregated stats (views, likes, comments, shares) per platform
- Export a summary CSV report
- Launch the web dashboard

## How to use this skill

When the user asks to search, track, or analyze a brand keyword on social media, translate their request into `trend-rover` CLI commands and run them.

**Always confirm these before running:**
1. The keyword to search for
2. The date range (since / until in YYYY-MM-DD format)
3. Which platforms (youtube, x, or both)

If any are missing, ask the user before proceeding.

## CLI Commands

### Search and store feeds
```bash
trend-rover search "KEYWORD" \
  --platform youtube x \
  --since YYYY-MM-DD \
  --until YYYY-MM-DD \
  [--type video|shorts|live] \
  [--duration short|medium|long] \
  [--sort-by relevance|upload_date|views|rating] \
  [--limit 50] \
  [--logo PATH_TO_LOGO] \
  [--vision-engine opencv|llm]
```

### View stats
```bash
trend-rover stats "KEYWORD" \
  --platform youtube x \
  --since YYYY-MM-DD \
  --until YYYY-MM-DD \
  --json
```

### Export summary CSV
```bash
trend-rover export "KEYWORD" \
  --platform youtube x \
  --date YYYYMMDD \
  --output ./report.csv
```

### Launch dashboard
```bash
trend-rover dashboard --port 7860
```

## After running commands

- For search: report how many feeds were found per platform
- For stats: present the data as a readable table with platform columns
- For export: confirm the file was saved and show the path
- Offer follow-up actions: "Want me to export the results?" or "Should I launch the dashboard?"

## Examples

**User:** "Search YouTube for Pokekara videos from last month"
→ Confirm keyword=Pokekara, since=first day of last month, until=last day of last month, platform=youtube
→ Run: `trend-rover search "Pokekara" --platform youtube --since 2026-04-01 --until 2026-04-30`

**User:** "Show me the stats for Pokekara across YouTube and X in April"
→ First run search if not already done, then:
→ Run: `trend-rover stats "Pokekara" --platform youtube x --since 2026-04-01 --until 2026-04-30 --json`
→ Display results as a formatted table

**User:** "Export the Pokekara report for April 26"
→ Run: `trend-rover export "Pokekara" --platform youtube x --date 20260426 --output ./pokekara-report.csv`
```

- [ ] **Step 3: Register skill in pyproject.toml for Claude Code discovery**

Add to `pyproject.toml` under `[project]`:
```toml
[project.entry-points."claude_code.skills"]
trend-rover = "trend_rover.skill"
```

And add the skill data file to package includes. Modify `pyproject.toml`:
```toml
[tool.hatch.build.targets.wheel]
include = [
    "trend_rover/**",
]
```

- [ ] **Step 4: Verify skill file is valid markdown**

```bash
python -c "
from pathlib import Path
content = Path('trend_rover/skill/trend-rover.md').read_text()
assert 'name: trend-rover' in content
assert 'trend-rover search' in content
print('Skill file OK, length:', len(content), 'chars')
"
```

Expected: prints length without error

- [ ] **Step 5: Commit**

```bash
git add trend_rover/skill/ pyproject.toml
git commit -m "feat: Claude Code skill definition for /trend-rover"
```

---

### Task 3: Final Full Verification

- [ ] **Step 1: Run complete test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass

- [ ] **Step 2: Verify CLI entry point works end-to-end**

```bash
python -m trend_rover.cli --help
python -m trend_rover.cli search --help
python -m trend_rover.cli dashboard --help
```

Expected: all print help without errors

- [ ] **Step 3: Verify package installs cleanly**

```bash
pip install -e . --quiet
trend-rover --help
```

Expected: `trend-rover` command available in PATH, help text printed

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: plan 6 complete — dashboard and Claude Code skill"
```

---

## Implementation Order Summary

Implement plans in this order — each plan's output is required by the next:

| Plan | Depends On | Output |
|------|-----------|--------|
| Plan 1: Scaffold + Storage | — | Feed, DB, CSV, Config |
| Plan 2: YouTube Scraper | Plan 1 | YouTubeScraper |
| Plan 3: X Scraper | Plan 1, Plan 2 (_utils) | XScraper |
| Plan 4: Vision | Plan 1 | OpenCVDetector, LLMDetector |
| Plan 5: CLI + Orchestrator | Plans 1–4 | CLI, run_search, run_stats, run_export |
| Plan 6: Dashboard + Skill | Plans 1–5 | Gradio UI, Claude Code Skill |
```

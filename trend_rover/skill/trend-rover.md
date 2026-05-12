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

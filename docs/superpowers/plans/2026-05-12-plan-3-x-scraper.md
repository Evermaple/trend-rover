# Trend Rover Plan 3: X (Twitter) Scraper

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the X (Twitter) scraper that searches by keyword + date range using `since:` / `until:` operators, simulates scroll to load results, extracts tweet engagement stats, and handles login via user-supplied cookies.

**Architecture:** `XScraper` extends `BaseScraper`. Playwright loads `x.com/search` with search operators in the query. Scroll simulation loads more tweets. Cookies are loaded from a JSON file (exported from browser). Text matching uses the same `_text_matches` helper as the YouTube scraper (no logo detection for X).

**Tech Stack:** Python 3.11+, Playwright (async), pytest

**Prerequisites:** Plan 1 complete (Feed, BaseScraper, Config), Plan 2 complete (_utils).

---

## File Map

| File | Responsibility |
|------|---------------|
| `trend_rover/scrapers/x.py` | `XScraper` — search + stats |
| `tests/test_x_scraper.py` | Unit tests with mocked DOM content |

---

### Task 1: X Scraper — Tweet Parsing

**Files:**
- Create: `trend_rover/scrapers/x.py`
- Create: `tests/test_x_scraper.py`

- [ ] **Step 1: Write failing tests for tweet parsing helpers**

`tests/test_x_scraper.py`:
```python
import pytest
from datetime import datetime, timezone
from trend_rover.scrapers.x import _parse_count, _parse_tweet_article, _build_search_url


def test_parse_count_plain():
    assert _parse_count("1,234") == 1234


def test_parse_count_k_suffix():
    assert _parse_count("4.5K") == 4500


def test_parse_count_m_suffix():
    assert _parse_count("1.2M") == 1200000


def test_parse_count_zero():
    assert _parse_count("0") == 0


def test_parse_count_empty():
    assert _parse_count("") == 0


def test_build_search_url_basic():
    from datetime import date
    url = _build_search_url("Pokekara", date(2026, 4, 1), date(2026, 4, 30))
    assert "Pokekara" in url
    assert "since%3A2026-04-01" in url or "since:2026-04-01" in url
    assert "until%3A2026-04-30" in url or "until:2026-04-30" in url


def test_parse_tweet_article_valid():
    # Simulate the data-testid attributes Playwright would extract
    scraped_at = datetime(2026, 5, 12, tzinfo=timezone.utc)
    tweet_data = {
        "tweet_id": "1234567890",
        "text": "Pokekara is amazing! Check it out",
        "author": "testuser",
        "views": "10.5K",
        "likes": "300",
        "replies": "50",
        "reposts": "20",
        "bookmarks": "10",
        "timestamp": "2026-04-26T12:00:00.000Z",
        "url": "https://x.com/testuser/status/1234567890",
    }
    feed = _parse_tweet_article(tweet_data, keyword="Pokekara", scraped_at=scraped_at)
    assert feed.platform == "x"
    assert feed.feed_id == "1234567890"
    assert feed.views == 10500
    assert feed.likes == 300
    assert feed.shares == 20
    assert feed.comments == 50
    assert feed.bookmarks == 10
    assert feed.author == "testuser"


def test_parse_tweet_article_missing_optional_fields():
    scraped_at = datetime(2026, 5, 12, tzinfo=timezone.utc)
    tweet_data = {
        "tweet_id": "9999",
        "text": "Pokekara post",
        "author": "user2",
        "views": "",
        "likes": "",
        "replies": "",
        "reposts": "",
        "bookmarks": "",
        "timestamp": "",
        "url": "https://x.com/user2/status/9999",
    }
    feed = _parse_tweet_article(tweet_data, keyword="Pokekara", scraped_at=scraped_at)
    assert feed.views == 0
    assert feed.likes == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_x_scraper.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement XScraper**

`trend_rover/scrapers/x.py`:
```python
import asyncio
import json
import re
from datetime import date, datetime, timezone
from typing import Optional
from urllib.parse import quote

from playwright.async_api import async_playwright

from trend_rover.models import Feed
from trend_rover.scrapers.base import BaseScraper
from trend_rover.scrapers._utils import random_delay, random_ua
from trend_rover.scrapers.youtube import _text_matches
from trend_rover.config import Config


def _parse_count(text: str) -> int:
    if not text:
        return 0
    text = text.strip().replace(",", "")
    m = re.match(r"([\d.]+)([KkMm]?)", text)
    if not m:
        return 0
    value = float(m.group(1))
    suffix = m.group(2).upper()
    if suffix == "K":
        return int(value * 1_000)
    if suffix == "M":
        return int(value * 1_000_000)
    return int(value)


def _build_search_url(keyword: str, start_date: date, end_date: date) -> str:
    query = f"{keyword} since:{start_date.isoformat()} until:{end_date.isoformat()}"
    return f"https://x.com/search?q={quote(query)}&src=typed_query&f=live"


def _parse_tweet_article(data: dict, keyword: str, scraped_at: datetime) -> Feed:
    timestamp_str = data.get("timestamp", "")
    try:
        published_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        published_at = scraped_at

    return Feed(
        platform="x",
        feed_id=data["tweet_id"],
        keyword=keyword,
        title=data.get("text", "")[:200],
        url=data.get("url", ""),
        author=data.get("author", ""),
        published_at=published_at,
        views=_parse_count(data.get("views", "")),
        likes=_parse_count(data.get("likes", "")),
        comments=_parse_count(data.get("replies", "")),
        shares=_parse_count(data.get("reposts", "")),
        bookmarks=_parse_count(data.get("bookmarks", "")),
        thumbnail_url="",
        logo_matched=False,
        scraped_at=scraped_at,
    )


_EXTRACT_TWEETS_JS = """
() => {
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    const results = [];
    for (const article of articles) {
        const linkEl = article.querySelector('a[href*="/status/"]');
        const href = linkEl ? linkEl.getAttribute('href') : '';
        const tweetId = href.split('/status/').pop()?.split('?')[0] || '';
        const textEl = article.querySelector('[data-testid="tweetText"]');
        const text = textEl ? textEl.innerText : '';
        const timeEl = article.querySelector('time');
        const timestamp = timeEl ? timeEl.getAttribute('datetime') : '';
        const authorEl = article.querySelector('[data-testid="User-Name"] a');
        const author = authorEl ? authorEl.getAttribute('href')?.replace('/', '') : '';

        const getCount = (testid) => {
            const el = article.querySelector(`[data-testid="${testid}"] span`);
            return el ? el.innerText : '0';
        };
        results.push({
            tweet_id: tweetId,
            text: text,
            author: author,
            timestamp: timestamp,
            url: tweetId ? `https://x.com${href}` : '',
            views: getCount('app-text-transition-container'),
            likes: getCount('like'),
            replies: getCount('reply'),
            reposts: getCount('retweet'),
            bookmarks: getCount('bookmark'),
        });
    }
    return results;
}
"""


class XScraper(BaseScraper):
    def __init__(self, config: Config = None):
        self._config = config or Config()

    def search(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        limit: int = 50,
        **filters,
    ) -> list[Feed]:
        return asyncio.run(self._search_async(keyword, start_date, end_date, limit))

    async def _search_async(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        limit: int,
    ) -> list[Feed]:
        url = _build_search_url(keyword, start_date, end_date)
        scraped_at = datetime.now(timezone.utc)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=random_ua())

            if self._config.x_cookies_file:
                try:
                    with open(self._config.x_cookies_file) as f:
                        cookies = json.load(f)
                    await context.add_cookies(cookies)
                except (FileNotFoundError, json.JSONDecodeError):
                    pass

            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)

            tweet_data_list = []
            scroll_attempts = 0
            max_scrolls = 10

            while len(tweet_data_list) < limit and scroll_attempts < max_scrolls:
                items = await page.evaluate(_EXTRACT_TWEETS_JS)
                tweet_data_list = items  # replace with latest full list
                if len(tweet_data_list) >= limit:
                    break
                await page.evaluate("window.scrollBy(0, window.innerHeight * 3)")
                await page.wait_for_timeout(2000)
                scroll_attempts += 1

            await browser.close()

        feeds: list[Feed] = []
        seen = set()
        for data in tweet_data_list[:limit]:
            tweet_id = data.get("tweet_id", "")
            if not tweet_id or tweet_id in seen:
                continue
            seen.add(tweet_id)

            if not _text_matches(data.get("text", ""), keyword):
                continue

            feed = _parse_tweet_article(data, keyword=keyword, scraped_at=scraped_at)
            feeds.append(feed)

        return feeds

    def get_stats(self, feed_id: str) -> Feed:
        return asyncio.run(self._get_stats_async(feed_id))

    async def _get_stats_async(self, feed_id: str) -> Feed:
        # For X, re-scrape search results for a specific tweet ID is impractical.
        # Instead, navigate to the tweet directly and extract stats.
        scraped_at = datetime.now(timezone.utc)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=random_ua())
            page = await context.new_page()
            await page.goto(f"https://x.com/i/status/{feed_id}", wait_until="networkidle", timeout=30000)
            items = await page.evaluate(_EXTRACT_TWEETS_JS)
            await browser.close()

        for item in items:
            if item.get("tweet_id") == feed_id:
                return _parse_tweet_article(item, keyword="", scraped_at=scraped_at)

        # fallback empty feed
        return Feed(
            platform="x",
            feed_id=feed_id,
            keyword="",
            title="",
            url=f"https://x.com/i/status/{feed_id}",
            author="",
            published_at=scraped_at,
            views=0, likes=0, comments=0, shares=0, bookmarks=0,
            thumbnail_url="",
            logo_matched=False,
            scraped_at=scraped_at,
        )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_x_scraper.py -v
```

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add trend_rover/scrapers/x.py tests/test_x_scraper.py
git commit -m "feat: X (Twitter) scraper with Playwright scroll and cookie auth"
```

---

### Task 2: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "chore: plan 3 complete — X scraper"
```

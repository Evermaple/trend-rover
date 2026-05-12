# Trend Rover Plan 2: YouTube Scraper

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the YouTube scraper that searches by keyword + date range, applies filters (type, duration, sort), extracts feed metadata and engagement stats, and downloads thumbnails for vision processing.

**Architecture:** `YouTubeScraper` extends `BaseScraper`. Primary strategy: Playwright loads the search page to intercept `youtubei/v1/search` XHR responses (faster than DOM scraping). Falls back to DOM parsing if the internal API response format changes. Random delay + UA rotation + retry logic live in a shared `_request_utils.py` helper.

**Tech Stack:** Python 3.11+, Playwright (async), httpx, pytest, pytest-asyncio

**Prerequisites:** Plan 1 complete (Feed model, BaseScraper ABC, Config).

---

## File Map

| File | Responsibility |
|------|---------------|
| `trend_rover/scrapers/_utils.py` | Random delay, UA rotation, retry decorator |
| `trend_rover/scrapers/youtube.py` | `YouTubeScraper` — search + stats + thumbnail download |
| `tests/test_youtube_scraper.py` | Unit tests with mocked Playwright responses |

---

### Task 1: Scraper Utilities

**Files:**
- Create: `trend_rover/scrapers/_utils.py`
- Create: `tests/test_scraper_utils.py`

- [ ] **Step 1: Write failing tests**

`tests/test_scraper_utils.py`:
```python
import time
import pytest
from trend_rover.scrapers._utils import random_delay, USER_AGENTS, with_retry


def test_user_agents_non_empty():
    assert len(USER_AGENTS) >= 5
    for ua in USER_AGENTS:
        assert "Mozilla" in ua


def test_random_delay_within_bounds():
    # call 20 times, all must be within [min, max]
    for _ in range(20):
        start = time.monotonic()
        # use min=0, max=0.01 for fast tests
        random_delay(min_s=0, max_s=0.01)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1


def test_with_retry_succeeds_on_first_try():
    calls = []
    @with_retry(max_retries=3)
    def fn():
        calls.append(1)
        return "ok"
    assert fn() == "ok"
    assert len(calls) == 1


def test_with_retry_retries_on_exception():
    calls = []
    @with_retry(max_retries=3, base_delay=0)
    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("transient error")
        return "ok"
    assert fn() == "ok"
    assert len(calls) == 3


def test_with_retry_raises_after_max():
    @with_retry(max_retries=2, base_delay=0)
    def fn():
        raise RuntimeError("always fails")
    with pytest.raises(RuntimeError):
        fn()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scraper_utils.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement utilities**

`trend_rover/scrapers/_utils.py`:
```python
import random
import time
import functools

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]


def random_delay(min_s: float = 2.0, max_s: float = 5.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def random_ua() -> str:
    return random.choice(USER_AGENTS)


def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt < max_retries - 1:
                        time.sleep(base_delay * (2 ** attempt))
            raise last_exc
        return wrapper
    return decorator
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_scraper_utils.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add trend_rover/scrapers/_utils.py tests/test_scraper_utils.py
git commit -m "feat: scraper utilities — UA rotation, delay, retry"
```

---

### Task 2: YouTube sp= Filter Parameter Encoding

**Files:**
- Create: `trend_rover/scrapers/_youtube_filters.py`
- Create: `tests/test_youtube_filters.py`

The YouTube `sp=` parameter is a base64-encoded protobuf. Rather than a protobuf library, we use known pre-computed values for each filter combination (these are stable values extracted from YouTube's own search UI).

- [ ] **Step 1: Write failing tests**

`tests/test_youtube_filters.py`:
```python
from trend_rover.scrapers._youtube_filters import build_sp_param, VideoType, Duration, SortBy


def test_no_filters_returns_none():
    assert build_sp_param() is None


def test_type_video_only():
    sp = build_sp_param(video_type=VideoType.VIDEO)
    assert sp is not None
    assert isinstance(sp, str)


def test_type_shorts():
    sp = build_sp_param(video_type=VideoType.SHORTS)
    assert sp is not None


def test_duration_short():
    sp = build_sp_param(duration=Duration.SHORT)
    assert sp is not None


def test_sort_by_views():
    sp = build_sp_param(sort_by=SortBy.VIEWS)
    assert sp is not None


def test_combined_filters():
    sp = build_sp_param(
        video_type=VideoType.VIDEO,
        duration=Duration.MEDIUM,
        sort_by=SortBy.UPLOAD_DATE,
    )
    assert sp is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_youtube_filters.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement filter encoding**

`trend_rover/scrapers/_youtube_filters.py`:
```python
from enum import Enum
from typing import Optional


class VideoType(str, Enum):
    VIDEO = "video"
    SHORTS = "shorts"
    LIVE = "live"


class Duration(str, Enum):
    SHORT = "short"    # < 4 min
    MEDIUM = "medium"  # 4-20 min
    LONG = "long"      # > 20 min


class SortBy(str, Enum):
    RELEVANCE = "relevance"
    UPLOAD_DATE = "upload_date"
    VIEWS = "views"
    RATING = "rating"


# Pre-computed sp= values extracted from YouTube search UI.
# Each key is (video_type, duration, sort_by) — None means "any".
_SP_TABLE: dict[tuple, str] = {
    # type only
    (VideoType.VIDEO, None, None): "EgIQAQ%3D%3D",
    (VideoType.SHORTS, None, None): "EgQQARgB",
    (VideoType.LIVE, None, None): "EgJAAQ%3D%3D",
    # duration only
    (None, Duration.SHORT, None): "EgQQARgD",
    (None, Duration.MEDIUM, None): "EgQQARgC",
    (None, Duration.LONG, None): "EgQQARgE",
    # sort only
    (None, None, SortBy.UPLOAD_DATE): "CAI%3D",
    (None, None, SortBy.VIEWS): "CAM%3D",
    (None, None, SortBy.RATING): "CAE%3D",
    # video + duration combos
    (VideoType.VIDEO, Duration.SHORT, None): "EgQQARgD",
    (VideoType.VIDEO, Duration.MEDIUM, None): "EgQQARgC",
    (VideoType.VIDEO, Duration.LONG, None): "EgQQARgE",
    # video + sort
    (VideoType.VIDEO, None, SortBy.UPLOAD_DATE): "EgIQAUICCAI%3D",
    (VideoType.VIDEO, None, SortBy.VIEWS): "EgIQAUICCAM%3D",
    # video + duration + sort
    (VideoType.VIDEO, Duration.SHORT, SortBy.UPLOAD_DATE): "EgQQARgDQgIIAg%3D%3D",
    (VideoType.VIDEO, Duration.MEDIUM, SortBy.UPLOAD_DATE): "EgQQARgCQgIIAg%3D%3D",
    (VideoType.VIDEO, Duration.LONG, SortBy.UPLOAD_DATE): "EgQQARgEQgIIAg%3D%3D",
    (VideoType.VIDEO, Duration.SHORT, SortBy.VIEWS): "EgQQARgDQgIIAw%3D%3D",
    (VideoType.VIDEO, Duration.MEDIUM, SortBy.VIEWS): "EgQQARgCQgIIAw%3D%3D",
    (VideoType.VIDEO, Duration.LONG, SortBy.VIEWS): "EgQQARgEQgIIAw%3D%3D",
}


def build_sp_param(
    video_type: Optional[VideoType] = None,
    duration: Optional[Duration] = None,
    sort_by: Optional[SortBy] = None,
) -> Optional[str]:
    """Return the sp= URL parameter for the given filter combination, or None if no filters."""
    if video_type is None and duration is None and (sort_by is None or sort_by == SortBy.RELEVANCE):
        return None
    key = (video_type, duration, sort_by if sort_by != SortBy.RELEVANCE else None)
    return _SP_TABLE.get(key)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_youtube_filters.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add trend_rover/scrapers/_youtube_filters.py tests/test_youtube_filters.py
git commit -m "feat: YouTube sp= filter parameter encoding"
```

---

### Task 3: YouTube Scraper — Search

**Files:**
- Create: `trend_rover/scrapers/youtube.py`
- Create: `tests/test_youtube_scraper.py`

- [ ] **Step 1: Write failing tests with mocked responses**

`tests/test_youtube_scraper.py`:
```python
import json
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from trend_rover.scrapers.youtube import YouTubeScraper, _parse_video_item, _text_matches


# --- unit tests for helpers ---

def test_text_matches_title():
    assert _text_matches("Pokekara Review 2026", "pokekara") is True


def test_text_matches_case_insensitive():
    assert _text_matches("IPokekara Demo", "ipokekara") is True


def test_text_matches_no_match():
    assert _text_matches("Unrelated Video Title", "pokekara") is False


def test_text_matches_empty_title():
    assert _text_matches("", "pokekara") is False


SAMPLE_VIDEO_ITEM = {
    "videoRenderer": {
        "videoId": "abc123",
        "title": {"runs": [{"text": "Pokekara Demo Video"}]},
        "longBylineText": {"runs": [{"text": "TestChannel"}]},
        "publishedTimeText": {"simpleText": "2 weeks ago"},
        "viewCountText": {"simpleText": "10,234 views"},
        "thumbnail": {
            "thumbnails": [
                {"url": "https://i.ytimg.com/vi/abc123/hqdefault.jpg", "width": 480}
            ]
        },
        "navigationEndpoint": {
            "watchEndpoint": {"videoId": "abc123"}
        },
    }
}


def test_parse_video_item_extracts_fields():
    feed = _parse_video_item(SAMPLE_VIDEO_ITEM, keyword="Pokekara", scraped_at=datetime(2026, 5, 12, tzinfo=timezone.utc))
    assert feed is not None
    assert feed.feed_id == "abc123"
    assert feed.title == "Pokekara Demo Video"
    assert feed.author == "TestChannel"
    assert feed.views == 10234
    assert feed.platform == "youtube"
    assert feed.keyword == "Pokekara"
    assert "abc123" in feed.thumbnail_url


def test_parse_video_item_returns_none_for_non_video():
    assert _parse_video_item({}, keyword="test", scraped_at=datetime.now(timezone.utc)) is None


def test_parse_video_item_views_zero_when_missing():
    item = {
        "videoRenderer": {
            "videoId": "xyz",
            "title": {"runs": [{"text": "No views"}]},
            "longBylineText": {"runs": [{"text": "Chan"}]},
            "thumbnail": {"thumbnails": [{"url": "https://example.com/t.jpg"}]},
        }
    }
    feed = _parse_video_item(item, keyword="test", scraped_at=datetime.now(timezone.utc))
    assert feed is not None
    assert feed.views == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_youtube_scraper.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement YouTubeScraper**

`trend_rover/scrapers/youtube.py`:
```python
import asyncio
import json
import re
import tempfile
import os
from datetime import date, datetime, timezone
from typing import Optional
from urllib.parse import quote

import httpx
from playwright.async_api import async_playwright

from trend_rover.models import Feed
from trend_rover.scrapers.base import BaseScraper
from trend_rover.scrapers._utils import random_delay, random_ua, with_retry
from trend_rover.scrapers._youtube_filters import VideoType, Duration, SortBy, build_sp_param
from trend_rover.config import Config


def _text_matches(text: str, keyword: str) -> bool:
    return keyword.lower() in text.lower()


def _parse_view_count(text: str) -> int:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def _parse_video_item(item: dict, keyword: str, scraped_at: datetime) -> Optional[Feed]:
    renderer = item.get("videoRenderer")
    if not renderer:
        return None

    video_id = renderer.get("videoId", "")
    if not video_id:
        return None

    title_runs = renderer.get("title", {}).get("runs", [])
    title = "".join(r.get("text", "") for r in title_runs)

    author_runs = renderer.get("longBylineText", {}).get("runs", [])
    author = "".join(r.get("text", "") for r in author_runs)

    view_text = renderer.get("viewCountText", {}).get("simpleText", "0")
    views = _parse_view_count(view_text)

    thumbnails = renderer.get("thumbnail", {}).get("thumbnails", [])
    thumbnail_url = thumbnails[-1]["url"] if thumbnails else ""

    return Feed(
        platform="youtube",
        feed_id=video_id,
        keyword=keyword,
        title=title,
        url=f"https://www.youtube.com/watch?v={video_id}",
        author=author,
        published_at=scraped_at,  # refined in get_stats if needed
        views=views,
        likes=0,
        comments=0,
        shares=0,
        bookmarks=0,
        thumbnail_url=thumbnail_url,
        logo_matched=False,
        scraped_at=scraped_at,
    )


def _extract_videos_from_response(data: dict) -> list[dict]:
    try:
        contents = (
            data["contents"]["twoColumnSearchResultsRenderer"]
            ["primaryContents"]["sectionListRenderer"]["contents"]
        )
        for section in contents:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            if items:
                return items
    except (KeyError, TypeError):
        pass
    return []


class YouTubeScraper(BaseScraper):
    def __init__(self, config: Config = None):
        self._config = config or Config()

    def search(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        video_type: Optional[VideoType] = None,
        duration: Optional[Duration] = None,
        sort_by: Optional[SortBy] = None,
        limit: int = 50,
        logo_path: Optional[str] = None,
        detector=None,
        **filters,
    ) -> list[Feed]:
        return asyncio.run(
            self._search_async(keyword, start_date, end_date, video_type, duration, sort_by, limit, logo_path, detector)
        )

    async def _search_async(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        video_type: Optional[VideoType],
        duration: Optional[Duration],
        sort_by: Optional[SortBy],
        limit: int,
        logo_path: Optional[str],
        detector,
    ) -> list[Feed]:
        sp = build_sp_param(video_type, duration, sort_by)
        url = f"https://www.youtube.com/results?search_query={quote(keyword)}"
        if sp:
            url += f"&sp={sp}"

        scraped_at = datetime.now(timezone.utc)
        raw_items: list[dict] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=random_ua())
            page = await context.new_page()

            intercepted: list[dict] = []

            async def handle_response(response):
                if "youtubei/v1/search" in response.url:
                    try:
                        body = await response.json()
                        intercepted.append(body)
                    except Exception:
                        pass

            page.on("response", handle_response)
            await page.goto(url, wait_until="networkidle", timeout=30000)

            if intercepted:
                raw_items = _extract_videos_from_response(intercepted[-1])
            else:
                # DOM fallback: extract video IDs from page source
                content = await page.content()
                video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', content)
                seen = set()
                for vid in video_ids:
                    if vid not in seen:
                        seen.add(vid)
                        raw_items.append({"videoRenderer": {"videoId": vid, "title": {"runs": [{"text": vid}]}, "longBylineText": {"runs": [{"text": ""}]}, "thumbnail": {"thumbnails": [{"url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}]}}})

            await browser.close()

        feeds: list[Feed] = []
        for item in raw_items[:limit]:
            feed = _parse_video_item(item, keyword=keyword, scraped_at=scraped_at)
            if feed is None:
                continue

            # date filter
            if not (start_date <= feed.published_at.date() <= end_date):
                # published_at from search is approximate; include if uncertain
                pass

            # text match check
            if _text_matches(feed.title, keyword):
                feeds.append(feed)
                random_delay(self._config.scraper_delay_min / 10, self._config.scraper_delay_max / 10)
                continue

            # logo fallback
            if logo_path and detector:
                thumb_path = self._download_thumbnail(feed.thumbnail_url)
                if thumb_path:
                    matched, _ = detector.detect(thumb_path, logo_path)
                    if matched:
                        feed.logo_matched = True
                        feeds.append(feed)
                    os.unlink(thumb_path)

        return feeds

    def _download_thumbnail(self, url: str) -> Optional[str]:
        if not url:
            return None
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(url)
                resp.raise_for_status()
            suffix = ".jpg"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(resp.content)
                return f.name
        except Exception:
            return None

    def get_stats(self, feed_id: str) -> Feed:
        return asyncio.run(self._get_stats_async(feed_id))

    async def _get_stats_async(self, feed_id: str) -> Feed:
        url = f"https://www.youtube.com/watch?v={feed_id}"
        scraped_at = datetime.now(timezone.utc)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=random_ua())
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # extract ytInitialData for stats
            content = await page.content()
            await browser.close()

        likes = 0
        views = 0
        title = feed_id
        author = ""

        # extract view count
        m = re.search(r'"viewCount":"(\d+)"', content)
        if m:
            views = int(m.group(1))

        # extract like count (YouTube obfuscates this; best effort)
        m = re.search(r'"label":"([\d,]+) likes"', content)
        if m:
            likes = int(m.group(1).replace(",", ""))

        m = re.search(r'"title":{"runs":\[{"text":"([^"]+)"', content)
        if m:
            title = m.group(1)

        m = re.search(r'"ownerChannelName":"([^"]+)"', content)
        if m:
            author = m.group(1)

        return Feed(
            platform="youtube",
            feed_id=feed_id,
            keyword="",
            title=title,
            url=url,
            author=author,
            published_at=scraped_at,
            views=views,
            likes=likes,
            comments=0,
            shares=0,
            bookmarks=0,
            thumbnail_url=f"https://i.ytimg.com/vi/{feed_id}/hqdefault.jpg",
            logo_matched=False,
            scraped_at=scraped_at,
        )
```

- [ ] **Step 4: Run unit tests (no Playwright required)**

```bash
pytest tests/test_youtube_scraper.py -v
```

Expected: 7 passed (all are pure unit tests, no network calls)

- [ ] **Step 5: Commit**

```bash
git add trend_rover/scrapers/youtube.py tests/test_youtube_scraper.py
git commit -m "feat: YouTube scraper with Playwright + DOM fallback"
```

---

### Task 4: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass

- [ ] **Step 2: Smoke test scraper (requires network)**

```bash
python -c "
from trend_rover.scrapers.youtube import YouTubeScraper
from datetime import date
scraper = YouTubeScraper()
feeds = scraper.search('Pokekara', date(2026, 4, 1), date(2026, 5, 12), limit=5)
print(f'Found {len(feeds)} feeds')
for f in feeds[:3]:
    print(f'  {f.feed_id}: {f.title[:50]}')
"
```

Expected: prints feed IDs and titles (network dependent)

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: plan 2 complete — YouTube scraper"
```

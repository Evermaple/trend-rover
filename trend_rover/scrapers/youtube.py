import asyncio
import calendar
import json
import random
import re
import tempfile
import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

import httpx
from playwright.async_api import async_playwright

from trend_rover.models import Feed
from trend_rover.scrapers.base import BaseScraper
from trend_rover.scrapers._utils import random_ua
from trend_rover.scrapers._youtube_filters import VideoType, Duration, SortBy, UploadDate, build_sp_param
from trend_rover.config import Config


def _text_matches(text: str, keyword: str) -> bool:
    return keyword.lower() in text.lower()


def _parse_relative_time(text: str, now: datetime) -> datetime:
    """Parse YouTube relative time string like '3 days ago' into a datetime.
    Subtracts N units from now to get the approximate publish date.
    """
    text = text.lower().strip()
    patterns = [
        (r"(\d+)\s+second", "seconds"),
        (r"(\d+)\s+minute", "minutes"),
        (r"(\d+)\s+hour", "hours"),
        (r"(\d+)\s+day", "days"),
        (r"(\d+)\s+week", "weeks"),
        (r"(\d+)\s+month", "months"),
        (r"(\d+)\s+year", "years"),
    ]
    for pattern, unit in patterns:
        m = re.search(pattern, text)
        if m:
            val = int(m.group(1))
            base = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if unit in ("seconds", "minutes", "hours"):
                return base
            if unit == "days":
                return base - timedelta(days=val)
            if unit == "weeks":
                return base - timedelta(weeks=val)
            if unit == "months":
                month = base.month - val
                year = base.year + (month - 1) // 12
                month = ((month - 1) % 12) + 1
                try:
                    return base.replace(year=year, month=month)
                except ValueError:
                    last_day = calendar.monthrange(year, month)[1]
                    return base.replace(year=year, month=month, day=last_day)
            if unit == "years":
                try:
                    return base.replace(year=base.year - val)
                except ValueError:
                    return base.replace(year=base.year - val, day=28)
    return now


def _pick_upload_date(start_date: date, end_date: date) -> Optional[UploadDate]:
    today = date.today()
    if start_date >= today:
        return UploadDate.TODAY
    week_start = today - timedelta(days=today.weekday())
    if start_date >= week_start:
        return UploadDate.WEEK
    if start_date.year == today.year and start_date.month == today.month:
        return UploadDate.MONTH
    if start_date.year == today.year:
        return UploadDate.YEAR
    return None


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

    published_text = renderer.get("publishedTimeText", {}).get("simpleText", "")
    published_at = _parse_relative_time(published_text, scraped_at) if published_text else scraped_at

    thumbnails = renderer.get("thumbnail", {}).get("thumbnails", [])
    thumbnail_url = thumbnails[-1]["url"] if thumbnails else ""

    return Feed(
        platform="youtube",
        feed_id=video_id,
        keyword=keyword,
        title=title,
        url=f"https://www.youtube.com/watch?v={video_id}",
        author=author,
        published_at=published_at,
        views=views,
        likes=0,
        comments=0,
        shares=0,
        bookmarks=0,
        thumbnail_url=thumbnail_url,
        logo_matched=False,
        scraped_at=scraped_at,
    )


def _extract_initial_data(data: dict) -> tuple[list[dict], Optional[str]]:
    """Extract video items and continuation token from ytInitialData / first-page XHR response.
    Returns (video_items, continuation_token).
    """
    try:
        contents = (
            data["contents"]["twoColumnSearchResultsRenderer"]
            ["primaryContents"]["sectionListRenderer"]["contents"]
        )
        video_items: list[dict] = []
        continuation_token: Optional[str] = None

        for section in contents:
            if "itemSectionRenderer" in section:
                for item in section["itemSectionRenderer"].get("contents", []):
                    if "videoRenderer" in item:
                        video_items.append(item)
            if "continuationItemRenderer" in section:
                continuation_token = (
                    section["continuationItemRenderer"]
                    .get("continuationEndpoint", {})
                    .get("continuationCommand", {})
                    .get("token")
                )

        return video_items, continuation_token
    except (KeyError, TypeError):
        pass
    return [], None


def _extract_continuation_page(data: dict) -> tuple[list[dict], Optional[str]]:
    """Extract video items and continuation token from a continuation API response.
    Returns (video_items, continuation_token).
    """
    try:
        for action in data.get("onResponseReceivedCommands", []):
            items = action.get("appendContinuationItemsAction", {}).get("continuationItems", [])
            if not items:
                continue
            video_items: list[dict] = []
            continuation_token = None
            for item in items:
                if "videoRenderer" in item:
                    video_items.append(item)
                elif "itemSectionRenderer" in item:
                    for sub in item["itemSectionRenderer"].get("contents", []):
                        if "videoRenderer" in sub:
                            video_items.append(sub)
                elif "continuationItemRenderer" in item:
                    token = (
                        item["continuationItemRenderer"]
                        .get("continuationEndpoint", {})
                        .get("continuationCommand", {})
                        .get("token")
                    )
                    if token:
                        continuation_token = token
            return video_items, continuation_token
    except (KeyError, TypeError):
        pass
    return [], None


def _parse_initial_data_from_html(content: str) -> tuple[list[dict], Optional[str]]:
    """Parse ytInitialData JSON from page HTML using brace-matching for reliability."""
    for pattern in [r"var ytInitialData\s*=\s*(\{)", r"ytInitialData\s*=\s*(\{)"]:
        m = re.search(pattern, content)
        if not m:
            continue
        start = m.start(1)
        depth = 0
        for i in range(start, len(content)):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(content[start:i + 1])
                        return _extract_initial_data(data)
                    except (json.JSONDecodeError, Exception):
                        pass
                    break
    return [], None


def _extract_api_key(content: str) -> str:
    m = re.search(r'"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"', content)
    return m.group(1) if m else "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"


def _extract_visitor_data(content: str) -> Optional[str]:
    m = re.search(r'"visitorData"\s*:\s*"([^"]+)"', content)
    return m.group(1) if m else None


def _extract_client_version(content: str) -> str:
    m = re.search(r'"INNERTUBE_CLIENT_VERSION"\s*:\s*"([^"]+)"', content)
    return m.group(1) if m else "2.20240101.00.00"


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
        upload_date = _pick_upload_date(start_date, end_date)
        sp = build_sp_param(video_type, duration, sort_by, upload_date)
        url = f"https://www.youtube.com/results?search_query={quote(keyword)}"
        if sp:
            url += f"&sp={sp}"

        scraped_at = datetime.now(timezone.utc)

        # Step 1: Load first page via browser to get cookies + page data
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(user_agent=random_ua(), locale="en-US")
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
            content = await page.content()
            cookies = await context.cookies()
            await browser.close()

        api_key = _extract_api_key(content)
        visitor_data = _extract_visitor_data(content)
        client_version = _extract_client_version(content)

        # Parse first page: prefer XHR intercept, fall back to HTML
        if intercepted:
            raw_items, continuation_token = _extract_initial_data(intercepted[-1])
        else:
            raw_items, continuation_token = _parse_initial_data_from_html(content)

        # Step 2: Paginate via youtubei API
        cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": random_ua(),
            "X-YouTube-Client-Name": "1",
            "X-YouTube-Client-Version": client_version,
            "Cookie": cookie_header,
        }
        if visitor_data:
            headers["X-Goog-Visitor-Id"] = visitor_data

        max_pages = 20
        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            page_num = 0
            while continuation_token and page_num < max_pages:
                page_num += 1
                await asyncio.sleep(random.uniform(
                    self._config.scraper_delay_min / 2,
                    self._config.scraper_delay_max / 2,
                ))
                payload = {
                    "context": {
                        "client": {
                            "clientName": "WEB",
                            "clientVersion": client_version,
                            **({"visitorData": visitor_data} if visitor_data else {}),
                        }
                    },
                    "continuation": continuation_token,
                }
                try:
                    resp = await client.post(
                        f"https://www.youtube.com/youtubei/v1/search?key={api_key}",
                        json=payload,
                    )
                    resp.raise_for_status()
                    page_items, continuation_token = _extract_continuation_page(resp.json())
                    if not page_items:
                        break
                    raw_items.extend(page_items)
                except Exception:
                    break

        # Step 3: Parse, deduplicate, filter by date
        feeds: list[Feed] = []
        seen_ids: set[str] = set()
        for item in raw_items:
            feed = _parse_video_item(item, keyword=keyword, scraped_at=scraped_at)
            if feed is None or feed.feed_id in seen_ids:
                continue
            seen_ids.add(feed.feed_id)

            if logo_path and detector and not _text_matches(feed.title, keyword):
                thumb_path = self._download_thumbnail(feed.thumbnail_url)
                if thumb_path:
                    matched, _ = detector.detect(thumb_path, logo_path)
                    if matched:
                        feed.logo_matched = True
                        feeds.append(feed)
                    os.unlink(thumb_path)
            else:
                feeds.append(feed)

        filtered = [f for f in feeds if start_date <= f.published_at.date() <= end_date]
        return filtered[:limit] if limit else filtered

    def _download_thumbnail(self, url: str) -> Optional[str]:
        if not url:
            return None
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(url)
                resp.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
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
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(user_agent=random_ua(), locale="en-US")
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            content = await page.content()
            await browser.close()

        likes = 0
        views = 0
        title = feed_id
        author = ""

        m = re.search(r'"viewCount":"(\d+)"', content)
        if m:
            views = int(m.group(1))

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

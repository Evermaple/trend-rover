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
        published_at=scraped_at,
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
                content = await page.content()
                video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', content)
                seen = set()
                for vid in video_ids:
                    if vid not in seen:
                        seen.add(vid)
                        raw_items.append({
                            "videoRenderer": {
                                "videoId": vid,
                                "title": {"runs": [{"text": vid}]},
                                "longBylineText": {"runs": [{"text": ""}]},
                                "thumbnail": {"thumbnails": [{"url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}]},
                            }
                        })

            await browser.close()

        feeds: list[Feed] = []
        for item in raw_items[:limit]:
            feed = _parse_video_item(item, keyword=keyword, scraped_at=scraped_at)
            if feed is None:
                continue

            if _text_matches(feed.title, keyword):
                feeds.append(feed)
                random_delay(self._config.scraper_delay_min / 10, self._config.scraper_delay_max / 10)
                continue

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

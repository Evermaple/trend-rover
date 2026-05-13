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
            context = await browser.new_context(user_agent=random_ua(), locale="en-US")

            if self._config.x_cookies_file:
                try:
                    with open(self._config.x_cookies_file) as f:
                        cookies = json.load(f)
                    await context.add_cookies(cookies)
                except (FileNotFoundError, json.JSONDecodeError):
                    pass

            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            try:
                await page.wait_for_selector(
                    'article[data-testid="tweet"]', timeout=15000,
                )
            except Exception:
                await browser.close()
                return []

            tweet_data_list = []
            scroll_attempts = 0
            max_scrolls = 20
            prev_count = 0
            stale_rounds = 0

            while scroll_attempts < max_scrolls:
                items = await page.evaluate(_EXTRACT_TWEETS_JS)
                seen_ids = {d.get("tweet_id") for d in tweet_data_list}
                for item in items:
                    if item.get("tweet_id") and item["tweet_id"] not in seen_ids:
                        tweet_data_list.append(item)
                        seen_ids.add(item["tweet_id"])

                if len(tweet_data_list) >= limit:
                    break

                if len(tweet_data_list) == prev_count:
                    stale_rounds += 1
                    if stale_rounds >= 3:
                        break
                else:
                    stale_rounds = 0
                prev_count = len(tweet_data_list)

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
        scraped_at = datetime.now(timezone.utc)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=random_ua(), locale="en-US")
            page = await context.new_page()
            await page.goto(f"https://x.com/i/status/{feed_id}", wait_until="domcontentloaded", timeout=60000)
            try:
                await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
            except Exception:
                pass
            items = await page.evaluate(_EXTRACT_TWEETS_JS)
            await browser.close()

        for item in items:
            if item.get("tweet_id") == feed_id:
                return _parse_tweet_article(item, keyword="", scraped_at=scraped_at)

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

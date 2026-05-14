from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Callable, Optional

from trend_rover.config import Config, load_config
from trend_rover.models import Feed
from trend_rover.storage.db import Database
from trend_rover.storage.export import export_csv


@dataclass
class SearchResult:
    total: int
    by_platform: dict[str, int]
    feeds: list[Feed] = field(default_factory=list)


def _default_scraper_factory(config: Config) -> dict[str, Callable]:
    def make_youtube():
        from trend_rover.scrapers.youtube import YouTubeScraper
        return YouTubeScraper(config)

    def make_x():
        from trend_rover.scrapers.x import XScraper
        return XScraper(config)

    return {"youtube": make_youtube, "x": make_x}


def run_search(
    keyword: str,
    platforms: list[str],
    start_date: date,
    end_date: date,
    scraper_factory: dict[str, Callable] = None,
    logo_path: Optional[str] = None,
    vision_engine: Optional[str] = None,
    vision_threshold: float = 0.8,
    limit: int = 50,
    db_path: Optional[str] = None,
    config: Config = None,
    **scraper_filters,
) -> SearchResult:
    if config is None:
        config = load_config()
    if vision_engine:
        config.vision_engine = vision_engine
        config.vision_threshold = vision_threshold

    detector = None
    if logo_path:
        from trend_rover.vision import get_detector
        detector = get_detector(config)

    if scraper_factory is None:
        scraper_factory = _default_scraper_factory(config)

    db = Database(db_path)
    all_feeds: list[Feed] = []
    by_platform: dict[str, int] = {}

    for platform in platforms:
        factory_fn = scraper_factory.get(platform)
        if not factory_fn:
            continue
        scraper = factory_fn()
        feeds = scraper.search(
            keyword=keyword,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            logo_path=logo_path,
            detector=detector,
            **scraper_filters,
        )
        for feed in feeds:
            db.upsert(feed)
        by_platform[platform] = len(feeds)
        all_feeds.extend(feeds)

    db.close()
    return SearchResult(total=len(all_feeds), by_platform=by_platform, feeds=all_feeds)


@dataclass
class DailyStats:
    date: str
    count: int
    views: int
    likes: int
    comments: int
    shares: int
    bookmarks: int


@dataclass
class StatsResult:
    keyword: str
    platform_totals: dict[str, dict]
    platform_daily: dict[str, list[DailyStats]] = field(default_factory=dict)


def run_stats(
    keyword: str,
    platforms: list[str],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db_path: Optional[str] = None,
) -> StatsResult:
    db = Database(db_path)
    platform_totals: dict[str, dict] = {}
    platform_daily: dict[str, list[DailyStats]] = {}

    for platform in platforms:
        feeds = db.query(
            keyword=keyword,
            platform=platform,
            start_date=start_date,
            end_date=end_date,
        )
        platform_totals[platform] = {
            "count": len(feeds),
            "views": sum(f.views for f in feeds),
            "likes": sum(f.likes for f in feeds),
            "comments": sum(f.comments for f in feeds),
            "shares": sum(f.shares for f in feeds),
            "bookmarks": sum(f.bookmarks for f in feeds),
        }

        # Aggregate by date
        daily: dict[str, dict] = {}
        for f in feeds:
            day = f.published_at.strftime("%Y-%m-%d")
            if day not in daily:
                daily[day] = {"count": 0, "views": 0, "likes": 0, "comments": 0, "shares": 0, "bookmarks": 0}
            daily[day]["count"] += 1
            daily[day]["views"] += f.views
            daily[day]["likes"] += f.likes
            daily[day]["comments"] += f.comments
            daily[day]["shares"] += f.shares
            daily[day]["bookmarks"] += f.bookmarks

        platform_daily[platform] = [
            DailyStats(date=d, **daily[d]) for d in sorted(daily)
        ]

    db.close()
    return StatsResult(keyword=keyword, platform_totals=platform_totals, platform_daily=platform_daily)


def run_export(
    keyword: str,
    platforms: list[str],
    date_str: str,
    output_path: str,
    db_path: Optional[str] = None,
) -> None:
    db = Database(db_path)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        export_csv(db, keyword=keyword, platforms=platforms, date_str=date_str, output=f)
    db.close()

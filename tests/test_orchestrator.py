from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from trend_rover.models import Feed
from trend_rover.orchestrator import run_search, SearchResult


def _make_feed(feed_id="v1", keyword="Pokekara", platform="youtube", logo_matched=False, title="Pokekara Video"):
    return Feed(
        platform=platform,
        feed_id=feed_id,
        keyword=keyword,
        title=title,
        url=f"https://youtube.com/watch?v={feed_id}",
        author="Chan",
        published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        views=1000,
        likes=50,
        comments=10,
        shares=5,
        bookmarks=2,
        thumbnail_url="https://example.com/thumb.jpg",
        logo_matched=logo_matched,
        scraped_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )


def test_run_search_stores_feeds(tmp_path):
    mock_scraper = MagicMock()
    mock_scraper.search.return_value = [_make_feed("v1"), _make_feed("v2")]

    db_path = str(tmp_path / "test.db")
    result = run_search(
        keyword="Pokekara",
        platforms=["youtube"],
        start_date=date(2026, 4, 1),
        end_date=date(2026, 5, 12),
        scraper_factory={"youtube": lambda: mock_scraper},
        db_path=db_path,
    )

    assert isinstance(result, SearchResult)
    assert result.total == 2
    assert result.by_platform["youtube"] == 2


def test_run_search_deduplicates_across_calls(tmp_path):
    mock_scraper = MagicMock()
    feed = _make_feed("v1")
    mock_scraper.search.return_value = [feed]

    db_path = str(tmp_path / "test.db")
    run_search(
        keyword="Pokekara",
        platforms=["youtube"],
        start_date=date(2026, 4, 1),
        end_date=date(2026, 5, 12),
        scraper_factory={"youtube": lambda: mock_scraper},
        db_path=db_path,
    )
    run_search(
        keyword="Pokekara",
        platforms=["youtube"],
        start_date=date(2026, 4, 1),
        end_date=date(2026, 5, 12),
        scraper_factory={"youtube": lambda: mock_scraper},
        db_path=db_path,
    )
    from trend_rover.storage.db import Database
    db = Database(db_path)
    feeds = db.query(keyword="Pokekara", platform="youtube")
    db.close()
    assert len(feeds) == 1


def test_run_search_multi_platform(tmp_path):
    yt_scraper = MagicMock()
    yt_scraper.search.return_value = [_make_feed("v1", platform="youtube")]
    x_scraper = MagicMock()
    x_scraper.search.return_value = [_make_feed("t1", platform="x")]

    db_path = str(tmp_path / "test.db")
    result = run_search(
        keyword="Pokekara",
        platforms=["youtube", "x"],
        start_date=date(2026, 4, 1),
        end_date=date(2026, 5, 12),
        scraper_factory={"youtube": lambda: yt_scraper, "x": lambda: x_scraper},
        db_path=db_path,
    )
    assert result.total == 2
    assert result.by_platform["youtube"] == 1
    assert result.by_platform["x"] == 1

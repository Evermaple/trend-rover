import tempfile
import os
from datetime import datetime, timezone, date

import pytest

from trend_rover.models import Feed
from trend_rover.storage.db import Database


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    d = Database(path)
    yield d
    d.close()
    os.unlink(path)


def _make_feed(feed_id="abc123", keyword="Pokekara", platform="youtube", logo_matched=False):
    return Feed(
        platform=platform,
        feed_id=feed_id,
        keyword=keyword,
        title=f"Title {feed_id}",
        url=f"https://youtube.com/watch?v={feed_id}",
        author="TestChannel",
        published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        views=10000,
        likes=300,
        comments=50,
        shares=20,
        bookmarks=10,
        thumbnail_url=f"https://i.ytimg.com/vi/{feed_id}/hqdefault.jpg",
        logo_matched=logo_matched,
        scraped_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )


def test_insert_and_query(db):
    feed = _make_feed()
    db.upsert(feed)
    results = db.query(keyword="Pokekara", platform="youtube")
    assert len(results) == 1
    assert results[0].feed_id == "abc123"
    assert results[0].views == 10000


def test_upsert_deduplicates(db):
    feed = _make_feed()
    db.upsert(feed)
    db.upsert(feed)  # same platform+feed_id
    results = db.query(keyword="Pokekara", platform="youtube")
    assert len(results) == 1


def test_query_filters_by_date(db):
    feed_apr = _make_feed(feed_id="apr")
    feed_apr.published_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    feed_may = _make_feed(feed_id="may")
    feed_may.published_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    db.upsert(feed_apr)
    db.upsert(feed_may)

    results = db.query(
        keyword="Pokekara",
        platform="youtube",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
    )
    assert len(results) == 1
    assert results[0].feed_id == "may"


def test_query_filters_by_platform(db):
    yt_feed = _make_feed(feed_id="yt1", platform="youtube")
    x_feed = _make_feed(feed_id="x1", platform="x")
    db.upsert(yt_feed)
    db.upsert(x_feed)

    results = db.query(keyword="Pokekara", platform="x")
    assert len(results) == 1
    assert results[0].feed_id == "x1"

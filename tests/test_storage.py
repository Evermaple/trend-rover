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


import csv
import io
from trend_rover.storage.export import export_csv


def test_csv_export_single_platform(db):
    feed = _make_feed(feed_id="v1", platform="youtube")
    feed.views = 10000
    feed.likes = 300
    feed.comments = 50
    feed.shares = 20
    feed.bookmarks = 10
    db.upsert(feed)

    buf = io.StringIO()
    export_csv(
        db,
        keyword="Pokekara",
        platforms=["youtube"],
        date_str="20260426",
        output=buf,
    )
    buf.seek(0)
    rows = list(csv.reader(buf))

    assert rows[0] == ["媒体平台", "YouTube"]
    assert rows[1] == ["日期", "20260426"]
    assert rows[2] == ["关键词", "Pokekara"]
    assert rows[3][0] == "视频/帖子数量"
    assert int(rows[3][1]) == 1
    assert rows[4][0] == "查看次数"
    assert int(rows[4][1]) == 10000
    assert rows[5][0] == "互动次数（转发，评论，点赞）"
    assert int(rows[5][1]) == 370  # 20+50+300


def test_csv_export_two_platforms(db):
    yt = _make_feed(feed_id="v1", platform="youtube")
    yt.views = 10000
    yt.likes = 300
    yt.comments = 50
    yt.shares = 20
    yt.bookmarks = 10
    x_feed = _make_feed(feed_id="t1", platform="x")
    x_feed.views = 2000
    x_feed.likes = 100
    x_feed.comments = 10
    x_feed.shares = 5
    x_feed.bookmarks = 3
    db.upsert(yt)
    db.upsert(x_feed)

    buf = io.StringIO()
    export_csv(
        db,
        keyword="Pokekara",
        platforms=["youtube", "x"],
        date_str="20260426",
        output=buf,
    )
    buf.seek(0)
    rows = list(csv.reader(buf))

    assert rows[0] == ["媒体平台", "YouTube", "X"]
    assert rows[3][0] == "视频/帖子数量"
    assert int(rows[3][1]) == 1
    assert int(rows[3][2]) == 1

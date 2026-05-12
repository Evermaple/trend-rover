from datetime import datetime, timezone
from trend_rover.models import Feed


def test_feed_defaults():
    feed = Feed(
        platform="youtube",
        feed_id="abc123",
        keyword="Pokekara",
        title="Pokekara Review",
        url="https://youtube.com/watch?v=abc123",
        author="TestChannel",
        published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        views=10000,
        likes=300,
        comments=50,
        shares=20,
        bookmarks=10,
        thumbnail_url="https://i.ytimg.com/vi/abc123/hqdefault.jpg",
        logo_matched=False,
        scraped_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )
    assert feed.platform == "youtube"
    assert feed.logo_matched is False
    assert feed.thumbnail_url == "https://i.ytimg.com/vi/abc123/hqdefault.jpg"


def test_feed_logo_matched():
    feed = Feed(
        platform="youtube",
        feed_id="xyz789",
        keyword="Pokekara",
        title="No keyword in title",
        url="https://youtube.com/watch?v=xyz789",
        author="TestChannel",
        published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        views=5000,
        likes=100,
        comments=10,
        shares=5,
        bookmarks=2,
        thumbnail_url="https://i.ytimg.com/vi/xyz789/hqdefault.jpg",
        logo_matched=True,
        scraped_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )
    assert feed.logo_matched is True

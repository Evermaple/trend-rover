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

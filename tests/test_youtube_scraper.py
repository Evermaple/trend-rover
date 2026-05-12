from datetime import datetime, timezone
from trend_rover.scrapers.youtube import YouTubeScraper, _parse_video_item, _text_matches


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

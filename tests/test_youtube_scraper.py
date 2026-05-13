from datetime import date, datetime, timedelta, timezone
from trend_rover.scrapers.youtube import (
    YouTubeScraper, _parse_video_item, _text_matches,
    _parse_relative_time, _pick_upload_date,
)
from trend_rover.scrapers._youtube_filters import UploadDate


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
    scraped_at = datetime(2026, 5, 12, tzinfo=timezone.utc)
    feed = _parse_video_item(SAMPLE_VIDEO_ITEM, keyword="Pokekara", scraped_at=scraped_at)
    assert feed is not None
    assert feed.feed_id == "abc123"
    assert feed.title == "Pokekara Demo Video"
    assert feed.author == "TestChannel"
    assert feed.views == 10234
    assert feed.platform == "youtube"
    assert feed.keyword == "Pokekara"
    assert "abc123" in feed.thumbnail_url
    assert feed.published_at.date() == date(2026, 4, 28)


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


def test_parse_relative_time_days():
    now = datetime(2026, 5, 12, tzinfo=timezone.utc)
    result = _parse_relative_time("3 days ago", now)
    assert result.date() == date(2026, 5, 9)


def test_parse_relative_time_weeks():
    now = datetime(2026, 5, 12, tzinfo=timezone.utc)
    result = _parse_relative_time("2 weeks ago", now)
    assert result.date() == date(2026, 4, 28)


def test_parse_relative_time_hours():
    now = datetime(2026, 5, 12, 15, 0, tzinfo=timezone.utc)
    result = _parse_relative_time("5 hours ago", now)
    assert result.date() == date(2026, 5, 12)


def test_parse_relative_time_months():
    now = datetime(2026, 5, 12, tzinfo=timezone.utc)
    result = _parse_relative_time("2 months ago", now)
    assert result.date() == date(2026, 3, 12)


def test_parse_relative_time_streamed():
    now = datetime(2026, 5, 12, tzinfo=timezone.utc)
    result = _parse_relative_time("Streamed 1 day ago", now)
    assert result.date() == date(2026, 5, 11)


def test_parse_relative_time_unknown_returns_now():
    now = datetime(2026, 5, 12, tzinfo=timezone.utc)
    result = _parse_relative_time("just now", now)
    assert result == now


def test_pick_upload_date_today():
    today = date.today()
    assert _pick_upload_date(today, today) == UploadDate.TODAY


def test_pick_upload_date_this_week():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    if week_start == today:
        result = _pick_upload_date(today, today)
        assert result == UploadDate.TODAY
    else:
        result = _pick_upload_date(week_start, today)
        assert result == UploadDate.WEEK


def test_pick_upload_date_this_month():
    today = date.today()
    first_of_month = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())
    if first_of_month < week_start:
        result = _pick_upload_date(first_of_month, today)
        assert result == UploadDate.MONTH


def test_pick_upload_date_this_year():
    today = date.today()
    jan_first = date(today.year, 1, 1)
    result = _pick_upload_date(jan_first, today)
    assert result in (UploadDate.YEAR, UploadDate.MONTH, UploadDate.WEEK, UploadDate.TODAY)


def test_pick_upload_date_old_returns_none():
    result = _pick_upload_date(date(2020, 1, 1), date(2020, 12, 31))
    assert result is None

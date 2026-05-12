import pytest
from datetime import date
from trend_rover.dashboard.app import (
    format_stats_for_display,
    validate_date_range,
    platforms_from_checkboxes,
)


def test_format_stats_for_display():
    platform_totals = {
        "youtube": {"count": 20, "views": 10000, "likes": 300, "comments": 50, "shares": 20, "bookmarks": 10},
        "x": {"count": 11, "views": 2000, "likes": 100, "comments": 10, "shares": 5, "bookmarks": 3},
    }
    rows = format_stats_for_display(platform_totals, platforms=["youtube", "x"])
    assert len(rows) > 0
    # first row should be count row
    assert rows[0][0] == "帖子数量"
    assert rows[0][1] == 20
    assert rows[0][2] == 11


def test_validate_date_range_valid():
    error = validate_date_range("2026-04-01", "2026-05-12")
    assert error is None


def test_validate_date_range_end_before_start():
    error = validate_date_range("2026-05-12", "2026-04-01")
    assert error is not None
    assert "end" in error.lower() or "after" in error.lower() or "before" in error.lower()


def test_validate_date_range_invalid_format():
    error = validate_date_range("not-a-date", "2026-05-12")
    assert error is not None


def test_platforms_from_checkboxes():
    result = platforms_from_checkboxes(["YouTube", "X"])
    assert result == ["youtube", "x"]


def test_platforms_from_checkboxes_single():
    result = platforms_from_checkboxes(["YouTube"])
    assert result == ["youtube"]

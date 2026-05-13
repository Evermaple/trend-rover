from trend_rover.scrapers._youtube_filters import (
    build_sp_param, VideoType, Duration, SortBy, UploadDate,
)


def test_no_filters_returns_none():
    assert build_sp_param() is None


def test_relevance_returns_none():
    assert build_sp_param(sort_by=SortBy.RELEVANCE) is None


def test_type_video_only():
    sp = build_sp_param(video_type=VideoType.VIDEO)
    assert sp == "EgIQAQ=="


def test_type_shorts():
    sp = build_sp_param(video_type=VideoType.SHORTS)
    assert sp == "EgIQCQ=="


def test_type_live():
    sp = build_sp_param(video_type=VideoType.LIVE)
    assert sp == "EgJAAQ=="


def test_duration_short():
    sp = build_sp_param(duration=Duration.SHORT)
    assert sp is not None


def test_sort_by_views():
    sp = build_sp_param(sort_by=SortBy.VIEWS)
    assert sp == "CAM="


def test_sort_by_upload_date():
    sp = build_sp_param(sort_by=SortBy.UPLOAD_DATE)
    assert sp == "CAI="


def test_combined_filters():
    sp = build_sp_param(
        video_type=VideoType.VIDEO,
        duration=Duration.MEDIUM,
        sort_by=SortBy.UPLOAD_DATE,
    )
    assert sp is not None


def test_upload_date_today_video():
    sp = build_sp_param(upload_date=UploadDate.TODAY, video_type=VideoType.VIDEO)
    assert sp == "EgQIAhAB"


def test_upload_date_week_video():
    sp = build_sp_param(upload_date=UploadDate.WEEK, video_type=VideoType.VIDEO)
    assert sp == "EgQIAxAB"


def test_upload_date_week_shorts():
    sp = build_sp_param(upload_date=UploadDate.WEEK, video_type=VideoType.SHORTS)
    assert sp == "EgQIAxAJ"


def test_upload_date_month_only():
    sp = build_sp_param(upload_date=UploadDate.MONTH)
    assert sp == "EgIIBA=="


def test_upload_date_year_only():
    sp = build_sp_param(upload_date=UploadDate.YEAR)
    assert sp == "EgIIBQ=="

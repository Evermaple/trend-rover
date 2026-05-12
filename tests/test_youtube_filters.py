from trend_rover.scrapers._youtube_filters import build_sp_param, VideoType, Duration, SortBy


def test_no_filters_returns_none():
    assert build_sp_param() is None


def test_type_video_only():
    sp = build_sp_param(video_type=VideoType.VIDEO)
    assert sp is not None
    assert isinstance(sp, str)


def test_type_shorts():
    sp = build_sp_param(video_type=VideoType.SHORTS)
    assert sp is not None


def test_duration_short():
    sp = build_sp_param(duration=Duration.SHORT)
    assert sp is not None


def test_sort_by_views():
    sp = build_sp_param(sort_by=SortBy.VIEWS)
    assert sp is not None


def test_combined_filters():
    sp = build_sp_param(
        video_type=VideoType.VIDEO,
        duration=Duration.MEDIUM,
        sort_by=SortBy.UPLOAD_DATE,
    )
    assert sp is not None

from enum import Enum
from typing import Optional


class VideoType(str, Enum):
    VIDEO = "video"
    SHORTS = "shorts"
    LIVE = "live"


class Duration(str, Enum):
    SHORT = "short"    # < 4 min
    MEDIUM = "medium"  # 4-20 min
    LONG = "long"      # > 20 min


class SortBy(str, Enum):
    RELEVANCE = "relevance"
    UPLOAD_DATE = "upload_date"
    VIEWS = "views"
    RATING = "rating"


# Pre-computed sp= values extracted from YouTube search UI.
# Each key is (video_type, duration, sort_by) — None means "any".
_SP_TABLE: dict[tuple, str] = {
    # type only
    (VideoType.VIDEO, None, None): "EgIQAQ%3D%3D",
    (VideoType.SHORTS, None, None): "EgQQARgB",
    (VideoType.LIVE, None, None): "EgJAAQ%3D%3D",
    # duration only
    (None, Duration.SHORT, None): "EgQQARgD",
    (None, Duration.MEDIUM, None): "EgQQARgC",
    (None, Duration.LONG, None): "EgQQARgE",
    # sort only
    (None, None, SortBy.UPLOAD_DATE): "CAI%3D",
    (None, None, SortBy.VIEWS): "CAM%3D",
    (None, None, SortBy.RATING): "CAE%3D",
    # video + duration combos
    (VideoType.VIDEO, Duration.SHORT, None): "EgQQARgD",
    (VideoType.VIDEO, Duration.MEDIUM, None): "EgQQARgC",
    (VideoType.VIDEO, Duration.LONG, None): "EgQQARgE",
    # video + sort
    (VideoType.VIDEO, None, SortBy.UPLOAD_DATE): "EgIQAUICCAI%3D",
    (VideoType.VIDEO, None, SortBy.VIEWS): "EgIQAUICCAM%3D",
    # video + duration + sort
    (VideoType.VIDEO, Duration.SHORT, SortBy.UPLOAD_DATE): "EgQQARgDQgIIAg%3D%3D",
    (VideoType.VIDEO, Duration.MEDIUM, SortBy.UPLOAD_DATE): "EgQQARgCQgIIAg%3D%3D",
    (VideoType.VIDEO, Duration.LONG, SortBy.UPLOAD_DATE): "EgQQARgEQgIIAg%3D%3D",
    (VideoType.VIDEO, Duration.SHORT, SortBy.VIEWS): "EgQQARgDQgIIAw%3D%3D",
    (VideoType.VIDEO, Duration.MEDIUM, SortBy.VIEWS): "EgQQARgCQgIIAw%3D%3D",
    (VideoType.VIDEO, Duration.LONG, SortBy.VIEWS): "EgQQARgEQgIIAw%3D%3D",
}


def build_sp_param(
    video_type: Optional[VideoType] = None,
    duration: Optional[Duration] = None,
    sort_by: Optional[SortBy] = None,
) -> Optional[str]:
    """Return the sp= URL parameter for the given filter combination, or None if no filters."""
    if video_type is None and duration is None and (sort_by is None or sort_by == SortBy.RELEVANCE):
        return None
    key = (video_type, duration, sort_by if sort_by != SortBy.RELEVANCE else None)
    return _SP_TABLE.get(key)

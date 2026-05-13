import base64
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


class UploadDate(str, Enum):
    HOUR = "hour"
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


_SORT_BY_VALUE = {SortBy.RATING: 1, SortBy.UPLOAD_DATE: 2, SortBy.VIEWS: 3}
_UPLOAD_DATE_VALUE = {
    UploadDate.HOUR: 1, UploadDate.TODAY: 2, UploadDate.WEEK: 3,
    UploadDate.MONTH: 4, UploadDate.YEAR: 5,
}
_DURATION_VALUE = {Duration.MEDIUM: 2, Duration.SHORT: 3, Duration.LONG: 4}


def _encode_varint(val: int) -> bytes:
    result = []
    while val > 0x7F:
        result.append((val & 0x7F) | 0x80)
        val >>= 7
    result.append(val)
    return bytes(result)


def _encode_varint_field(field_num: int, val: int) -> bytes:
    tag = (field_num << 3) | 0
    return bytes([tag]) + _encode_varint(val)


def _encode_message_field(field_num: int, content: bytes) -> bytes:
    tag = (field_num << 3) | 2
    return bytes([tag, len(content)]) + content


def build_sp_param(
    video_type: Optional[VideoType] = None,
    duration: Optional[Duration] = None,
    sort_by: Optional[SortBy] = None,
    upload_date: Optional[UploadDate] = None,
) -> Optional[str]:
    if (video_type is None and duration is None and upload_date is None
            and (sort_by is None or sort_by == SortBy.RELEVANCE)):
        return None

    parts = b""

    if sort_by and sort_by != SortBy.RELEVANCE:
        parts += _encode_varint_field(1, _SORT_BY_VALUE[sort_by])

    filters = b""
    if upload_date:
        filters += _encode_varint_field(1, _UPLOAD_DATE_VALUE[upload_date])
    if video_type == VideoType.VIDEO:
        filters += _encode_varint_field(2, 1)
    elif video_type == VideoType.SHORTS:
        filters += _encode_varint_field(2, 9)
    if duration:
        filters += _encode_varint_field(3, _DURATION_VALUE[duration])
    if video_type == VideoType.LIVE:
        filters += _encode_varint_field(8, 1)

    if filters:
        parts += _encode_message_field(2, filters)

    return base64.b64encode(parts).decode()

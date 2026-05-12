import csv
import sys
from datetime import date
from typing import IO, Optional

from trend_rover.storage.db import Database

PLATFORM_DISPLAY = {
    "youtube": "YouTube",
    "x": "X",
}


def export_csv(
    db: Database,
    keyword: str,
    platforms: list[str],
    date_str: str,
    output: IO = None,
) -> None:
    """
    Write transposed summary CSV to output (file-like object).
    date_str format: YYYYMMDD — used as display label and date filter.
    """
    if output is None:
        output = sys.stdout

    # parse date_str to filter by exact day
    filter_date = date(
        int(date_str[:4]),
        int(date_str[4:6]),
        int(date_str[6:8]),
    )

    cols: list[dict] = []
    for platform in platforms:
        feeds = db.query(
            keyword=keyword,
            platform=platform,
            start_date=filter_date,
            end_date=filter_date,
        )
        total_views = sum(f.views for f in feeds)
        total_interactions = sum(f.shares + f.comments + f.likes for f in feeds)
        cols.append({
            "platform": PLATFORM_DISPLAY.get(platform, platform.upper()),
            "count": len(feeds),
            "views": total_views,
            "interactions": total_interactions,
        })

    writer = csv.writer(output)
    writer.writerow(["媒体平台"] + [c["platform"] for c in cols])
    writer.writerow(["日期"] + [date_str] * len(cols))
    writer.writerow(["关键词"] + [keyword] * len(cols))
    writer.writerow(["视频/帖子数量"] + [c["count"] for c in cols])
    writer.writerow(["查看次数"] + [c["views"] for c in cols])
    writer.writerow(["互动次数（转发，评论，点赞）"] + [c["interactions"] for c in cols])

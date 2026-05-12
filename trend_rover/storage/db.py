import sqlite3
from datetime import date, datetime, timezone
from typing import Optional

from trend_rover.models import Feed


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS feeds (
    platform TEXT NOT NULL,
    feed_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    author TEXT NOT NULL,
    published_at TEXT NOT NULL,
    views INTEGER NOT NULL DEFAULT 0,
    likes INTEGER NOT NULL DEFAULT 0,
    comments INTEGER NOT NULL DEFAULT 0,
    shares INTEGER NOT NULL DEFAULT 0,
    bookmarks INTEGER NOT NULL DEFAULT 0,
    thumbnail_url TEXT NOT NULL DEFAULT '',
    logo_matched INTEGER NOT NULL DEFAULT 0,
    scraped_at TEXT NOT NULL,
    PRIMARY KEY (platform, feed_id)
)
"""

UPSERT = """
INSERT INTO feeds VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(platform, feed_id) DO UPDATE SET
    views=excluded.views,
    likes=excluded.likes,
    comments=excluded.comments,
    shares=excluded.shares,
    bookmarks=excluded.bookmarks,
    logo_matched=excluded.logo_matched,
    scraped_at=excluded.scraped_at
"""


def _row_to_feed(row) -> Feed:
    return Feed(
        platform=row[0],
        feed_id=row[1],
        keyword=row[2],
        title=row[3],
        url=row[4],
        author=row[5],
        published_at=datetime.fromisoformat(row[6]),
        views=row[7],
        likes=row[8],
        comments=row[9],
        shares=row[10],
        bookmarks=row[11],
        thumbnail_url=row[12],
        logo_matched=bool(row[13]),
        scraped_at=datetime.fromisoformat(row[14]),
    )


class Database:
    def __init__(self, path: str = None):
        if path is None:
            import os
            os.makedirs(os.path.expanduser("~/.trend-rover"), exist_ok=True)
            path = os.path.expanduser("~/.trend-rover/data.db")
        self._conn = sqlite3.connect(path)
        self._conn.execute(CREATE_TABLE)
        self._conn.commit()

    def upsert(self, feed: Feed) -> None:
        self._conn.execute(UPSERT, (
            feed.platform,
            feed.feed_id,
            feed.keyword,
            feed.title,
            feed.url,
            feed.author,
            feed.published_at.isoformat(),
            feed.views,
            feed.likes,
            feed.comments,
            feed.shares,
            feed.bookmarks,
            feed.thumbnail_url,
            int(feed.logo_matched),
            feed.scraped_at.isoformat(),
        ))
        self._conn.commit()

    def query(
        self,
        keyword: str,
        platform: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[Feed]:
        sql = "SELECT * FROM feeds WHERE keyword=?"
        params: list = [keyword]
        if platform:
            sql += " AND platform=?"
            params.append(platform)
        if start_date:
            sql += " AND published_at >= ?"
            params.append(start_date.isoformat())
        if end_date:
            sql += " AND published_at <= ?"
            params.append(f"{end_date.isoformat()}T23:59:59")
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_feed(r) for r in rows]

    def close(self) -> None:
        self._conn.close()

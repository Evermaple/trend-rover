from dataclasses import dataclass
from datetime import datetime


@dataclass
class Feed:
    platform: str
    feed_id: str
    keyword: str
    title: str
    url: str
    author: str
    published_at: datetime
    views: int
    likes: int
    comments: int
    shares: int
    bookmarks: int
    thumbnail_url: str
    logo_matched: bool
    scraped_at: datetime

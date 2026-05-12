# Trend Rover Plan 1: Project Scaffold + Data Model + Storage

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap the project structure, define the core `Feed` data model and abstract base classes, implement SQLite persistence, and CSV export — everything downstream plans depend on.

**Architecture:** Single Python package `trend_rover` with submodules for scrapers, vision, storage, dashboard, and skill. Storage uses SQLite via the standard library `sqlite3` module. CSV export writes the transposed summary format defined in the spec.

**Tech Stack:** Python 3.11+, sqlite3 (stdlib), dataclasses, abc, tomllib (stdlib 3.11+), pytest

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Package metadata, dependencies, entry point |
| `trend_rover/__init__.py` | Package version |
| `trend_rover/models.py` | `Feed` dataclass |
| `trend_rover/scrapers/__init__.py` | Empty |
| `trend_rover/scrapers/base.py` | `BaseScraper` ABC |
| `trend_rover/vision/__init__.py` | Empty |
| `trend_rover/vision/base.py` | `BaseDetector` ABC |
| `trend_rover/storage/__init__.py` | Empty |
| `trend_rover/storage/db.py` | SQLite init, insert, query |
| `trend_rover/storage/export.py` | CSV export |
| `trend_rover/config.py` | Load `~/.trend-rover/config.toml` |
| `tests/__init__.py` | Empty |
| `tests/test_models.py` | Feed dataclass tests |
| `tests/test_storage.py` | SQLite and CSV tests |
| `tests/test_config.py` | Config loading tests |

---

### Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `trend_rover/__init__.py`
- Create: `trend_rover/scrapers/__init__.py`
- Create: `trend_rover/vision/__init__.py`
- Create: `trend_rover/storage/__init__.py`
- Create: `trend_rover/dashboard/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "trend-rover"
version = "0.1.0"
description = "Track brand keyword trends across YouTube and X"
requires-python = ">=3.11"
dependencies = [
    "playwright>=1.44",
    "httpx>=0.27",
    "opencv-python>=4.9",
    "gradio>=4.36",
    "rich>=13.7",
    "anthropic>=0.28",
    "openai>=1.30",
]

[project.scripts]
trend-rover = "trend_rover.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package init files**

`trend_rover/__init__.py`:
```python
__version__ = "0.1.0"
```

All other `__init__.py` files (scrapers, vision, storage, dashboard, tests): empty files.

```bash
mkdir -p trend_rover/scrapers trend_rover/vision trend_rover/storage trend_rover/dashboard trend_rover/skill tests
touch trend_rover/scrapers/__init__.py trend_rover/vision/__init__.py trend_rover/storage/__init__.py trend_rover/dashboard/__init__.py tests/__init__.py
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -e ".[dev]" 2>/dev/null || pip install -e .
pip install pytest
playwright install chromium
```

- [ ] **Step 4: Commit**

```bash
git init
git add pyproject.toml trend_rover/ tests/
git commit -m "chore: project scaffold"
```

---

### Task 2: Feed Data Model

**Files:**
- Create: `trend_rover/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:
```python
from datetime import datetime, timezone
from trend_rover.models import Feed


def test_feed_defaults():
    feed = Feed(
        platform="youtube",
        feed_id="abc123",
        keyword="Pokekara",
        title="Pokekara Review",
        url="https://youtube.com/watch?v=abc123",
        author="TestChannel",
        published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        views=10000,
        likes=300,
        comments=50,
        shares=20,
        bookmarks=10,
        thumbnail_url="https://i.ytimg.com/vi/abc123/hqdefault.jpg",
        logo_matched=False,
        scraped_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )
    assert feed.platform == "youtube"
    assert feed.logo_matched is False
    assert feed.thumbnail_url == "https://i.ytimg.com/vi/abc123/hqdefault.jpg"


def test_feed_logo_matched():
    feed = Feed(
        platform="youtube",
        feed_id="xyz789",
        keyword="Pokekara",
        title="No keyword in title",
        url="https://youtube.com/watch?v=xyz789",
        author="TestChannel",
        published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        views=5000,
        likes=100,
        comments=10,
        shares=5,
        bookmarks=2,
        thumbnail_url="https://i.ytimg.com/vi/xyz789/hqdefault.jpg",
        logo_matched=True,
        scraped_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )
    assert feed.logo_matched is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```

Expected: `ImportError: cannot import name 'Feed' from 'trend_rover.models'`

- [ ] **Step 3: Implement Feed dataclass**

`trend_rover/models.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_models.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add trend_rover/models.py tests/test_models.py
git commit -m "feat: add Feed dataclass"
```

---

### Task 3: Abstract Base Classes

**Files:**
- Create: `trend_rover/scrapers/base.py`
- Create: `trend_rover/vision/base.py`

- [ ] **Step 1: Create BaseScraper**

`trend_rover/scrapers/base.py`:
```python
from abc import ABC, abstractmethod
from datetime import date

from trend_rover.models import Feed


class BaseScraper(ABC):
    @abstractmethod
    def search(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        **filters,
    ) -> list[Feed]:
        """Search for feeds matching keyword in date range."""

    @abstractmethod
    def get_stats(self, feed_id: str) -> Feed:
        """Fetch latest engagement stats for a single feed."""
```

- [ ] **Step 2: Create BaseDetector**

`trend_rover/vision/base.py`:
```python
from abc import ABC, abstractmethod


class BaseDetector(ABC):
    @abstractmethod
    def detect(self, thumbnail_path: str, logo_path: str) -> tuple[bool, float]:
        """
        Check if thumbnail contains logo.
        Returns (matched, confidence_score).
        """
```

- [ ] **Step 3: Verify imports work**

```bash
python -c "from trend_rover.scrapers.base import BaseScraper; from trend_rover.vision.base import BaseDetector; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add trend_rover/scrapers/base.py trend_rover/vision/base.py
git commit -m "feat: add BaseScraper and BaseDetector ABCs"
```

---

### Task 4: SQLite Storage

**Files:**
- Create: `trend_rover/storage/db.py`
- Create: `tests/test_storage.py` (partial — SQLite section)

- [ ] **Step 1: Write failing tests for db**

`tests/test_storage.py`:
```python
import tempfile
import os
from datetime import datetime, timezone, date

import pytest

from trend_rover.models import Feed
from trend_rover.storage.db import Database


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    d = Database(path)
    yield d
    d.close()
    os.unlink(path)


def _make_feed(feed_id="abc123", keyword="Pokekara", platform="youtube", logo_matched=False):
    return Feed(
        platform=platform,
        feed_id=feed_id,
        keyword=keyword,
        title=f"Title {feed_id}",
        url=f"https://youtube.com/watch?v={feed_id}",
        author="TestChannel",
        published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        views=10000,
        likes=300,
        comments=50,
        shares=20,
        bookmarks=10,
        thumbnail_url=f"https://i.ytimg.com/vi/{feed_id}/hqdefault.jpg",
        logo_matched=logo_matched,
        scraped_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )


def test_insert_and_query(db):
    feed = _make_feed()
    db.upsert(feed)
    results = db.query(keyword="Pokekara", platform="youtube")
    assert len(results) == 1
    assert results[0].feed_id == "abc123"
    assert results[0].views == 10000


def test_upsert_deduplicates(db):
    feed = _make_feed()
    db.upsert(feed)
    db.upsert(feed)  # same platform+feed_id
    results = db.query(keyword="Pokekara", platform="youtube")
    assert len(results) == 1


def test_query_filters_by_date(db):
    feed_apr = _make_feed(feed_id="apr")
    feed_apr.published_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    feed_may = _make_feed(feed_id="may")
    feed_may.published_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    db.upsert(feed_apr)
    db.upsert(feed_may)

    results = db.query(
        keyword="Pokekara",
        platform="youtube",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
    )
    assert len(results) == 1
    assert results[0].feed_id == "may"


def test_query_filters_by_platform(db):
    yt_feed = _make_feed(feed_id="yt1", platform="youtube")
    x_feed = _make_feed(feed_id="x1", platform="x")
    db.upsert(yt_feed)
    db.upsert(x_feed)

    results = db.query(keyword="Pokekara", platform="x")
    assert len(results) == 1
    assert results[0].feed_id == "x1"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_storage.py -v -k "not csv"
```

Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Implement Database**

`trend_rover/storage/db.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_storage.py -v -k "not csv"
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add trend_rover/storage/db.py tests/test_storage.py
git commit -m "feat: SQLite storage with upsert and query"
```

---

### Task 5: CSV Export

**Files:**
- Create: `trend_rover/storage/export.py`
- Modify: `tests/test_storage.py` (add CSV tests)

- [ ] **Step 1: Write failing CSV tests**

Append to `tests/test_storage.py`:
```python
import csv
import io
from trend_rover.storage.export import export_csv


def test_csv_export_single_platform(db):
    feed = _make_feed(feed_id="v1", platform="youtube")
    feed.views = 10000
    feed.likes = 300
    feed.comments = 50
    feed.shares = 20
    feed.bookmarks = 10
    db.upsert(feed)

    buf = io.StringIO()
    export_csv(
        db,
        keyword="Pokekara",
        platforms=["youtube"],
        date_str="20260426",
        output=buf,
    )
    buf.seek(0)
    rows = list(csv.reader(buf))

    assert rows[0] == ["媒体平台", "YouTube"]
    assert rows[1] == ["日期", "20260426"]
    assert rows[2] == ["关键词", "Pokekara"]
    assert rows[3][0] == "视频/帖子数量"
    assert int(rows[3][1]) == 1
    assert rows[4][0] == "查看次数"
    assert int(rows[4][1]) == 10000
    assert rows[5][0] == "互动次数（转发，评论，点赞）"
    assert int(rows[5][1]) == 370  # 20+50+300


def test_csv_export_two_platforms(db):
    yt = _make_feed(feed_id="v1", platform="youtube")
    yt.views = 10000
    yt.likes = 300
    yt.comments = 50
    yt.shares = 20
    yt.bookmarks = 10
    x_feed = _make_feed(feed_id="t1", platform="x")
    x_feed.views = 2000
    x_feed.likes = 100
    x_feed.comments = 10
    x_feed.shares = 5
    x_feed.bookmarks = 3
    db.upsert(yt)
    db.upsert(x_feed)

    buf = io.StringIO()
    export_csv(
        db,
        keyword="Pokekara",
        platforms=["youtube", "x"],
        date_str="20260426",
        output=buf,
    )
    buf.seek(0)
    rows = list(csv.reader(buf))

    assert rows[0] == ["媒体平台", "YouTube", "X"]
    assert rows[3][0] == "视频/帖子数量"
    assert int(rows[3][1]) == 1
    assert int(rows[3][2]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_storage.py -v -k "csv"
```

Expected: `ImportError: cannot import name 'export_csv'`

- [ ] **Step 3: Implement export_csv**

`trend_rover/storage/export.py`:
```python
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
```

- [ ] **Step 4: Run all storage tests**

```bash
pytest tests/test_storage.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add trend_rover/storage/export.py tests/test_storage.py
git commit -m "feat: CSV export in transposed summary format"
```

---

### Task 6: Config Loading

**Files:**
- Create: `trend_rover/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

`tests/test_config.py`:
```python
import tempfile
import os
import pytest
from trend_rover.config import Config, load_config


def test_default_config():
    config = Config()
    assert config.scraper_delay_min == 2
    assert config.scraper_delay_max == 5
    assert config.scraper_max_retries == 3
    assert config.vision_engine == "opencv"
    assert config.vision_threshold == 0.8
    assert config.x_cookies_file is None


def test_load_from_toml():
    toml_content = """
[scraper]
delay_min = 1
delay_max = 3
max_retries = 5

[scraper.x]
cookies_file = "/home/user/.trend-rover/x_cookies.json"

[vision]
engine = "llm"
threshold = 0.9

[vision.llm]
provider = "claude"
api_key = "sk-test"
model = "claude-sonnet-4-6"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        path = f.name

    try:
        config = load_config(path)
        assert config.scraper_delay_min == 1
        assert config.scraper_delay_max == 3
        assert config.scraper_max_retries == 5
        assert config.x_cookies_file == "/home/user/.trend-rover/x_cookies.json"
        assert config.vision_engine == "llm"
        assert config.vision_threshold == 0.9
        assert config.llm_provider == "claude"
        assert config.llm_api_key == "sk-test"
        assert config.llm_model == "claude-sonnet-4-6"
    finally:
        os.unlink(path)


def test_missing_config_file_returns_defaults():
    config = load_config("/nonexistent/path/config.toml")
    assert config.scraper_delay_min == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `ImportError: cannot import name 'Config'`

- [ ] **Step 3: Implement config**

`trend_rover/config.py`:
```python
import tomllib
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    scraper_delay_min: float = 2.0
    scraper_delay_max: float = 5.0
    scraper_max_retries: int = 3
    x_cookies_file: Optional[str] = None
    vision_engine: str = "opencv"
    vision_threshold: float = 0.8
    llm_provider: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None


def load_config(path: str = None) -> Config:
    if path is None:
        import os
        path = os.path.expanduser("~/.trend-rover/config.toml")

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        return Config()

    scraper = data.get("scraper", {})
    x_section = scraper.get("x", {})
    vision = data.get("vision", {})
    llm = vision.get("llm", {})

    return Config(
        scraper_delay_min=scraper.get("delay_min", 2.0),
        scraper_delay_max=scraper.get("delay_max", 5.0),
        scraper_max_retries=scraper.get("max_retries", 3),
        x_cookies_file=x_section.get("cookies_file"),
        vision_engine=vision.get("engine", "opencv"),
        vision_threshold=vision.get("threshold", 0.8),
        llm_provider=llm.get("provider"),
        llm_api_key=llm.get("api_key"),
        llm_model=llm.get("model"),
    )
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add trend_rover/config.py tests/test_config.py
git commit -m "feat: config loading from TOML with defaults"
```

---

### Task 7: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass, 0 errors

- [ ] **Step 2: Verify package imports cleanly**

```bash
python -c "
from trend_rover.models import Feed
from trend_rover.scrapers.base import BaseScraper
from trend_rover.vision.base import BaseDetector
from trend_rover.storage.db import Database
from trend_rover.storage.export import export_csv
from trend_rover.config import Config, load_config
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 3: Commit final state**

```bash
git add -A
git commit -m "chore: plan 1 complete — scaffold, models, storage, config"
```

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from itemadapter import ItemAdapter

from comic_crawler.items import BookItem, ChapterItem, ImageItem
from comic_crawler.paths import extension_from_url


class MetadataAndImagePipeline:
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.connection: sqlite3.Connection | None = None
        self.spider = None

    @classmethod
    def from_crawler(cls, crawler):
        config = crawler.settings.getdict("CRAWLER_CONFIG")
        database_path = config.get("storage", {}).get("database", "data/crawler.sqlite3")
        pipeline = cls(database_path)
        pipeline.spider = crawler.spider
        return pipeline

    def open_spider(self) -> None:
        spider = self.spider
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self.create_schema()
        self.connection.execute(
            """
            INSERT INTO crawl_runs (spider, entry_url, config, started_at, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                spider.name,
                getattr(spider, "start_url", ""),
                json.dumps(getattr(spider, "config", {}), ensure_ascii=False),
                utc_now(),
                "running",
            ),
        )
        self.connection.commit()

    def close_spider(self) -> None:
        if self.connection is None:
            return
        self.connection.execute(
            """
            UPDATE crawl_runs
            SET ended_at = ?, status = ?
            WHERE id = (SELECT id FROM crawl_runs ORDER BY id DESC LIMIT 1)
            """,
            (utc_now(), "finished"),
        )
        self.connection.commit()
        self.connection.close()

    def process_item(self, item):
        if isinstance(item, BookItem):
            self.save_book(ItemAdapter(item).asdict())
        elif isinstance(item, ChapterItem):
            self.save_chapter(ItemAdapter(item).asdict())
        elif isinstance(item, ImageItem):
            self.save_image(ItemAdapter(item).asdict())
        return item

    def create_schema(self) -> None:
        assert self.connection is not None
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                book_id TEXT PRIMARY KEY,
                site TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                author TEXT,
                status TEXT,
                area TEXT,
                tags TEXT,
                updated_at TEXT,
                description TEXT,
                cover_url TEXT,
                latest_chapter_name TEXT,
                latest_chapter_url TEXT,
                local_dir TEXT,
                saved_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chapters (
                chapter_id TEXT PRIMARY KEY,
                book_id TEXT NOT NULL,
                site TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                original_index INTEGER NOT NULL,
                crawl_index INTEGER NOT NULL,
                previous_url TEXT,
                next_url TEXT,
                image_count INTEGER NOT NULL DEFAULT 0,
                local_dir TEXT,
                image_urls TEXT,
                saved_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                site TEXT NOT NULL,
                source_url TEXT NOT NULL,
                page_index INTEGER NOT NULL,
                local_path TEXT NOT NULL,
                status INTEGER,
                skipped INTEGER NOT NULL DEFAULT 0,
                content_type TEXT,
                sha256 TEXT,
                size INTEGER,
                error TEXT,
                saved_at TEXT NOT NULL,
                UNIQUE(chapter_id, page_index),
                UNIQUE(source_url, local_path)
            );

            CREATE TABLE IF NOT EXISTS crawl_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spider TEXT NOT NULL,
                entry_url TEXT NOT NULL,
                config TEXT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def save_book(self, item: dict[str, Any]) -> None:
        local_dir = Path(item["local_dir"])
        (local_dir / "cover").mkdir(parents=True, exist_ok=True)
        (local_dir / "chapters").mkdir(parents=True, exist_ok=True)
        write_json(local_dir / "book.json", item)

        assert self.connection is not None
        self.connection.execute(
            """
            INSERT INTO books (
                book_id, site, url, title, author, status, area, tags, updated_at,
                description, cover_url, latest_chapter_name, latest_chapter_url,
                local_dir, saved_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(book_id) DO UPDATE SET
                site=excluded.site,
                url=excluded.url,
                title=excluded.title,
                author=excluded.author,
                status=excluded.status,
                area=excluded.area,
                tags=excluded.tags,
                updated_at=excluded.updated_at,
                description=excluded.description,
                cover_url=excluded.cover_url,
                latest_chapter_name=excluded.latest_chapter_name,
                latest_chapter_url=excluded.latest_chapter_url,
                local_dir=excluded.local_dir,
                saved_at=excluded.saved_at
            """,
            (
                item["book_id"],
                item["site"],
                item["url"],
                item["title"],
                item.get("author"),
                item.get("status"),
                item.get("area"),
                json.dumps(item.get("tags", []), ensure_ascii=False),
                item.get("updated_at"),
                item.get("description"),
                item.get("cover_url"),
                item.get("latest_chapter_name"),
                item.get("latest_chapter_url"),
                item.get("local_dir"),
                utc_now(),
            ),
        )
        self.connection.commit()

    def save_chapter(self, item: dict[str, Any]) -> None:
        local_dir = Path(item["local_dir"])
        (local_dir / "images").mkdir(parents=True, exist_ok=True)
        write_json(local_dir / "chapter.json", item)

        assert self.connection is not None
        self.connection.execute(
            """
            INSERT INTO chapters (
                chapter_id, book_id, site, url, title, original_index, crawl_index,
                previous_url, next_url, image_count, local_dir, image_urls, saved_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chapter_id) DO UPDATE SET
                book_id=excluded.book_id,
                site=excluded.site,
                url=excluded.url,
                title=excluded.title,
                original_index=excluded.original_index,
                crawl_index=excluded.crawl_index,
                previous_url=excluded.previous_url,
                next_url=excluded.next_url,
                image_count=excluded.image_count,
                local_dir=excluded.local_dir,
                image_urls=excluded.image_urls,
                saved_at=excluded.saved_at
            """,
            (
                item["chapter_id"],
                item["book_id"],
                item["site"],
                item["url"],
                item["title"],
                int(item["original_index"]),
                int(item["crawl_index"]),
                item.get("previous_url"),
                item.get("next_url"),
                int(item.get("image_count", 0)),
                item.get("local_dir"),
                json.dumps(item.get("image_urls", []), ensure_ascii=False),
                utc_now(),
            ),
        )
        self.connection.commit()

    def save_image(self, item: dict[str, Any]) -> None:
        local_path = Path(item["local_path"])
        local_path.parent.mkdir(parents=True, exist_ok=True)

        body = item.get("body")
        skipped = bool(item.get("skipped"))
        content_type = item.get("content_type")
        if body and not skipped:
            suffix = extension_from_url(item["source_url"], content_type)
            if local_path.suffix != suffix:
                local_path = local_path.with_suffix(suffix)
                item["local_path"] = str(local_path)
            local_path.write_bytes(body)

        sha256 = None
        size = None
        if local_path.exists():
            data = local_path.read_bytes()
            sha256 = hashlib.sha256(data).hexdigest()
            size = len(data)

        assert self.connection is not None
        self.connection.execute(
            """
            INSERT INTO images (
                book_id, chapter_id, site, source_url, page_index, local_path,
                status, skipped, content_type, sha256, size, error, saved_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chapter_id, page_index) DO UPDATE SET
                source_url=excluded.source_url,
                local_path=excluded.local_path,
                status=excluded.status,
                skipped=excluded.skipped,
                content_type=excluded.content_type,
                sha256=excluded.sha256,
                size=excluded.size,
                error=excluded.error,
                saved_at=excluded.saved_at
            """,
            (
                item["book_id"],
                item["chapter_id"],
                item["site"],
                item["source_url"],
                int(item["page_index"]),
                str(local_path),
                item.get("status"),
                1 if skipped else 0,
                content_type,
                sha256,
                size,
                item.get("error"),
                utc_now(),
            ),
        )
        self.connection.commit()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

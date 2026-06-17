from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

import scrapy

from comic_crawler.config import DEFAULT_CONFIG
from comic_crawler.items import BookItem, ChapterItem, ImageItem
from comic_crawler.paths import (
    book_dir,
    chapter_dir,
    extract_numeric_id,
    image_path,
    site_name,
)
from comic_crawler.viewer import IMAGE_EXTENSIONS


class QuquBookSpider(scrapy.Spider):
    name = "ququ_book"
    allowed_domains = ["ququmh.top", "www.ququmh.top", "tupian.run"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config: dict[str, Any] = {}
        self.start_url = ""

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.config = crawler.settings.getdict("CRAWLER_CONFIG") or DEFAULT_CONFIG
        spider.start_url = spider.config["target"]["url"]
        return spider

    async def start(self):
        for request in self.start_requests():
            yield request

    def start_requests(self):
        yield scrapy.Request(self.start_url, callback=self.parse_book)

    def parse_book(self, response):
        book_id = extract_numeric_id(response.url, "book")
        site = site_name(response.url)
        title = first_text(
            response.css('meta[property="og:novel:book_name"]::attr(content)').get(),
            response.css('meta[property="og:title"]::attr(content)').get(),
            response.css(".banner_detail_form .info h1::text").get(),
        )
        author = first_text(
            response.css('meta[property="og:novel:author"]::attr(content)').get(),
            text_after(response, "作者："),
        )
        status = first_text(
            response.css('meta[property="og:novel:status"]::attr(content)').get(),
            text_after(response, "状态："),
        )
        area = clean_text(response.css(".banner_detail_form .ticai a::text").get())
        tags = [clean_text(tag) for tag in response.css('a[href*="tag="]::text').getall()]
        updated_at = first_text(
            response.css('meta[property="og:novel:update_time"]::attr(content)').get(),
            text_after(response, "更新时间："),
        )
        description = first_text(
            response.css('meta[property="og:description"]::attr(content)').get(),
            response.css(".banner_detail_form .content::text").get(),
        )
        cover_url = response.urljoin(
            first_text(
                response.css('meta[property="og:image"]::attr(content)').get(),
                response.css(".banner_detail_form .cover img::attr(src)").get(),
            )
        )
        latest_chapter_name = clean_text(
            response.css('meta[property="og:novel:latest_chapter_name"]::attr(content)').get()
        )
        latest_chapter_url = response.urljoin(
            response.css('meta[property="og:novel:latest_chapter_url"]::attr(content)').get()
            or ""
        )

        output_dir = Path(self.config["storage"]["output_dir"])
        root_dir = book_dir(output_dir, site, book_id, title)
        direct_chapters = parse_chapter_links(response)

        yield BookItem(
            book_id=book_id,
            site=site,
            url=response.url,
            title=title,
            author=author,
            status=status,
            area=area,
            tags=tags,
            updated_at=updated_at,
            description=description,
            cover_url=cover_url,
            latest_chapter_name=latest_chapter_name,
            latest_chapter_url=latest_chapter_url,
            local_dir=str(root_dir),
            chapters=direct_chapters,
        )

        if self.config["crawl"].get("download_images", True) and cover_url:
            cover_path = root_dir / "cover" / "cover.jpg"
            yield self.image_request_or_skip(
                source_url=cover_url,
                referer=response.url,
                local_path=cover_path,
                book_id=book_id,
                chapter_id="cover",
                site=site,
                page_index=0,
            )

        first_chapter_url = response.css(".banner_detail_form .bottom .btn-2::attr(href)").get()
        chapter_index_url = latest_chapter_url if latest_chapter_url else response.urljoin(first_chapter_url or "")
        if chapter_index_url:
            yield scrapy.Request(
                chapter_index_url,
                callback=self.parse_chapter_index,
                meta={
                    "book": {
                        "book_id": book_id,
                        "site": site,
                        "url": response.url,
                        "title": title,
                        "author": author,
                        "status": status,
                        "area": area,
                        "tags": tags,
                        "updated_at": updated_at,
                        "description": description,
                        "cover_url": cover_url,
                        "latest_chapter_name": latest_chapter_name,
                        "latest_chapter_url": latest_chapter_url,
                        "local_dir": str(root_dir),
                    }
                },
            )
            return

        yield from self.schedule_chapters(response, direct_chapters, book_id, title, root_dir, site)

    def parse_chapter_index(self, response):
        book = response.meta["book"]
        chapters = parse_chapter_links(response)
        if chapters:
            yield BookItem(**book, chapters=chapters)
        yield from self.schedule_chapters(
            response=response,
            chapters=chapters,
            book_id=book["book_id"],
            book_title=book["title"],
            root_dir=Path(book["local_dir"]),
            site=book["site"],
        )

    def schedule_chapters(self, response, chapters, book_id, book_title, root_dir, site):
        chapter_order = self.config["crawl"].get("chapter_order", "desc")
        max_chapters = int(self.config["crawl"].get("max_chapters", 20))
        crawl_mode = self.config["crawl"].get("mode", "full")
        stop_on_existing = bool(self.config["crawl"].get("stop_on_existing_chapter", True))
        crawl_queue = select_chapters_for_crawl(
            chapters,
            root_dir=root_dir,
            chapter_order=chapter_order,
            max_chapters=max_chapters,
            incremental=crawl_mode == "incremental",
            stop_on_existing=stop_on_existing,
        )
        for crawl_index, chapter in enumerate(crawl_queue, start=1):
            chapter_url = response.urljoin(chapter["url"])
            meta = {
                "book_id": book_id,
                "book_title": book_title,
                "book_root": str(root_dir),
                "site": site,
                "original_index": chapter["original_index"],
                "crawl_index": crawl_index,
                "fallback_title": chapter["title"],
            }
            yield scrapy.Request(
                chapter_url,
                callback=self.parse_chapter,
                meta=meta,
                dont_filter=True,
            )

    def parse_chapter(self, response):
        book_id = response.meta["book_id"]
        site = response.meta["site"]
        original_index = int(response.meta["original_index"])
        crawl_index = int(response.meta["crawl_index"])
        chapter_id = extract_numeric_id(response.url, "chapter")
        title = first_text(
            response.css(".header h1.title::text").get(),
            response.css("title::text").get(),
            response.meta.get("fallback_title"),
        )
        title = title.replace(response.meta["book_title"], "").strip(" -_") or title
        root_dir = Path(response.meta["book_root"])
        current_chapter_dir = chapter_dir(root_dir, original_index, chapter_id, title)
        image_urls = parse_image_urls(response)

        previous_url = nav_link(response, "上一章")
        next_url = nav_link(response, "下一章")
        yield ChapterItem(
            book_id=book_id,
            chapter_id=chapter_id,
            site=site,
            url=response.url,
            title=title,
            original_index=original_index,
            crawl_index=crawl_index,
            previous_url=previous_url,
            next_url=next_url,
            image_count=len(image_urls),
            local_dir=str(current_chapter_dir),
            image_urls=image_urls,
        )

        if not self.config["crawl"].get("download_images", True):
            return

        for page_index, image_url in enumerate(image_urls, start=1):
            target_path = image_path(current_chapter_dir, page_index, image_url)
            yield self.image_request_or_skip(
                source_url=image_url,
                referer=response.url,
                local_path=target_path,
                book_id=book_id,
                chapter_id=chapter_id,
                site=site,
                page_index=page_index,
            )

    def parse_image(self, response, **kwargs):
        yield ImageItem(
            **kwargs,
            body=response.body,
            status=response.status,
            skipped=False,
            content_type=response.headers.get("Content-Type", b"").decode("latin1"),
            error=None,
        )

    def image_error(self, failure):
        request = failure.request
        yield ImageItem(
            **request.cb_kwargs,
            body=None,
            status=None,
            skipped=False,
            content_type=None,
            error=str(failure.value),
        )

    def image_request_or_skip(
        self,
        *,
        source_url: str,
        referer: str,
        local_path: Path,
        book_id: str,
        chapter_id: str,
        site: str,
        page_index: int,
    ):
        kwargs = {
            "book_id": book_id,
            "chapter_id": chapter_id,
            "site": site,
            "url": source_url,
            "source_url": source_url,
            "page_index": page_index,
            "local_path": str(local_path),
            "referer": referer,
        }
        if local_path.exists() and local_path.stat().st_size > 0:
            return ImageItem(
                **kwargs,
                body=None,
                status=200,
                skipped=True,
                content_type=None,
                error=None,
            )
        return scrapy.Request(
            source_url,
            callback=self.parse_image,
            errback=self.image_error,
            headers={"Referer": referer},
            cb_kwargs=kwargs,
            dont_filter=True,
        )


def parse_chapter_links(response) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    seen: set[str] = set()
    selectors = response.css(".sidebar-content a[href*='/chapter/']")
    if not selectors:
        selectors = response.css("#detail-list-select a[href*='/chapter/']")
    if not selectors:
        selectors = response.css("a[href*='/chapter/']")
    for selector in selectors:
        href = selector.css("::attr(href)").get()
        title = clean_text(" ".join(selector.css("::text").getall()))
        if not href or not title:
            continue
        absolute_url = response.urljoin(href)
        parsed = urlparse(absolute_url)
        if "/chapter/" not in parsed.path:
            continue
        chapter_id = extract_numeric_id(absolute_url, "chapter")
        if not chapter_id or not chapter_id.isdigit() or chapter_id in seen:
            continue
        seen.add(chapter_id)
        display_index = leading_number(title) or len(links) + 1
        links.append(
            {
                "chapter_id": chapter_id,
                "title": title,
                "url": absolute_url,
                "original_index": display_index,
            }
        )
    return links


def parse_image_urls(response) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for selector in response.css(".imgpic img, .comicpage img"):
        candidates = [
            selector.css("::attr(src)").get(),
            selector.css("::attr(data-original)").get(),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            absolute_url = response.urljoin(candidate)
            lower = absolute_url.lower()
            if "loadimg" in lower or lower.endswith(".webp") and "/static/" in lower:
                continue
            if absolute_url in seen:
                continue
            seen.add(absolute_url)
            urls.append(absolute_url)
            break
    return urls


def nav_link(response, label: str) -> str | None:
    href = response.xpath(f"//a[contains(normalize-space(.), '{label}')]/@href").get()
    return response.urljoin(href) if href else None


def text_after(response, label: str) -> str:
    text = " ".join(response.css(".banner_detail_form .info *::text").getall())
    if label not in text:
        return ""
    return clean_text(text.split(label, 1)[1].split(" ", 1)[0])


def first_text(*values: str | None) -> str:
    for value in values:
        cleaned = clean_text(value)
        if cleaned:
            return cleaned
    return ""


def clean_text(value: str | None) -> str:
    return " ".join((value or "").split())


def leading_number(value: str) -> int | None:
    match = re.match(r"^\s*(\d+)", value)
    return int(match.group(1)) if match else None


def select_chapters_for_crawl(
    chapters: list[dict[str, Any]],
    *,
    root_dir: Path,
    chapter_order: str,
    max_chapters: int,
    incremental: bool,
    stop_on_existing: bool,
) -> list[dict[str, Any]]:
    crawl_queue = list(reversed(chapters)) if chapter_order == "desc" else list(chapters)
    selected: list[dict[str, Any]] = []
    for chapter in crawl_queue:
        if len(selected) >= max_chapters:
            break
        if incremental and stop_on_existing and local_chapter_complete(root_dir, chapter):
            break
        selected.append(chapter)
    return selected


def local_chapter_complete(root_dir: Path, chapter: dict[str, Any]) -> bool:
    chapter_dir_path = find_local_chapter_dir(root_dir, chapter)
    if chapter_dir_path is None:
        return False
    metadata_path = chapter_dir_path / "chapter.json"
    if not metadata_path.is_file():
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    image_count = int(metadata.get("image_count") or 0)
    if image_count < 1:
        return False
    images_dir = chapter_dir_path / "images"
    if not images_dir.is_dir():
        return False
    existing_images = [
        path
        for path in images_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS and path.stat().st_size > 0
    ]
    return len(existing_images) >= image_count


def find_local_chapter_dir(root_dir: Path, chapter: dict[str, Any]) -> Path | None:
    prefix = f"{int(chapter.get('original_index') or 0):04d}_chapter_{chapter.get('chapter_id')}_"
    chapters_dir = root_dir / "chapters" if (root_dir / "chapters").exists() else root_dir
    candidates = sorted(chapters_dir.glob(f"{prefix}*"))
    return candidates[0] if candidates and candidates[0].is_dir() else None

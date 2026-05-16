from __future__ import annotations

import scrapy


class BookItem(scrapy.Item):
    book_id = scrapy.Field()
    site = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    author = scrapy.Field()
    status = scrapy.Field()
    area = scrapy.Field()
    tags = scrapy.Field()
    updated_at = scrapy.Field()
    description = scrapy.Field()
    cover_url = scrapy.Field()
    latest_chapter_name = scrapy.Field()
    latest_chapter_url = scrapy.Field()
    local_dir = scrapy.Field()
    chapters = scrapy.Field()


class ChapterItem(scrapy.Item):
    book_id = scrapy.Field()
    chapter_id = scrapy.Field()
    site = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    original_index = scrapy.Field()
    crawl_index = scrapy.Field()
    previous_url = scrapy.Field()
    next_url = scrapy.Field()
    image_count = scrapy.Field()
    local_dir = scrapy.Field()
    image_urls = scrapy.Field()


class ImageItem(scrapy.Item):
    book_id = scrapy.Field()
    chapter_id = scrapy.Field()
    site = scrapy.Field()
    url = scrapy.Field()
    source_url = scrapy.Field()
    page_index = scrapy.Field()
    local_path = scrapy.Field()
    referer = scrapy.Field()
    body = scrapy.Field()
    status = scrapy.Field()
    skipped = scrapy.Field()
    content_type = scrapy.Field()
    error = scrapy.Field()

from __future__ import annotations

from scrapy.http import HtmlResponse, Request

from comic_crawler.spiders.ququ_book import parse_chapter_links, parse_image_urls


def make_response(url: str, html: str) -> HtmlResponse:
    request = Request(url=url)
    return HtmlResponse(url=url, body=html.encode("utf-8"), encoding="utf-8", request=request)


def test_parse_chapter_links_keeps_original_order():
    response = make_response(
        "https://www.ququmh.top/book/3137",
        """
        <a href="/chapter/195669">1.姐姐1</a>
        <a href="/chapter/195670">2.姐姐2</a>
        <a href="/chapter/1102431">762 苦主</a>
        """,
    )

    chapters = parse_chapter_links(response)
    desc_queue = list(reversed(chapters))[:2]

    assert [chapter["chapter_id"] for chapter in chapters] == ["195669", "195670", "1102431"]
    assert [chapter["chapter_id"] for chapter in desc_queue] == ["1102431", "195670"]
    assert desc_queue[0]["original_index"] == 762


def test_parse_chapter_links_prefers_sidebar_full_catalog():
    response = make_response(
        "https://www.ququmh.top/chapter/1102431",
        """
        <div class="fanye"><a href="/chapter/1101500">上一章</a></div>
        <div class="sidebar-content">
          <a href="/chapter/195669">1.姐姐1</a>
          <a href="/chapter/195670">2.姐姐2</a>
          <a href="/chapter/1102431">762 苦主</a>
        </div>
        """,
    )

    chapters = parse_chapter_links(response)

    assert [chapter["chapter_id"] for chapter in chapters] == ["195669", "195670", "1102431"]
    assert chapters[-1]["original_index"] == 762


def test_parse_image_urls_prefers_real_src_and_filters_placeholder():
    response = make_response(
        "https://www.ququmh.top/chapter/1102431",
        """
        <div class="imgpic">
          <img class="lazy" data-original="https://res2.tupian.run/a/001.jpg" src="/static/images/loadimg.webp">
          <img src="https://res2.tupian.run/a/002.jpg" data-original="https://res2.tupian.run/placeholder.webp">
          <img src="/static/images/loadimg.webp">
        </div>
        """,
    )

    assert parse_image_urls(response) == [
        "https://res2.tupian.run/a/001.jpg",
        "https://res2.tupian.run/a/002.jpg",
    ]

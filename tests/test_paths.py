from __future__ import annotations

from pathlib import Path

from comic_crawler.paths import book_dir, chapter_dir, safe_name, site_name


def test_safe_name_removes_invalid_path_characters():
    assert safe_name('762 苦主/:*?"<>|') == "762 苦主"


def test_site_name_strips_www():
    assert site_name("https://www.ququmh.top/book/3137") == "ququmh.top"


def test_directory_shape_matches_site_structure():
    root = book_dir(Path("downloads"), "ququmh.top", "3137", "一人之下")
    chapter = chapter_dir(root, 762, "1102431", "762 苦主")

    assert str(chapter) == (
        "downloads/ququmh.top/book_3137_一人之下/"
        "chapters/0762_chapter_1102431_762 苦主"
    )

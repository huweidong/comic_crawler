from __future__ import annotations

import json

import pytest

from comic_crawler.viewer import (
    chapter_payload,
    list_images,
    media_path,
    scan_chapters,
)


def make_chapter(root, dirname, title, index, image_names):
    chapter_dir = root / dirname
    images_dir = chapter_dir / "images"
    images_dir.mkdir(parents=True)
    (chapter_dir / "chapter.json").write_text(
        json.dumps(
            {
                "title": title,
                "chapter_id": dirname.split("_")[2],
                "original_index": index,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    for image_name in image_names:
        (images_dir / image_name).write_bytes(b"image")
    return chapter_dir


def test_scan_chapters_orders_ascending_and_descending(tmp_path):
    make_chapter(tmp_path, "0733_chapter_1078180_733 处境", "733 处境", 733, ["0001.jpg"])
    make_chapter(tmp_path, "0762_chapter_1102431_762 苦主", "762 苦主", 762, ["0001.jpg"])

    asc = scan_chapters(tmp_path, "asc")
    desc = scan_chapters(tmp_path, "desc")

    assert [chapter.index for chapter in asc] == [733, 762]
    assert [chapter.index for chapter in desc] == [762, 733]


def test_scan_chapters_falls_back_to_directory_name(tmp_path):
    chapter_dir = tmp_path / "0750_chapter_1091966_750 死路"
    (chapter_dir / "images").mkdir(parents=True)
    (chapter_dir / "images" / "0001.jpg").write_bytes(b"image")

    chapters = scan_chapters(tmp_path, "desc")

    assert chapters[0].index == 750
    assert chapters[0].title == "750 死路"
    assert chapters[0].image_count == 1


def test_list_images_uses_natural_sort(tmp_path):
    chapter_dir = tmp_path / "0762_chapter_1102431_762 苦主"
    images_dir = chapter_dir / "images"
    images_dir.mkdir(parents=True)
    for name in ["0010.jpg", "0002.jpg", "0001.jpg", "note.txt"]:
        (images_dir / name).write_bytes(b"data")

    assert [path.name for path in list_images(chapter_dir)] == [
        "0001.jpg",
        "0002.jpg",
        "0010.jpg",
    ]


def test_chapter_payload_includes_media_urls(tmp_path):
    make_chapter(tmp_path, "0762_chapter_1102431_762 苦主", "762 苦主", 762, ["0001.jpg"])

    payload = chapter_payload(tmp_path, "0762_chapter_1102431_762 苦主")

    assert payload is not None
    assert payload["title"] == "762 苦主"
    assert payload["images"][0]["url"].startswith("/media/")


def test_media_path_rejects_nested_paths(tmp_path):
    make_chapter(tmp_path, "0762_chapter_1102431_762 苦主", "762 苦主", 762, ["0001.jpg"])

    with pytest.raises(ValueError):
        media_path(tmp_path, "../0762_chapter_1102431_762 苦主", "0001.jpg")

    with pytest.raises(ValueError):
        media_path(tmp_path, "0762_chapter_1102431_762 苦主", "../0001.jpg")

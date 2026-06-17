from __future__ import annotations

import json

from scripts.build_manifest import build_manifest, write_manifest


def make_chapter(root, dirname, title, index, image_names):
    chapter_dir = root / "chapters" / dirname
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


def test_build_manifest_sorts_chapters_and_images(tmp_path):
    book_dir = tmp_path / "book_3137_一人之下"
    make_chapter(book_dir, "0762_chapter_1102431_762 苦主", "762 苦主", 762, ["0010.jpg", "0001.jpg"])
    make_chapter(book_dir, "0733_chapter_1078180_733 处境", "733 处境", 733, ["0001.webp"])

    manifest = build_manifest(book_dir, "site/book")

    assert [chapter["index"] for chapter in manifest["chapters"]] == [733, 762]
    assert manifest["chapters"][1]["images"][0]["name"] == "0001.jpg"
    assert manifest["chapters"][1]["images"][0]["key"] == (
        "site/book/chapters/0762_chapter_1102431_762 苦主/images/0001.jpg"
    )
    assert manifest["chapters"][1]["images"][0]["url"].startswith("/media/")


def test_write_manifest_defaults_to_book_dir(tmp_path):
    book_dir = tmp_path / "book_3137_一人之下"
    make_chapter(book_dir, "0733_chapter_1078180_733 处境", "733 处境", 733, ["0001.jpg"])

    output = write_manifest(book_dir, None, "site/book")

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output == book_dir / "manifest.json"
    assert payload["r2_prefix"] == "site/book"
    assert payload["chapters"][0]["image_count"] == 1

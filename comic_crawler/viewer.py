from __future__ import annotations

import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
NUMBER_RE = re.compile(r"(\d+)")


@dataclass(frozen=True)
class ChapterPreview:
    name: str
    title: str
    chapter_id: str
    index: int
    image_count: int
    path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "chapter_id": self.chapter_id,
            "index": self.index,
            "image_count": self.image_count,
        }


def scan_chapters(chapters_dir: Path, order: str = "desc") -> list[ChapterPreview]:
    chapters_root = chapters_dir.resolve()
    if order not in {"asc", "desc"}:
        order = "desc"
    if not chapters_root.exists():
        return []

    chapters: list[ChapterPreview] = []
    for chapter_dir in chapters_root.iterdir():
        if not chapter_dir.is_dir():
            continue
        chapter = read_chapter(chapter_dir)
        if chapter is not None:
            chapters.append(chapter)

    return sorted(
        chapters,
        key=lambda chapter: (chapter.index, natural_key(chapter.name)),
        reverse=order == "desc",
    )


def read_chapter(chapter_dir: Path) -> ChapterPreview | None:
    metadata = read_json(chapter_dir / "chapter.json")
    fallback = parse_chapter_dir_name(chapter_dir.name)
    title = str(metadata.get("title") or fallback["title"] or chapter_dir.name)
    chapter_id = str(metadata.get("chapter_id") or fallback["chapter_id"] or "")
    index = safe_int(metadata.get("original_index"), fallback["index"])
    images = list_images(chapter_dir)

    return ChapterPreview(
        name=chapter_dir.name,
        title=title,
        chapter_id=chapter_id,
        index=index,
        image_count=len(images),
        path=chapter_dir.resolve(),
    )


def parse_chapter_dir_name(name: str) -> dict[str, Any]:
    parts = name.split("_", 3)
    index = safe_int(parts[0], 0) if parts else 0
    chapter_id = ""
    title = name
    if len(parts) >= 4 and parts[1] == "chapter":
        chapter_id = parts[2]
        title = parts[3]
    return {"index": index, "chapter_id": chapter_id, "title": title}


def list_images(chapter_dir: Path) -> list[Path]:
    images_dir = chapter_dir / "images"
    if not images_dir.exists():
        return []
    images = [
        path.resolve()
        for path in images_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(images, key=lambda path: natural_key(path.name))


def get_chapter(chapters_dir: Path, name: str) -> ChapterPreview | None:
    chapters_root = chapters_dir.resolve()
    chapter_dir = safe_child(chapters_root, name)
    if not chapter_dir.is_dir():
        return None
    return read_chapter(chapter_dir)


def chapter_payload(chapters_dir: Path, name: str) -> dict[str, Any] | None:
    chapter = get_chapter(chapters_dir, name)
    if chapter is None:
        return None
    images = [
        {
            "name": image.name,
            "url": f"/media/{url_component(chapter.name)}/images/{url_component(image.name)}",
        }
        for image in list_images(chapter.path)
    ]
    payload = chapter.to_dict()
    payload["images"] = images
    return payload


def media_path(chapters_dir: Path, chapter_name: str, image_name: str) -> Path:
    chapters_root = chapters_dir.resolve()
    chapter_dir = safe_child(chapters_root, chapter_name)
    image_path = safe_child(chapter_dir / "images", image_name)
    if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError("Unsupported image extension")
    if not image_path.is_file():
        raise FileNotFoundError(image_path)
    return image_path


def content_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def safe_child(parent: Path, child_name: str) -> Path:
    if "/" in child_name or "\\" in child_name:
        raise ValueError("Nested paths are not allowed")
    candidate = (parent.resolve() / child_name).resolve()
    candidate.relative_to(parent.resolve())
    return candidate


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def natural_key(value: str) -> list[int | str]:
    pieces: list[int | str] = []
    for piece in NUMBER_RE.split(value):
        if piece.isdigit():
            pieces.append(int(piece))
        elif piece:
            pieces.append(piece.lower())
    return pieces


def safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def url_component(value: str) -> str:
    from urllib.parse import quote

    return quote(value, safe="")

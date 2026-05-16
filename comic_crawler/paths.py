from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse


INVALID_PATH_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')
SPACES = re.compile(r"\s+")


def safe_name(value: str | None, fallback: str = "untitled", max_length: int = 80) -> str:
    name = (value or "").strip() or fallback
    name = INVALID_PATH_CHARS.sub("_", name)
    name = SPACES.sub(" ", name).strip(" ._")
    if not name:
        name = fallback
    return name[:max_length].strip(" ._") or fallback


def site_name(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def extract_numeric_id(url: str, marker: str) -> str:
    match = re.search(rf"/{re.escape(marker)}/+([^/?#]+)", url)
    return match.group(1) if match else ""


def book_dir(output_dir: Path, site: str, book_id: str, title: str) -> Path:
    return output_dir / site / f"book_{book_id}_{safe_name(title)}"


def chapter_dir(
    book_root: Path,
    original_index: int,
    chapter_id: str,
    title: str,
) -> Path:
    return (
        book_root
        / "chapters"
        / f"{original_index:04d}_chapter_{chapter_id}_{safe_name(title)}"
    )


def extension_from_url(url: str, content_type: str | None = None) -> str:
    if content_type:
        content_type = content_type.split(";")[0].strip().lower()
        mapping = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }
        if content_type in mapping:
            return mapping[content_type]

    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"


def image_path(chapter_root: Path, page_index: int, image_url: str) -> Path:
    return chapter_root / "images" / f"{page_index:04d}{extension_from_url(image_url)}"

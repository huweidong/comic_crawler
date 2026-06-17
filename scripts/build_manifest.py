from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from comic_crawler.viewer import list_images, read_json, scan_chapters, url_component


DEFAULT_BOOK_DIR = PROJECT_ROOT / "downloads" / "ququmh.top" / "book_3137_一人之下"
DEFAULT_PREFIX = "ququmh.top/book_3137_一人之下"


def build_manifest(book_dir: Path, r2_prefix: str = DEFAULT_PREFIX) -> dict[str, Any]:
    book_dir = book_dir.expanduser().resolve()
    chapters_dir = book_dir / "chapters"
    book_metadata = read_json(book_dir / "book.json")
    chapters = []

    for chapter in scan_chapters(chapters_dir, "asc"):
        images = []
        for image in list_images(chapter.path):
            r2_key = f"{r2_prefix}/chapters/{chapter.name}/images/{image.name}"
            images.append(
                {
                    "name": image.name,
                    "key": r2_key,
                    "url": f"/media/{url_component(chapter.name)}/images/{url_component(image.name)}",
                }
            )

        chapter_json_key = f"{r2_prefix}/chapters/{chapter.name}/chapter.json"
        chapters.append(
            {
                **chapter.to_dict(),
                "chapter_json_key": chapter_json_key,
                "images": images,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "r2_prefix": r2_prefix,
        "book": {
            "title": book_metadata.get("title") or "一人之下",
            "book_id": str(book_metadata.get("book_id") or "3137"),
            "site": book_metadata.get("site") or "ququmh.top",
        },
        "chapters": chapters,
    }


def write_manifest(book_dir: Path, output: Path | None, r2_prefix: str) -> Path:
    book_dir = book_dir.expanduser().resolve()
    output_path = (output.expanduser().resolve() if output else book_dir / "manifest.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(book_dir, r2_prefix)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Cloudflare R2 manifest for downloaded comics.")
    parser.add_argument("--book-dir", default=str(DEFAULT_BOOK_DIR), help="Downloaded book directory.")
    parser.add_argument("--output", help="Manifest output path. Defaults to <book-dir>/manifest.json.")
    parser.add_argument("--r2-prefix", default=DEFAULT_PREFIX, help="R2 key prefix for this book.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(args.output) if args.output else None
    output_path = write_manifest(Path(args.book_dir), output, args.r2_prefix.strip("/"))
    print(f"Manifest written: {output_path}")


if __name__ == "__main__":
    main()

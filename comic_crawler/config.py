from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG: dict[str, Any] = {
    "target": {"url": "https://www.ququmh.top/book/3137"},
    "crawl": {
        "chapter_order": "desc",
        "max_chapters": 20,
        "download_images": True,
    },
    "storage": {
        "output_dir": "downloads",
        "database": "data/crawler.sqlite3",
    },
    "request": {
        "obey_robots_txt": True,
        "concurrent_requests_per_domain": 1,
        "download_delay": 2,
        "timeout": 20,
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}

    config = deep_merge(DEFAULT_CONFIG, loaded)
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    target_url = config.get("target", {}).get("url")
    if not target_url:
        raise ValueError("config target.url is required")

    crawl = config.get("crawl", {})
    if crawl.get("chapter_order") not in {"asc", "desc"}:
        raise ValueError("config crawl.chapter_order must be 'asc' or 'desc'")

    max_chapters = int(crawl.get("max_chapters", 20))
    if max_chapters < 1:
        raise ValueError("config crawl.max_chapters must be >= 1")
    crawl["max_chapters"] = max_chapters

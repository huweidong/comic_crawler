from __future__ import annotations

import pytest

from comic_crawler.config import load_config


def test_load_config_default_max_chapters(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("target:\n  url: https://example.com/book/1\n", encoding="utf-8")

    config = load_config(config_path)

    assert config["crawl"]["max_chapters"] == 20
    assert config["crawl"]["chapter_order"] == "desc"


def test_load_config_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "missing.yaml")


def test_load_config_rejects_invalid_order(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "target:\n  url: https://example.com/book/1\ncrawl:\n  chapter_order: newest\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="chapter_order"):
        load_config(config_path)

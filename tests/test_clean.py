from __future__ import annotations

import pytest

from comic_crawler.clean import clean_local_data, plan_cleanup


def test_plan_cleanup_uses_configured_storage_paths(tmp_path):
    config = {
        "storage": {
            "output_dir": "downloads",
            "database": "data/crawler.sqlite3",
        }
    }

    targets = plan_cleanup(config, tmp_path)

    assert targets[0].path == tmp_path / "downloads"
    assert targets[0].kind == "directory"
    assert targets[1].path == tmp_path / "data" / "crawler.sqlite3"
    assert targets[1].kind == "file"


def test_clean_local_data_removes_downloads_and_database(tmp_path):
    downloads = tmp_path / "downloads"
    database = tmp_path / "data" / "crawler.sqlite3"
    (downloads / "site" / "book").mkdir(parents=True)
    (downloads / "site" / "book" / "book.json").write_text("{}", encoding="utf-8")
    database.parent.mkdir(parents=True)
    database.write_text("sqlite", encoding="utf-8")

    removed = clean_local_data(
        {
            "storage": {
                "output_dir": "downloads",
                "database": "data/crawler.sqlite3",
            }
        },
        tmp_path,
    )

    assert downloads in removed
    assert database in removed
    assert not downloads.exists()
    assert not database.exists()
    assert not database.parent.exists()


def test_clean_local_data_rejects_paths_outside_project(tmp_path):
    outside = tmp_path.parent / "outside-downloads"
    config = {
        "storage": {
            "output_dir": outside,
            "database": "data/crawler.sqlite3",
        }
    }

    with pytest.raises(ValueError, match="outside project"):
        clean_local_data(config, tmp_path)

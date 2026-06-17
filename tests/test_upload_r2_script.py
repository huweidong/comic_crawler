from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


PROJECT_DIR = Path(__file__).resolve().parents[1]
BOOK_DIR = PROJECT_DIR / "downloads" / "ququmh.top" / "book_3137_一人之下"
R2_PREFIX = "ququmh.top/book_3137_一人之下"


def first_downloaded_chapter_image() -> tuple[str, str] | None:
    chapters_dir = BOOK_DIR / "chapters"
    if not chapters_dir.is_dir():
        return None
    for chapter_dir in sorted(chapters_dir.iterdir()):
        if not chapter_dir.is_dir():
            continue
        images = sorted((chapter_dir / "images").glob("*.jpg"))
        if images:
            relative = images[0].relative_to(BOOK_DIR).as_posix()
            return chapter_dir.name.split("_", 1)[0], f"{R2_PREFIX}/{relative}"
    return None


def test_upload_r2_skips_remote_existing_objects(tmp_path):
    existing = first_downloaded_chapter_image()
    if existing is None:
        pytest.skip("downloaded chapter images are required for this script integration test")
    chapter_prefix, existing_key = existing

    log_path = tmp_path / "npx.log"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_npx = fake_bin / "npx"
    fake_npx.write_text(
        """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$NPX_LOG"
if [[ "$*" == *" r2 object head "* ]]; then
  if [[ "$*" == *"$EXISTING_KEY"* ]]; then
    exit 0
  fi
  exit 1
fi
exit 0
""",
        encoding="utf-8",
    )
    fake_npx.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["NPX_LOG"] = str(log_path)
    env["EXISTING_KEY"] = existing_key
    env["R2_UPLOAD_CONCURRENCY"] = "1"

    subprocess.run(
        ["./scripts/upload_r2.sh", "--chapter-prefix", chapter_prefix],
        cwd=PROJECT_DIR,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    calls = log_path.read_text(encoding="utf-8").splitlines()
    assert any(" r2 object head " in call and existing_key in call for call in calls)
    assert not any(" r2 object put " in call and existing_key in call for call in calls)


def test_publish_cloudflare_passes_force_assets_to_upload_script():
    result = subprocess.run(
        ["./scripts/publish_cloudflare.sh", "--skip-crawl", "--skip-pages", "--force-assets", "--dry-run"],
        cwd=PROJECT_DIR,
        check=True,
        capture_output=True,
    )

    assert "./scripts/upload_r2.sh --force" in result.stdout.decode("utf-8", errors="replace")

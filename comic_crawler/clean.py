from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CleanupTarget:
    path: Path
    kind: str
    exists: bool


def plan_cleanup(config: dict[str, Any], project_dir: Path) -> list[CleanupTarget]:
    storage = config.get("storage", {})
    output_dir = resolve_project_path(project_dir, storage.get("output_dir", "downloads"))
    database = resolve_project_path(project_dir, storage.get("database", "data/crawler.sqlite3"))

    targets = [
        CleanupTarget(path=output_dir, kind="directory", exists=output_dir.exists()),
        CleanupTarget(path=database, kind="file", exists=database.exists()),
    ]
    data_dir = database.parent
    if data_dir != project_dir and data_dir.exists() and not is_same_or_child(output_dir, data_dir):
        targets.append(CleanupTarget(path=data_dir, kind="empty_directory", exists=True))
    return targets


def clean_local_data(config: dict[str, Any], project_dir: Path) -> list[Path]:
    removed: list[Path] = []
    for target in plan_cleanup(config, project_dir):
        path = target.path
        ensure_inside_project(project_dir, path)
        if not path.exists():
            continue

        if target.kind == "directory":
            shutil.rmtree(path)
            removed.append(path)
        elif target.kind == "file":
            path.unlink()
            removed.append(path)
        elif target.kind == "empty_directory":
            try:
                path.rmdir()
            except OSError:
                pass
            else:
                removed.append(path)
    return removed


def resolve_project_path(project_dir: Path, value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = project_dir / path
    return path.resolve()


def ensure_inside_project(project_dir: Path, path: Path) -> None:
    project_root = project_dir.resolve()
    resolved = path.resolve()
    if resolved == project_root:
        raise ValueError("Refusing to clean the project root directory")
    if not is_same_or_child(project_root, resolved):
        raise ValueError(f"Refusing to clean path outside project: {resolved}")


def is_same_or_child(parent: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True

from __future__ import annotations

import argparse
from pathlib import Path

from comic_crawler.clean import clean_local_data, plan_cleanup
from comic_crawler.config import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean local crawler data.")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the paths that would be removed without deleting them.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm deletion of local crawler data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_dir = Path(__file__).resolve().parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = project_dir / config_path

    config = load_config(config_path)
    targets = plan_cleanup(config=config, project_dir=project_dir)

    print("Local crawler data targets:")
    for target in targets:
        status = "exists" if target.exists else "missing"
        print(f"- [{status}] {target.path}")

    if args.dry_run:
        print("Dry run only. Nothing was deleted.")
        return

    if not args.yes:
        raise SystemExit("Refusing to delete data without --yes. Use --dry-run to preview.")

    removed = clean_local_data(config=config, project_dir=project_dir)
    if removed:
        print("Removed:")
        for path in removed:
            print(f"- {path}")
    else:
        print("No local crawler data found to remove.")


if __name__ == "__main__":
    main()

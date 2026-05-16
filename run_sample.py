from __future__ import annotations

import argparse
from pathlib import Path

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from comic_crawler.config import load_config
from comic_crawler.spiders.ququ_book import QuquBookSpider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the sample comic crawler.")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML.")
    parser.add_argument("--max-chapters", type=int, help="Override crawl.max_chapters.")
    parser.add_argument("--url", help="Override target.url.")
    parser.add_argument(
        "--chapter-order",
        choices=["asc", "desc"],
        help="Override crawl.chapter_order.",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Parse metadata only; do not download images.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_dir = Path(__file__).resolve().parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = project_dir / config_path

    config = load_config(config_path)
    if args.max_chapters is not None:
        config["crawl"]["max_chapters"] = args.max_chapters
    if args.url:
        config["target"]["url"] = args.url
    if args.chapter_order:
        config["crawl"]["chapter_order"] = args.chapter_order
    if args.no_images:
        config["crawl"]["download_images"] = False

    settings = get_project_settings()
    request_config = config.get("request", {})
    settings.set("ROBOTSTXT_OBEY", bool(request_config.get("obey_robots_txt", True)))
    settings.set(
        "CONCURRENT_REQUESTS_PER_DOMAIN",
        int(request_config.get("concurrent_requests_per_domain", 1)),
    )
    settings.set("DOWNLOAD_DELAY", float(request_config.get("download_delay", 2)))
    settings.set("DOWNLOAD_TIMEOUT", int(request_config.get("timeout", 20)))
    settings.set("CRAWLER_CONFIG", config)
    settings.set("CRAWLER_CONFIG_PATH", str(config_path))

    process = CrawlerProcess(settings)
    process.crawl(QuquBookSpider)
    process.start()


if __name__ == "__main__":
    main()

from __future__ import annotations

BOT_NAME = "comic_crawler"

SPIDER_MODULES = ["comic_crawler.spiders"]
NEWSPIDER_MODULE = "comic_crawler.spiders"

ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 2
DOWNLOAD_TIMEOUT = 20

USER_AGENT = (
    "comic-crawler-learning/1.0 "
    "(local study project; obeys robots.txt; low request rate)"
)

ITEM_PIPELINES = {
    "comic_crawler.pipelines.MetadataAndImagePipeline": 300,
}

LOG_LEVEL = "INFO"
FEED_EXPORT_ENCODING = "utf-8"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
TELNETCONSOLE_ENABLED = False

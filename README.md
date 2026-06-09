# Comic Crawler

一个用于学习爬虫完整流程的 Python/Scrapy 示例项目。示例入口是：

```text
https://www.ququmh.top/book/3137
```

项目默认只按倒序抓取最新 20 个章节，遵守 `robots.txt`，低并发、低频率请求，不包含登录、验证码、Cloudflare 挑战绕过或反爬规避逻辑。请仅用于本地学习实践，不要公开分发或商业使用抓取的图片资源。

## 安装

```bash
cd /Users/echo/Documents/视频工具/comic_crawler
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置

默认配置在 `config.yaml`：

```yaml
target:
  url: "https://www.ququmh.top/book/3137"

crawl:
  chapter_order: "desc"
  max_chapters: 20
  download_images: true

storage:
  output_dir: "downloads"
  database: "data/crawler.sqlite3"

request:
  obey_robots_txt: true
  concurrent_requests_per_domain: 1
  download_delay: 2
  timeout: 20
```

## 运行

```bash
python run_sample.py --config config.yaml
```

临时覆盖章节数量：

```bash
python run_sample.py --config config.yaml --max-chapters 5
```

只解析元数据，不下载图片：

```bash
python run_sample.py --config config.yaml --no-images
```

## 清理本地数据

正常爬取不会清理已有资源。需要重新开始时，先预览会删除哪些本地数据：

```bash
python clean_data.py --config config.yaml --dry-run
```

确认删除 `storage.output_dir` 和 `storage.database`：

```bash
python clean_data.py --config config.yaml --yes
```

## 本地预览图片

启动本地预览网站：

```bash
python viewer_server.py --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

默认预览目录：

```text
downloads/ququmh.top/book_3137_一人之下/chapters
```

也可以指定目录：

```bash
python viewer_server.py \
  --chapters-dir "/Users/echo/Documents/视频工具/comic_crawler/downloads/ququmh.top/book_3137_一人之下/chapters" \
  --port 8000
```

## 输出结构

图片和 JSON 元数据会按网站结构保存：

```text
downloads/
  ququmh.top/
    book_3137_一人之下/
      book.json
      cover/
        cover.jpg
      chapters/
        0762_chapter_1102431_762 苦主/
          chapter.json
          images/
            0001.jpg
```

SQLite 数据库默认保存到：

```text
data/crawler.sqlite3
```

## 测试

```bash
pytest
```

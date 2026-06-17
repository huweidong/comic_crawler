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
  mode: "full"
  stop_on_existing_chapter: true
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

只抓取最新增量章节：

```bash
python run_sample.py --config config.yaml --incremental
```

增量模式会从最新章节开始倒序检查；遇到第一个本地已经完整下载的章节后停止调度。判断“完整”的依据是该章节存在 `chapter.json`，且 `images/` 下已有图片数量不少于 `chapter.json` 里的 `image_count`。

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

### 快速脚本

启动爬虫：

```bash
./start_crawler.sh
```

启动预览服务（后台运行）：

```bash
./start_viewer.sh
```

关闭预览服务：

```bash
./stop_viewer.sh
```

预览服务日志保存在：

```text
logs/viewer.log
```

启动本地预览网站：

```bash
python viewer_server.py --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

同一 Wi-Fi 下手机访问时，推荐用系统 Python 启动，避免 Homebrew/虚拟环境 Python 被 macOS 防火墙识别拦截：

```bash
/usr/bin/python3 viewer_server.py --host 0.0.0.0 --port 8000
```

然后在电脑或手机浏览器打开电脑的局域网地址，例如：

```text
http://192.168.10.16:8000
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

## Cloudflare 在线发布

项目支持把本地爬取后的资源发布到 Cloudflare R2，并把预览网站发布到 Cloudflare Pages。

### 准备 Cloudflare API

复制环境变量模板：

```bash
cp .env.cloudflare.example .env.cloudflare
```

然后编辑 `.env.cloudflare`：

```bash
CLOUDFLARE_ACCOUNT_ID="填你的 Account ID"
CLOUDFLARE_API_TOKEN="填你的 Cloudflare API Token"
R2_BUCKET="comic-crawler-assets"
PAGES_PROJECT="comic-crawler"
```

`.env.cloudflare` 已加入 `.gitignore`，不要提交到 GitHub。

Cloudflare API Token 至少需要：

```text
Account - Workers R2 Storage - Edit
Account - Cloudflare Pages - Edit
```

### 准备 Cloudflare 资源

安装 Node 依赖：

```bash
npm install
```

创建 R2 bucket：

```bash
npx wrangler r2 bucket create comic-crawler-assets
```

Cloudflare Pages 项目建议：

```text
Project name: comic-crawler
Build command: npm run build
Build output directory: dist
```

Pages Functions 需要绑定 R2：

```text
Variable name: COMIC_ASSETS
Bucket: comic-crawler-assets
```

### 一键发布

默认串联本地爬取、生成 manifest、上传 R2、构建网页、发布 Pages：

```bash
./scripts/publish_cloudflare.sh
```

只发布已有本地资源，不重新爬取：

```bash
./scripts/publish_cloudflare.sh --skip-crawl
```

临时覆盖章节数量：

```bash
./scripts/publish_cloudflare.sh --max-chapters 5
```

增量爬取并发布：

```bash
./scripts/publish_cloudflare.sh --incremental
```

增量发布会执行：

```text
1. 倒序扫描最新章节，遇到第一个本地完整章节后停止
2. 重新生成 manifest.json
3. 只上传最新 N 个本地章节到 R2，N 来自 --max-chapters 或 config.yaml
4. 重新构建并发布 Pages
```

R2 上传会先检查远端对象是否已经存在；已存在的 `chapter.json` 和图片会跳过，不重复上传。`manifest.json` 仍会每次上传，用来刷新章节索引。

如果确实需要强制覆盖 R2 里的资源：

```bash
./scripts/publish_cloudflare.sh --incremental --max-chapters 5 --force-assets
```

只预演命令，不执行发布：

```bash
./scripts/publish_cloudflare.sh --dry-run
```

常用拆分命令：

```bash
python scripts/build_manifest.py
./scripts/upload_r2.sh
npm run build
npx wrangler pages deploy dist --project-name comic-crawler
```

上传图片较多时可以提高并发：

```bash
R2_UPLOAD_CONCURRENCY=12 ./scripts/upload_r2.sh
```

如果网络中断，可以只补传指定章节前缀：

```bash
./scripts/upload_r2.sh --chapter-prefix 0764 --chapter-prefix 0765
```

也可以只上传本地最新 N 个章节：

```bash
./scripts/upload_r2.sh --latest 5
```

上传脚本默认也会跳过 R2 上已经存在的对象；需要强制覆盖时：

```bash
./scripts/upload_r2.sh --latest 5 --force
```

发布成功后打开：

```text
https://comic-crawler.pages.dev
```

## 测试

```bash
pytest
npm run build
```

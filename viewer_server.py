from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from comic_crawler.viewer import (
    chapter_payload,
    content_type,
    media_path,
    scan_chapters,
)


DEFAULT_CHAPTERS_DIR = (
    Path(__file__).resolve().parent
    / "downloads"
    / "ququmh.top"
    / "book_3137_一人之下"
    / "chapters"
)


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>漫画图片预览</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f8;
      --panel: #ffffff;
      --line: #d9dee3;
      --text: #20252b;
      --muted: #66717d;
      --accent: #0b6fcb;
      --accent-soft: #e5f2ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      background: var(--bg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .app {
      display: grid;
      grid-template-columns: 320px 1fr;
      min-height: 100vh;
    }
    .sidebar {
      border-right: 1px solid var(--line);
      background: var(--panel);
      min-width: 0;
      display: flex;
      flex-direction: column;
    }
    .side-head {
      padding: 16px;
      border-bottom: 1px solid var(--line);
    }
    h1 {
      font-size: 18px;
      margin: 0 0 10px;
      line-height: 1.3;
    }
    .chapter-count {
      font-size: 13px;
      color: var(--muted);
    }
    .chapter-list {
      overflow: auto;
      padding: 8px;
    }
    .chapter-button {
      width: 100%;
      display: grid;
      grid-template-columns: 54px 1fr auto;
      gap: 8px;
      align-items: center;
      border: 0;
      border-radius: 8px;
      background: transparent;
      padding: 10px 8px;
      text-align: left;
      color: var(--text);
      cursor: pointer;
      font: inherit;
    }
    .chapter-button:hover { background: #f0f3f5; }
    .chapter-button.active {
      background: var(--accent-soft);
      color: #064f91;
      font-weight: 600;
    }
    .chapter-index {
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }
    .chapter-title {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .image-badge {
      color: var(--muted);
      font-size: 12px;
      font-variant-numeric: tabular-nums;
    }
    .main {
      min-width: 0;
      display: flex;
      flex-direction: column;
    }
    .toolbar {
      position: sticky;
      top: 0;
      z-index: 2;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(10px);
    }
    .toolbar-title {
      min-width: 0;
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 700;
    }
    button, select {
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      color: var(--text);
      padding: 0 10px;
      font: inherit;
      cursor: pointer;
    }
    button:hover, select:hover { border-color: #aeb8c2; }
    button:disabled {
      color: #a0a9b2;
      cursor: not-allowed;
      background: #f4f5f6;
    }
    .reader {
      width: min(1100px, 100%);
      margin: 0 auto;
      padding: 18px 16px 48px;
    }
    .reader.thumb {
      width: min(1280px, 100%);
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 12px;
      align-items: start;
    }
    .page {
      display: block;
      width: 100%;
      max-width: 1000px;
      margin: 0 auto 12px;
      background: #e9edf1;
      border: 1px solid var(--line);
    }
    .reader.thumb .page {
      margin: 0;
      max-height: 360px;
      object-fit: contain;
    }
    .empty {
      padding: 56px 18px;
      color: var(--muted);
      text-align: center;
    }
    @media (max-width: 760px) {
      .app { grid-template-columns: 1fr; }
      .sidebar {
        max-height: 38vh;
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }
      .toolbar {
        flex-wrap: wrap;
      }
      .toolbar-title {
        flex-basis: 100%;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="side-head">
        <h1>一人之下</h1>
        <div class="chapter-count" id="chapterCount">正在加载章节...</div>
      </div>
      <div class="chapter-list" id="chapterList"></div>
    </aside>
    <main class="main">
      <div class="toolbar">
        <div class="toolbar-title" id="currentTitle">请选择章节</div>
        <button id="refreshButton" type="button">刷新</button>
        <button id="prevButton" type="button">上一章</button>
        <button id="nextButton" type="button">下一章</button>
        <select id="orderSelect" aria-label="章节排序">
          <option value="desc">倒序</option>
          <option value="asc">正序</option>
        </select>
        <select id="viewSelect" aria-label="阅读模式">
          <option value="reader">阅读</option>
          <option value="thumb">缩略图</option>
        </select>
      </div>
      <section class="reader" id="reader"></section>
    </main>
  </div>
  <script>
    const state = {
      chapters: [],
      current: null,
      order: new URLSearchParams(location.search).get("order") || "desc",
      view: localStorage.getItem("viewer:view") || "reader",
    };

    const chapterList = document.getElementById("chapterList");
    const chapterCount = document.getElementById("chapterCount");
    const currentTitle = document.getElementById("currentTitle");
    const reader = document.getElementById("reader");
    const orderSelect = document.getElementById("orderSelect");
    const viewSelect = document.getElementById("viewSelect");
    const prevButton = document.getElementById("prevButton");
    const nextButton = document.getElementById("nextButton");
    const refreshButton = document.getElementById("refreshButton");

    orderSelect.value = state.order === "asc" ? "asc" : "desc";
    viewSelect.value = state.view === "thumb" ? "thumb" : "reader";

    orderSelect.addEventListener("change", async () => {
      state.order = orderSelect.value;
      await loadChapters({ keepCurrent: true });
    });
    viewSelect.addEventListener("change", () => {
      state.view = viewSelect.value;
      localStorage.setItem("viewer:view", state.view);
      renderReaderMode();
    });
    refreshButton.addEventListener("click", () => loadChapters({ keepCurrent: true }));
    prevButton.addEventListener("click", () => moveChapter(-1));
    nextButton.addEventListener("click", () => moveChapter(1));

    async function loadChapters(options = {}) {
      chapterCount.textContent = "正在加载章节...";
      const res = await fetch(`/api/chapters?order=${encodeURIComponent(state.order)}`);
      const payload = await res.json();
      state.chapters = payload.chapters || [];
      chapterCount.textContent = `${state.chapters.length} 个章节`;
      renderChapterList();

      const params = new URLSearchParams(location.search);
      const requested = options.keepCurrent && state.current
        ? state.current.name
        : params.get("chapter");
      const fallback = state.chapters[0] && state.chapters[0].name;
      const nextName = state.chapters.some((item) => item.name === requested)
        ? requested
        : fallback;

      if (nextName) {
        await selectChapter(nextName, { scrollList: false });
      } else {
        state.current = null;
        currentTitle.textContent = "没有可预览的章节";
        reader.innerHTML = `<div class="empty">没有找到章节图片。</div>`;
        updateButtons();
        syncUrl();
      }
    }

    function renderChapterList() {
      chapterList.innerHTML = "";
      for (const chapter of state.chapters) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "chapter-button";
        button.dataset.name = chapter.name;
        button.innerHTML = `
          <span class="chapter-index">${String(chapter.index).padStart(4, "0")}</span>
          <span class="chapter-title" title="${escapeHtml(chapter.title)}">${escapeHtml(chapter.title)}</span>
          <span class="image-badge">${chapter.image_count}</span>
        `;
        button.addEventListener("click", () => selectChapter(chapter.name));
        chapterList.appendChild(button);
      }
      highlightCurrentChapter();
    }

    async function selectChapter(name, options = {}) {
      const res = await fetch(`/api/chapter?name=${encodeURIComponent(name)}`);
      if (!res.ok) {
        reader.innerHTML = `<div class="empty">章节加载失败。</div>`;
        return;
      }
      state.current = await res.json();
      currentTitle.textContent = `${String(state.current.index).padStart(4, "0")} ${state.current.title}`;
      renderImages();
      highlightCurrentChapter();
      updateButtons();
      syncUrl();
      if (options.scrollList !== false) {
        document.querySelector(".chapter-button.active")?.scrollIntoView({ block: "nearest" });
      }
    }

    function renderImages() {
      renderReaderMode();
      if (!state.current.images.length) {
        reader.innerHTML = `<div class="empty">这一章没有图片。</div>`;
        return;
      }
      reader.innerHTML = "";
      for (const image of state.current.images) {
        const img = document.createElement("img");
        img.className = "page";
        img.src = image.url;
        img.alt = image.name;
        img.loading = "lazy";
        reader.appendChild(img);
      }
    }

    function renderReaderMode() {
      reader.className = `reader ${state.view === "thumb" ? "thumb" : ""}`.trim();
    }

    function highlightCurrentChapter() {
      for (const button of document.querySelectorAll(".chapter-button")) {
        button.classList.toggle("active", state.current && button.dataset.name === state.current.name);
      }
    }

    function updateButtons() {
      const index = state.chapters.findIndex((chapter) => state.current && chapter.name === state.current.name);
      prevButton.disabled = index <= 0;
      nextButton.disabled = index < 0 || index >= state.chapters.length - 1;
    }

    function moveChapter(delta) {
      const index = state.chapters.findIndex((chapter) => state.current && chapter.name === state.current.name);
      const next = state.chapters[index + delta];
      if (next) selectChapter(next.name);
    }

    function syncUrl() {
      const params = new URLSearchParams();
      params.set("order", state.order);
      if (state.current) params.set("chapter", state.current.name);
      history.replaceState(null, "", `/?${params.toString()}`);
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }

    loadChapters().catch((error) => {
      console.error(error);
      chapterCount.textContent = "加载失败";
      reader.innerHTML = `<div class="empty">预览服务返回异常。</div>`;
    });
  </script>
</body>
</html>
"""


class ViewerHandler(BaseHTTPRequestHandler):
    chapters_dir: Path

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self.send_bytes(INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif parsed.path == "/api/chapters":
                self.handle_chapters(parsed.query)
            elif parsed.path == "/api/chapter":
                self.handle_chapter(parsed.query)
            elif parsed.path.startswith("/media/"):
                self.handle_media(parsed.path)
            else:
                self.send_error(404, "Not Found")
        except ValueError:
            self.send_error(400, "Bad Request")
        except FileNotFoundError:
            self.send_error(404, "Not Found")

    def log_message(self, format: str, *args) -> None:
        return

    def handle_chapters(self, query: str) -> None:
        params = parse_qs(query)
        order = params.get("order", ["desc"])[0]
        chapters = [chapter.to_dict() for chapter in scan_chapters(self.chapters_dir, order)]
        self.send_json({"chapters": chapters})

    def handle_chapter(self, query: str) -> None:
        params = parse_qs(query)
        name = params.get("name", [""])[0]
        payload = chapter_payload(self.chapters_dir, name)
        if payload is None:
            self.send_error(404, "Chapter not found")
            return
        self.send_json(payload)

    def handle_media(self, path: str) -> None:
        parts = path.split("/")
        if len(parts) != 5 or parts[3] != "images":
            self.send_error(404, "Not Found")
            return
        chapter_name = unquote(parts[2])
        image_name = unquote(parts[4])
        image_path = media_path(self.chapters_dir, chapter_name, image_name)
        self.send_bytes(image_path.read_bytes(), content_type(image_path))

    def send_json(self, payload: object) -> None:
        self.send_bytes(
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def send_bytes(self, body: bytes, mime_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview downloaded comic images locally.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=8000, help="Bind port.")
    parser.add_argument(
        "--chapters-dir",
        default=str(DEFAULT_CHAPTERS_DIR),
        help="Downloaded chapters directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    chapters_dir = Path(args.chapters_dir).expanduser().resolve()
    handler = type("ConfiguredViewerHandler", (ViewerHandler,), {"chapters_dir": chapters_dir})
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Previewing: {chapters_dir}")
    print(f"Open: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

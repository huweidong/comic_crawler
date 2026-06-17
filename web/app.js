const state = {
  chapters: [],
  current: null,
  order: new URLSearchParams(location.search).get("order") || "desc",
  view: localStorage.getItem("viewer:view") || "reader",
};

const bookTitle = document.getElementById("bookTitle");
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
  if (!res.ok) throw new Error(`chapters failed: ${res.status}`);

  const payload = await res.json();
  state.chapters = payload.chapters || [];
  bookTitle.textContent = payload.book?.title || "漫画图片预览";
  chapterCount.textContent = `${state.chapters.length} 个章节`;
  renderChapterList();

  const params = new URLSearchParams(location.search);
  const requested = options.keepCurrent && state.current ? state.current.name : params.get("chapter");
  const fallback = state.chapters[0] && state.chapters[0].name;
  const nextName = state.chapters.some((item) => item.name === requested) ? requested : fallback;

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

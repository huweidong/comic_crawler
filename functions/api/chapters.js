const MANIFEST_KEY = "ququmh.top/book_3137_一人之下/manifest.json";

export async function onRequestGet(context) {
  const manifest = await readManifest(context.env);
  if (!manifest) {
    return json({ book: { title: "漫画图片预览" }, chapters: [] }, 200);
  }

  const url = new URL(context.request.url);
  const order = url.searchParams.get("order") === "asc" ? "asc" : "desc";
  const chapters = [...(manifest.chapters || [])].sort((a, b) => {
    const diff = Number(a.index || 0) - Number(b.index || 0);
    if (diff !== 0) return order === "asc" ? diff : -diff;
    return String(a.name || "").localeCompare(String(b.name || ""), "zh-CN", { numeric: true });
  });

  return json({
    book: manifest.book || { title: "漫画图片预览" },
    chapters: chapters.map((chapter) => ({
      name: chapter.name,
      title: chapter.title,
      chapter_id: chapter.chapter_id,
      index: chapter.index,
      image_count: chapter.image_count,
    })),
  });
}

async function readManifest(env) {
  const object = await env.COMIC_ASSETS.get(MANIFEST_KEY);
  return object ? object.json() : null;
}

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "public, max-age=60",
    },
  });
}

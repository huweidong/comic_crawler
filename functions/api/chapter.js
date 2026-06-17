const MANIFEST_KEY = "ququmh.top/book_3137_一人之下/manifest.json";

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const name = url.searchParams.get("name") || "";
  if (!isSafeName(name)) {
    return json({ error: "Bad chapter name" }, 400);
  }

  const object = await context.env.COMIC_ASSETS.get(MANIFEST_KEY);
  if (!object) {
    return json({ error: "Manifest not found" }, 404);
  }

  const manifest = await object.json();
  const chapter = (manifest.chapters || []).find((item) => item.name === name);
  if (!chapter) {
    return json({ error: "Chapter not found" }, 404);
  }

  return json({
    name: chapter.name,
    title: chapter.title,
    chapter_id: chapter.chapter_id,
    index: chapter.index,
    image_count: chapter.image_count,
    images: chapter.images || [],
  });
}

function isSafeName(value) {
  return Boolean(value) && !value.includes("/") && !value.includes("\\") && !value.includes("..");
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

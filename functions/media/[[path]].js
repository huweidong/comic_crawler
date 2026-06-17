const R2_PREFIX = "ququmh.top/book_3137_一人之下";
const IMAGE_EXTENSIONS = new Set(["jpg", "jpeg", "png", "webp", "gif"]);

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const relativePath = url.pathname.replace(/^\/media\/?/, "");
  const parts = relativePath.split("/");

  if (parts.length !== 3 || parts[1] !== "images") {
    return new Response("Not found", { status: 404 });
  }

  const chapterName = decodeURIComponent(parts[0]);
  const imageName = decodeURIComponent(parts[2]);
  if (!isSafeName(chapterName) || !isSafeName(imageName) || !isImage(imageName)) {
    return new Response("Bad request", { status: 400 });
  }

  const key = `${R2_PREFIX}/chapters/${chapterName}/images/${imageName}`;
  const object = await context.env.COMIC_ASSETS.get(key);
  if (!object) {
    return new Response("Not found", { status: 404 });
  }

  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set("etag", object.httpEtag);
  headers.set("cache-control", "public, max-age=31536000, immutable");
  if (!headers.has("content-type")) {
    headers.set("content-type", contentType(imageName));
  }

  return new Response(object.body, { headers });
}

function isSafeName(value) {
  return Boolean(value) && !value.includes("/") && !value.includes("\\") && !value.includes("..");
}

function isImage(value) {
  const extension = value.split(".").pop()?.toLowerCase();
  return IMAGE_EXTENSIONS.has(extension || "");
}

function contentType(value) {
  const extension = value.split(".").pop()?.toLowerCase();
  return {
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    png: "image/png",
    webp: "image/webp",
    gif: "image/gif",
  }[extension || ""] || "application/octet-stream";
}

import { cp, mkdir, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const distDir = resolve(root, "dist");
const webDir = resolve(root, "web");

await rm(distDir, { force: true, recursive: true });
await mkdir(distDir, { recursive: true });
await cp(webDir, distDir, { recursive: true });

console.log(`Built Cloudflare Pages assets into ${distDir}`);

#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env.cloudflare"
BOOK_DIR="$PROJECT_DIR/downloads/ququmh.top/book_3137_一人之下"
R2_PREFIX="ququmh.top/book_3137_一人之下"
DRY_RUN=0
FORCE_UPLOAD=0
UPLOAD_CONCURRENCY="${R2_UPLOAD_CONCURRENCY:-4}"
CHAPTER_PREFIXES=()
LATEST_COUNT=""

usage() {
  cat <<'USAGE'
Usage: ./scripts/upload_r2.sh [--dry-run] [--force] [--chapter-prefix 0764] [--latest N]

Uploads manifest.json, chapter.json files, and images to Cloudflare R2.
Requires .env.cloudflare with CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, and R2_BUCKET.

Options:
  --chapter-prefix P    Upload only chapters whose directory starts with P. Can repeat.
  --latest N           Upload only the latest N local chapter directories.
  --force              Upload files even when the R2 object already exists.
  --dry-run            Print upload commands without running them.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --force)
      FORCE_UPLOAD=1
      shift
      ;;
    --chapter-prefix)
      if [[ -z "${2:-}" ]]; then
        echo "--chapter-prefix requires a value such as 0764." >&2
        exit 1
      fi
      CHAPTER_PREFIXES+=("$2")
      shift 2
      ;;
    --latest)
      LATEST_COUNT="${2:-}"
      if [[ -z "$LATEST_COUNT" || ! "$LATEST_COUNT" =~ ^[0-9]+$ || "$LATEST_COUNT" -lt 1 ]]; then
        echo "--latest requires a positive number." >&2
        exit 1
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$ENV_FILE" && "$DRY_RUN" -eq 0 ]]; then
  echo "Missing $ENV_FILE. Copy .env.cloudflare.example and fill in your Cloudflare values." >&2
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-dry-run-account}"
  CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-dry-run-token}"
  R2_BUCKET="${R2_BUCKET:-comic-crawler-assets}"
fi

: "${CLOUDFLARE_ACCOUNT_ID:?Missing CLOUDFLARE_ACCOUNT_ID in .env.cloudflare}"
: "${CLOUDFLARE_API_TOKEN:?Missing CLOUDFLARE_API_TOKEN in .env.cloudflare}"
: "${R2_BUCKET:?Missing R2_BUCKET in .env.cloudflare}"

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '+'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

reject_placeholder() {
  local name="$1"
  local value="$2"
  if [[ "$DRY_RUN" -eq 0 && "$value" == *"填你的"* ]]; then
    echo "$name still contains the placeholder text. Please edit .env.cloudflare first." >&2
    exit 1
  fi
}

cd "$PROJECT_DIR"

reject_placeholder "CLOUDFLARE_ACCOUNT_ID" "$CLOUDFLARE_ACCOUNT_ID"
reject_placeholder "CLOUDFLARE_API_TOKEN" "$CLOUDFLARE_API_TOKEN"

if [[ ! -f "$BOOK_DIR/manifest.json" && "$DRY_RUN" -eq 0 ]]; then
  echo "Missing manifest.json. Run: python scripts/build_manifest.py" >&2
  exit 1
fi

run npx wrangler r2 object put "$R2_BUCKET/$R2_PREFIX/manifest.json" \
  --remote \
  --file "$BOOK_DIR/manifest.json" \
  --content-type "application/json; charset=utf-8"

if [[ ! -d "$BOOK_DIR/chapters" && "$DRY_RUN" -eq 1 ]]; then
  echo "Dry run: chapters directory not found, skipping per-file upload listing."
  echo "R2 upload complete."
  exit 0
fi

upload_one() {
  local file="$1"
  local relative="${file#$BOOK_DIR/}"
  local key="$R2_PREFIX/$relative"
  local content_type="application/octet-stream"
  case "${file##*.}" in
    json) content_type="application/json; charset=utf-8" ;;
    jpg|jpeg) content_type="image/jpeg" ;;
    png) content_type="image/png" ;;
    webp) content_type="image/webp" ;;
    gif) content_type="image/gif" ;;
  esac

  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '+ npx wrangler r2 object put %q --remote --file %q --content-type %q\n' \
      "$R2_BUCKET/$key" "$file" "$content_type"
  else
    if [[ "$FORCE_UPLOAD" -eq 0 ]] && remote_object_exists "$key"; then
      echo "Skip existing R2 object: $relative"
      return 0
    fi

    local attempt
    for attempt in 1 2 3; do
      if npx wrangler r2 object put "$R2_BUCKET/$key" \
        --remote \
        --file "$file" \
        --content-type "$content_type"; then
        return 0
      fi
      echo "Upload failed for $relative (attempt $attempt/3)." >&2
      sleep "$attempt"
    done
    return 1
  fi
}

remote_object_exists() {
  local key="$1"
  npx wrangler r2 object head "$R2_BUCKET/$key" --remote >/dev/null 2>&1
}

list_upload_files() {
  local prefix
  local chapter_dir
  if [[ "${#CHAPTER_PREFIXES[@]}" -gt 0 ]]; then
    for prefix in "${CHAPTER_PREFIXES[@]}"; do
      while IFS= read -r -d '' chapter_dir; do
        find "$chapter_dir" -type f \( -name 'chapter.json' -o -path '*/images/*' \) -print0
      done < <(find "$BOOK_DIR/chapters" -maxdepth 1 -type d -name "${prefix}_*" -print0)
    done
    return
  fi

  if [[ -n "$LATEST_COUNT" ]]; then
    local count=0
    while IFS= read -r -d '' chapter_dir; do
      find "$chapter_dir" -type f \( -name 'chapter.json' -o -path '*/images/*' \) -print0
      count=$((count + 1))
      if [[ "$count" -ge "$LATEST_COUNT" ]]; then
        break
      fi
    done < <(
      find "$BOOK_DIR/chapters" -maxdepth 1 -type d -name '[0-9][0-9][0-9][0-9]_*' -print0 \
        | sort -zr
    )
    return
  fi

  find "$BOOK_DIR/chapters" -type f \( -name 'chapter.json' -o -path '*/images/*' \) -print0
}

export BOOK_DIR R2_PREFIX R2_BUCKET DRY_RUN FORCE_UPLOAD
export -f upload_one remote_object_exists

list_upload_files \
  | sort -z \
  | xargs -0 -n 1 -P "$UPLOAD_CONCURRENCY" bash -c 'upload_one "$1"' _

echo "R2 upload complete."

#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env.cloudflare"
if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi
SKIP_CRAWL=0
SKIP_ASSETS=0
SKIP_PAGES=0
DRY_RUN=0
INCREMENTAL=0
FORCE_ASSETS=0
MAX_CHAPTERS=""

usage() {
  cat <<'USAGE'
Usage: ./scripts/publish_cloudflare.sh [options]

Options:
  --skip-crawl          Use existing local downloads.
  --skip-assets         Skip manifest generation and R2 upload.
  --skip-pages          Skip Cloudflare Pages deployment.
  --incremental         Crawl only newer/incomplete chapters and upload latest crawled range.
  --force-assets        Re-upload R2 assets even when the object already exists.
  --max-chapters N      Override crawler chapter count.
  --dry-run             Print commands without running them.
  -h, --help            Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-crawl)
      SKIP_CRAWL=1
      shift
      ;;
    --skip-assets)
      SKIP_ASSETS=1
      shift
      ;;
    --skip-pages)
      SKIP_PAGES=1
      shift
      ;;
    --incremental)
      INCREMENTAL=1
      shift
      ;;
    --force-assets)
      FORCE_ASSETS=1
      shift
      ;;
    --max-chapters)
      MAX_CHAPTERS="${2:-}"
      if [[ -z "$MAX_CHAPTERS" ]]; then
        echo "--max-chapters requires a number." >&2
        exit 1
      fi
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
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
  PAGES_PROJECT="${PAGES_PROJECT:-comic-crawler}"
fi

: "${CLOUDFLARE_ACCOUNT_ID:?Missing CLOUDFLARE_ACCOUNT_ID in .env.cloudflare}"
: "${CLOUDFLARE_API_TOKEN:?Missing CLOUDFLARE_API_TOKEN in .env.cloudflare}"
: "${R2_BUCKET:?Missing R2_BUCKET in .env.cloudflare}"
: "${PAGES_PROJECT:?Missing PAGES_PROJECT in .env.cloudflare}"

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '+'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

configured_max_chapters() {
  "$PYTHON_BIN" -c 'from comic_crawler.config import load_config; print(load_config("config.yaml")["crawl"]["max_chapters"])'
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

if [[ "$SKIP_CRAWL" -eq 0 ]]; then
  crawl_cmd=("$PYTHON_BIN" run_sample.py --config config.yaml)
  if [[ -n "$MAX_CHAPTERS" ]]; then
    crawl_cmd+=(--max-chapters "$MAX_CHAPTERS")
  fi
  if [[ "$INCREMENTAL" -eq 1 ]]; then
    crawl_cmd+=(--incremental)
  fi
  run "${crawl_cmd[@]}"
fi

if [[ "$SKIP_ASSETS" -eq 0 ]]; then
  run "$PYTHON_BIN" scripts/build_manifest.py
  upload_cmd=(./scripts/upload_r2.sh)
  if [[ "$FORCE_ASSETS" -eq 1 ]]; then
    upload_cmd+=(--force)
  fi
  if [[ "$INCREMENTAL" -eq 1 ]]; then
    latest_count="$MAX_CHAPTERS"
    if [[ -z "$latest_count" ]]; then
      latest_count="$(configured_max_chapters)"
    fi
    upload_cmd+=(--latest "$latest_count")
  fi
  run "${upload_cmd[@]}"
fi

if [[ "$SKIP_PAGES" -eq 0 ]]; then
  run npm install
  run npm run build
  run npx wrangler pages deploy dist --project-name "$PAGES_PROJECT"
fi

echo "Cloudflare publish flow complete."

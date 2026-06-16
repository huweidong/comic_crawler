#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$PROJECT_DIR/.viewer_server.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "Preview server is not running (PID file not found)."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if ! kill -0 "$PID" 2>/dev/null; then
  echo "Preview server is not running (stale PID $PID)."
  rm -f "$PID_FILE"
  exit 0
fi

kill "$PID"
for _ in {1..20}; do
  if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "Preview server stopped."
    exit 0
  fi
  sleep 0.1
done

echo "Preview server did not stop in time (PID $PID)."
exit 1

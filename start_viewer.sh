#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$PROJECT_DIR/.viewer_server.pid"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/viewer.log"
HOST="${VIEWER_HOST:-0.0.0.0}"
PORT="${VIEWER_PORT:-8000}"
PYTHON="/usr/bin/python3"
HEALTH_URL="http://127.0.0.1:$PORT/api/chapters?order=desc"

server_responds() {
  /usr/bin/curl --noproxy "*" --silent --fail --max-time 1 \
    "$HEALTH_URL" >/dev/null 2>&1
}

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null && server_responds; then
    echo "Preview server is already running (PID $PID)."
    exit 0
  fi
  rm -f "$PID_FILE"
fi

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR"

nohup "$PYTHON" viewer_server.py --host "$HOST" --port "$PORT" \
  >"$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" >"$PID_FILE"

for _ in {1..30}; do
  if server_responds; then
    break
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    break
  fi
  sleep 0.1
done

if ! server_responds; then
  echo "Preview server failed to start or did not respond on port $PORT."
  if [[ -s "$LOG_FILE" ]]; then
    echo "Log:"
    cat "$LOG_FILE"
  else
    echo "No log output was produced. Port $PORT may already be occupied."
  fi
  kill "$PID" 2>/dev/null || true
  rm -f "$PID_FILE"
  exit 1
fi

LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
echo "Preview server started (PID $PID)."
echo "Local: http://127.0.0.1:$PORT"
if [[ -n "$LAN_IP" ]]; then
  echo "LAN:   http://$LAN_IP:$PORT"
fi
echo "Log:   $LOG_FILE"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NODE_BIN="$HOME/.nvm/versions/node/v24.14.1/bin"

if [ -d "$NODE_BIN" ]; then
  export PATH="$NODE_BIN:$PATH"
fi

cd "$ROOT"

if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

# Remote OpenCode mode intentionally overrides local .env OpenCode settings.
export OPENCODE_SERVER_URL="${OPENCODE_REMOTE_SERVER_URL:-https://ryann-oceanlike-toxophily.ngrok-free.dev}"
export OPENCODE_SERVER_USERNAME="${OPENCODE_REMOTE_SERVER_USERNAME:-}"
export OPENCODE_SERVER_PASSWORD="${OPENCODE_REMOTE_SERVER_PASSWORD:-}"
export OPENCODE_PROXY_PORT="${OPENCODE_REMOTE_PROXY_PORT:-4098}"
export OPENCODE_DIRECTORY="${OPENCODE_REMOTE_DIRECTORY:-/tmp}"
export OPENCODE_NGROK_SKIP_BROWSER_WARNING="${OPENCODE_NGROK_SKIP_BROWSER_WARNING:-1}"
export OPENCODE_MODEL_PROVIDER_ID="${OPENCODE_REMOTE_MODEL_PROVIDER_ID:-${OPENCODE_MODEL_PROVIDER_ID:-openai}}"
export OPENCODE_MODEL_ID="${OPENCODE_REMOTE_MODEL_ID:-${OPENCODE_MODEL_ID:-gpt-5.2}}"

export LLM_API_KEY="${OPENCODE_REMOTE_LLM_API_KEY:-opencode-remote}"
export LLM_BASE_URL="${OPENCODE_REMOTE_LLM_BASE_URL:-http://127.0.0.1:${OPENCODE_PROXY_PORT}/v1}"
export LLM_MODEL_NAME="${OPENCODE_REMOTE_LLM_MODEL_NAME:-${OPENCODE_MODEL_ID}}"
FRONTEND_PORT="${FRONTEND_PORT:-3001}"

if [ -z "$OPENCODE_SERVER_USERNAME" ] || [ -z "$OPENCODE_SERVER_PASSWORD" ]; then
  echo "[dev:opencode-remote] missing OPENCODE_REMOTE_SERVER_USERNAME or OPENCODE_REMOTE_SERVER_PASSWORD in .env" >&2
  exit 1
fi

if [ "${OPENCODE_REMOTE_SKIP_PREFLIGHT:-0}" != "1" ] && command -v curl >/dev/null 2>&1; then
  status="$(
    curl -sS -o /dev/null -w '%{http_code}' \
      -u "${OPENCODE_SERVER_USERNAME}:${OPENCODE_SERVER_PASSWORD}" \
      -H 'ngrok-skip-browser-warning: true' \
      "${OPENCODE_SERVER_URL%/}/" || true
  )"
  if [ "$status" = "401" ]; then
    echo "[dev:opencode-remote] remote OpenCode basic auth failed for ${OPENCODE_SERVER_URL}" >&2
    echo "[dev:opencode-remote] check OPENCODE_REMOTE_SERVER_USERNAME / OPENCODE_REMOTE_SERVER_PASSWORD in .env" >&2
    exit 1
  fi
fi

echo "[dev:opencode-remote] node=$(node -v 2>/dev/null || echo missing) npm=$(npm -v 2>/dev/null || echo missing)"
echo "[dev:opencode-remote] forwarding LLM calls to remote OpenCode via local proxy on ${LLM_BASE_URL}"

pids=()

port_open() {
  python3 - "$1" "$2" <<'PY'
import socket, sys
host = sys.argv[1]
port = int(sys.argv[2])
s = socket.socket()
s.settimeout(0.5)
try:
    s.connect((host, port))
    print('open')
    sys.exit(0)
except Exception:
    sys.exit(1)
finally:
    s.close()
PY
}

run_named() {
  local name="$1"
  shift
  (
    cd "$ROOT"
    "$@" 2>&1 | sed -u "s/^/[$name] /"
  ) &
  pids+=("$!")
}

cleanup() {
  for pid in "${pids[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}

trap 'cleanup' EXIT INT TERM

if port_open 127.0.0.1 "$OPENCODE_PROXY_PORT" >/dev/null 2>&1; then
  echo "[dev:opencode-remote] reusing existing proxy on ${OPENCODE_PROXY_PORT}"
else
  run_named proxy npm run opencode:proxy
  sleep 2
fi

if port_open 127.0.0.1 5001 >/dev/null 2>&1; then
  echo "[dev:opencode-remote] reusing existing backend on 5001"
  echo "[dev:opencode-remote] existing backend must already use LLM_BASE_URL=${LLM_BASE_URL}"
else
  run_named backend npm run backend
  sleep 2
fi

if port_open 127.0.0.1 "$FRONTEND_PORT" >/dev/null 2>&1; then
  echo "[dev:opencode-remote] reusing existing frontend on ${FRONTEND_PORT}"
else
  run_named frontend npm run frontend
  sleep 2
fi

if [ "${#pids[@]}" -eq 0 ]; then
  echo "[dev:opencode-remote] all services already running"
  while true; do sleep 60; done
fi

while true; do
  for pid in "${pids[@]}"; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      wait "$pid" || true
      exit 1
    fi
  done
  sleep 1
done

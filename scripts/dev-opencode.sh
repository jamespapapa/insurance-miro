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

echo "[dev:opencode] node=$(node -v 2>/dev/null || echo missing) npm=$(npm -v 2>/dev/null || echo missing)"

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

if port_open 127.0.0.1 4096 >/dev/null 2>&1; then
  echo "[dev:opencode] reusing existing opencode serve on 4096"
else
  run_named opencode npm run opencode:serve
  sleep 4
fi

if port_open 127.0.0.1 4097 >/dev/null 2>&1; then
  echo "[dev:opencode] reusing existing proxy on 4097"
else
  run_named proxy npm run opencode:proxy
  sleep 2
fi

if port_open 127.0.0.1 5001 >/dev/null 2>&1; then
  echo "[dev:opencode] reusing existing backend on 5001"
else
  run_named backend npm run backend
  sleep 2
fi

FRONTEND_PORT="${FRONTEND_PORT:-3001}"

if port_open 127.0.0.1 "$FRONTEND_PORT" >/dev/null 2>&1; then
  echo "[dev:opencode] reusing existing frontend on ${FRONTEND_PORT}"
else
  run_named frontend npm run frontend
  sleep 2
fi

if [ "${#pids[@]}" -eq 0 ]; then
  echo "[dev:opencode] all services already running"
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

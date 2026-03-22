#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REF_DIR="$ROOT_DIR/reference/MiroFish"

if [ ! -d "$REF_DIR/.git" ]; then
  echo "Reference repo not found: $REF_DIR" >&2
  exit 1
fi

echo "[miromiro] Updating MiroFish reference..."
git -C "$REF_DIR" fetch origin --prune
git -C "$REF_DIR" checkout main
git -C "$REF_DIR" pull --ff-only origin main

echo "[miromiro] Reference updated to:"
git -C "$REF_DIR" log -1 --oneline

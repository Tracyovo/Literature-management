#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP="$ROOT/DesktopApp"
if [[ ! -d "$DESKTOP" ]]; then
  echo "DesktopApp folder not found."
  exit 1
fi

rm -rf "$DESKTOP/Frontend" "$DESKTOP/backend"
cp -r "$ROOT/Frontend" "$DESKTOP/Frontend"
mkdir -p "$DESKTOP/backend"
cp "$ROOT/dist/backend/LiteratureManagerBackend.exe" "$DESKTOP/backend/"

pushd "$DESKTOP" >/dev/null
npm install
npm run dist
popd >/dev/null

echo "Desktop app built at $DESKTOP/dist"

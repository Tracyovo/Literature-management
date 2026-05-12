#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_EXE="$ROOT/dist/backend/LiteratureManagerBackend.exe"
PORTABLE="$ROOT/dist/portable"

if [[ ! -f "$BACKEND_EXE" ]]; then
  echo "Backend exe not found. Run scripts/build_backend.sh first."
  exit 1
fi

rm -rf "$PORTABLE"
mkdir -p "$PORTABLE"
cp "$BACKEND_EXE" "$PORTABLE/LiteratureManagerBackend.exe"
cp -r "$ROOT/Frontend" "$PORTABLE/Frontend"
cp "$ROOT/launch_portable.bat" "$PORTABLE/launch_portable.bat"

echo "Portable build ready at $PORTABLE"

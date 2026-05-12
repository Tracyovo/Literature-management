#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENTRYPOINT="$ROOT/Backend/packaging/entrypoint.py"
BACKEND_PATH="$ROOT/Backend"
VENV_PY="$ROOT/.venv/Scripts/python.exe"
if [[ -f "$VENV_PY" ]]; then
  PYTHON_CMD="$VENV_PY"
else
  PYTHON_CMD="python"
fi

DIST="$ROOT/dist/backend"
WORK="$ROOT/dist/backend/build"
SPEC="$ROOT/dist/backend/spec"
mkdir -p "$DIST" "$WORK" "$SPEC"

"$PYTHON_CMD" -m PyInstaller --onefile --name LiteratureManagerBackend --noconfirm --clean --paths "$BACKEND_PATH" --distpath "$DIST" --workpath "$WORK" --specpath "$SPEC" "$ENTRYPOINT"

echo "Backend exe built at $DIST/LiteratureManagerBackend.exe"

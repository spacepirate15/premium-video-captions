#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "${PYTHON:-}" ]]; then
  PYTHON_BIN="$PYTHON"
elif [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif [[ -x "$HOME/miniconda3/bin/python" ]]; then
  PYTHON_BIN="$HOME/miniconda3/bin/python"
else
  echo "Could not find Python. Set PYTHON=/path/to/python or install python3." >&2
  exit 127
fi

exec "$PYTHON_BIN" "$ROOT_DIR/04-scripts/process_video.py" "$@"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"

usage() {
  cat <<'USAGE'
Usage: scripts/setup.sh

Creates a local Python virtual environment, installs runtime dependencies,
checks FFmpeg/FFprobe, creates local artifact folders, and runs smoke tests.

Environment:
  PYTHON=/path/to/python    Override Python interpreter
  VENV_DIR=/path/to/venv    Override virtual environment directory

Options:
  --print-python            Print the selected compatible Python and exit
USAGE
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

need_command() {
  local name="$1"
  local install_hint="$2"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Missing required command: $name" >&2
    echo "$install_hint" >&2
    exit 127
  fi
}

is_supported_python() {
  "$1" - <<'PY' >/dev/null 2>&1
import sys

version = sys.version_info
raise SystemExit(0 if (version.major, version.minor) >= (3, 11) and version.major == 3 and version.minor < 14 else 1)
PY
}

select_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    if is_supported_python "$PYTHON"; then
      printf '%s\n' "$PYTHON"
      return 0
    fi
    echo "PYTHON points to an unsupported interpreter. Use Python 3.11, 3.12, or 3.13." >&2
    return 1
  fi

  local candidate
  for candidate in python3.12 python3.11 python3.13 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      local path
      path="$(command -v "$candidate")"
      if is_supported_python "$path"; then
        printf '%s\n' "$path"
        return 0
      fi
    fi
  done

  echo "Could not find Python 3.11, 3.12, or 3.13." >&2
  echo "Install one of those versions, or set PYTHON=/path/to/python." >&2
  return 1
}

PYTHON_BIN="$(select_python)"

if [[ "${1:-}" == "--print-python" ]]; then
  printf '%s\n' "$PYTHON_BIN"
  exit 0
fi

need_command "git" "Install Git."
need_command "ffmpeg" "Install FFmpeg. macOS: brew install ffmpeg"
need_command "ffprobe" "Install FFmpeg/FFprobe. macOS: brew install ffmpeg"

if [[ -x "$VENV_DIR/bin/python" ]] && ! is_supported_python "$VENV_DIR/bin/python"; then
  echo "Existing virtual environment uses unsupported Python: $VENV_DIR" >&2
  echo "Remove it or choose a different VENV_DIR before running setup again." >&2
  exit 1
fi

"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r "$ROOT_DIR/04-scripts/requirements.txt"

mkdir -p \
  "$ROOT_DIR/01-raw-videos" \
  "$ROOT_DIR/02-processed-videos" \
  "$ROOT_DIR/03-assets/emojis" \
  "$ROOT_DIR/logs/transcripts"

python -m unittest discover -s "$ROOT_DIR/04-scripts" -p "test_*.py"
"$ROOT_DIR/04-scripts/caption_video.sh" --list-styles >/dev/null

cat <<SETUP_DONE
Setup complete.

Next:
  1. Drop a 1080x1920 video into 01-raw-videos/
  2. Run: source "$VENV_DIR/bin/activate"
  3. Run: 04-scripts/caption_video.sh --style evo --model base
SETUP_DONE

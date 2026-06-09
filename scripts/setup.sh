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

if [[ -n "${PYTHON:-}" ]]; then
  PYTHON_BIN="$PYTHON"
else
  need_command "python3" "Install Python 3.11 or newer."
  PYTHON_BIN="$(command -v python3)"
fi

need_command "git" "Install Git."
need_command "ffmpeg" "Install FFmpeg. macOS: brew install ffmpeg"
need_command "ffprobe" "Install FFmpeg/FFprobe. macOS: brew install ffmpeg"

"$PYTHON_BIN" - <<'PY'
import sys

if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 or newer is required.")
PY

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

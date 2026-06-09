#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${PREMIUM_CAPTIONS_REPO_URL:-https://github.com/spacepirate15/premium-video-captions.git}"
INSTALL_DIR="${1:-${PREMIUM_CAPTIONS_HOME:-$HOME/premium-video-captions}}"

usage() {
  cat <<'USAGE'
Usage: scripts/install.sh [install-dir]

Clones or updates premium-video-captions, then runs scripts/setup.sh.

Examples:
  scripts/install.sh
  scripts/install.sh "$HOME/tools/premium-video-captions"
USAGE
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if ! command -v git >/dev/null 2>&1; then
  echo "Missing required command: git" >&2
  exit 127
fi

if [[ -d "$INSTALL_DIR/.git" ]]; then
  git -C "$INSTALL_DIR" pull --ff-only
elif [[ -e "$INSTALL_DIR" ]]; then
  if [[ -n "$(find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    echo "Install directory exists and is not an empty Git checkout: $INSTALL_DIR" >&2
    exit 1
  fi
  git clone "$REPO_URL" "$INSTALL_DIR"
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

bash "$INSTALL_DIR/scripts/setup.sh"

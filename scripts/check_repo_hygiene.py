#!/usr/bin/env python3
"""Fail CI when public repository hygiene rules are violated."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

ALLOWED_PLACEHOLDERS = {
    "01-raw-videos/.gitkeep",
    "02-processed-videos/.gitkeep",
    "03-assets/emojis/.gitkeep",
    "logs/.gitkeep",
    "logs/transcripts/.gitkeep",
}

BLOCKED_PATH_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(^|/)\.DS_Store$"), "macOS metadata file"),
    (re.compile(r"(^|/)__pycache__/"), "Python bytecode cache"),
    (re.compile(r"\.py[co]$"), "Python bytecode file"),
    (re.compile(r"^01-raw-videos/.+"), "raw video artifact"),
    (re.compile(r"^02-processed-videos/.+"), "rendered video artifact"),
    (re.compile(r"^03-assets/emojis/.+\.(png|jpg|jpeg|webp)$", re.I), "downloaded emoji cache"),
    (re.compile(r"^logs/transcripts/.+\.json$", re.I), "transcript cache"),
    (re.compile(r"^04-scripts/temp_subtitles\.ass$"), "generated subtitle file"),
    (re.compile(r"(^|/)skills-lock\.json$"), "local agent lock file"),
    (re.compile(r"(^|/)\.env(\..*)?$"), "environment file"),
    (re.compile(r"\.(mp4|mov|m4v|mkv|avi|mp3|wav|m4a)$", re.I), "media artifact"),
)

SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bgh[oprsu]_[A-Za-z0-9_]{30,}\b"), "GitHub token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"), "GitHub fine-grained token"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "API key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (
        re.compile(
            r"(?i)\b(password|api[_-]?key|secret|token)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+=:-]{12,}"
        ),
        "credential assignment",
    ),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._-]{20,}"), "bearer token"),
)


@dataclass(frozen=True)
class Violation:
    path: str
    reason: str
    line: int | None = None

    def format(self) -> str:
        location = self.path if self.line is None else f"{self.path}:{self.line}"
        return f"{location}: {self.reason}"


def tracked_files() -> list[str]:
    output = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [line for line in output.splitlines() if line.strip()]


def find_path_violations(paths: Iterable[str]) -> list[Violation]:
    violations: list[Violation] = []
    for path in paths:
        normalized = path.replace("\\", "/")
        if normalized in ALLOWED_PLACEHOLDERS:
            continue
        for pattern, reason in BLOCKED_PATH_PATTERNS:
            if pattern.search(normalized):
                violations.append(Violation(normalized, reason))
                break
    return violations


def is_probably_binary(data: bytes) -> bool:
    return b"\0" in data


def find_secret_violations(path: str, text: str) -> list[Violation]:
    violations: list[Violation] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern, reason in SECRET_PATTERNS:
            if pattern.search(line):
                violations.append(Violation(path, reason, line_number))
                break
    return violations


def scan_file_for_secrets(path: str) -> list[Violation]:
    full_path = ROOT / path
    try:
        data = full_path.read_bytes()
    except OSError as exc:
        return [Violation(path, f"could not read tracked file: {exc}")]

    if is_probably_binary(data):
        return []

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return []
    return find_secret_violations(path, text)


def run(paths: Iterable[str]) -> list[Violation]:
    path_list = list(paths)
    violations = find_path_violations(path_list)
    for path in path_list:
        violations.extend(scan_file_for_secrets(path))
    return violations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional tracked paths to scan. Defaults to git ls-files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = args.paths or tracked_files()
    violations = run(paths)
    if not violations:
        print("Repository hygiene check passed.")
        return 0

    print("Repository hygiene check failed:", file=sys.stderr)
    for violation in violations:
        print(f"- {violation.format()}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

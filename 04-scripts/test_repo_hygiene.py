#!/usr/bin/env python3
"""Tests for public repository hygiene checks."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_repo_hygiene.py"
SPEC = importlib.util.spec_from_file_location("check_repo_hygiene", MODULE_PATH)
assert SPEC is not None
check_repo_hygiene = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = check_repo_hygiene
assert SPEC.loader is not None
SPEC.loader.exec_module(check_repo_hygiene)


class RepoHygieneTests(unittest.TestCase):
    def test_public_source_paths_are_allowed(self) -> None:
        paths = [
            "README.md",
            "04-scripts/process_video.py",
            "04-scripts/test_process_video.py",
            "scripts/setup.sh",
            "scripts/install.sh",
            "logs/transcripts/.gitkeep",
            "01-raw-videos/.gitkeep",
            "02-processed-videos/.gitkeep",
            "03-assets/emojis/.gitkeep",
        ]

        violations = check_repo_hygiene.find_path_violations(paths)

        self.assertEqual(violations, [])

    def test_private_artifact_paths_are_rejected(self) -> None:
        paths = [
            ".DS_Store",
            "01-raw-videos/private.mp4",
            "02-processed-videos/captioned_private.mp4",
            "03-assets/emojis/1f680.png",
            "04-scripts/__pycache__/process_video.pyc",
            "04-scripts/temp_subtitles.ass",
            "logs/transcripts/private.json",
            "skills-lock.json",
        ]

        violations = check_repo_hygiene.find_path_violations(paths)

        self.assertEqual(len(violations), len(paths))
        self.assertTrue(all(violation.reason for violation in violations))

    def test_secret_like_values_are_rejected(self) -> None:
        token_value = "gh" + "p_" + "abcdefghijklmnopqrstuvwxyz1234567890"
        text = f"GITHUB_TOKEN = '{token_value}'"

        violations = check_repo_hygiene.find_secret_violations("example.txt", text)

        self.assertEqual(len(violations), 1)
        self.assertIn("GitHub token", violations[0].reason)

    def test_generic_token_discussion_is_allowed(self) -> None:
        text = "Avoid per-project tokens and do not paste credentials into documentation."

        violations = check_repo_hygiene.find_secret_violations("docs/example.md", text)

        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()

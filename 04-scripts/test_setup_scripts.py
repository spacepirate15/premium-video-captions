#!/usr/bin/env python3
"""Tests for setup script behavior that can run without installing packages."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SetupScriptTests(unittest.TestCase):
    def test_setup_script_selects_supported_python(self) -> None:
        result = subprocess.run(
            [str(ROOT / "scripts" / "setup.sh"), "--print-python"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        python_path = result.stdout.strip()

        version = subprocess.check_output(
            [
                python_path,
                "-c",
                "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
            ],
            text=True,
        ).strip()
        major, minor = (int(part) for part in version.split("."))

        self.assertEqual(major, 3)
        self.assertGreaterEqual(minor, 11)
        self.assertLess(minor, 14)


if __name__ == "__main__":
    unittest.main()

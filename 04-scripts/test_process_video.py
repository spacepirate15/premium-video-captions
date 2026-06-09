#!/usr/bin/env python3
"""Focused tests for caption style behavior."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("process_video.py")
SPEC = importlib.util.spec_from_file_location("process_video", MODULE_PATH)
assert SPEC is not None
process_video = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = process_video
assert SPEC.loader is not None
SPEC.loader.exec_module(process_video)


class OpusClipStyleTests(unittest.TestCase):
    def test_opusclip_style_is_registered_as_lower_third_word_color_template(self) -> None:
        style = process_video.STYLES["opusclip"]

        self.assertEqual(style.variant, "opusclip")
        self.assertTrue(style.uppercase)
        self.assertGreaterEqual(style.caption_top_ratio, 0.62)
        self.assertLessEqual(style.caption_top_ratio, 0.72)
        self.assertGreater(style.emoji_scale, 1.7)

    def test_opusclip_uses_its_own_large_sticker_emoji_rules(self) -> None:
        style = process_video.STYLES["opusclip"]

        self.assertEqual(process_video.pick_relevant_emoji("want serious trading results", style), "✅")
        self.assertEqual(process_video.pick_relevant_emoji("the forex miner ea", style), "⛏️")
        self.assertEqual(process_video.pick_relevant_emoji("fully automated", style), "💯")
        self.assertEqual(process_video.pick_relevant_emoji("see the live proof", style), "👀")

    def test_opusclip_keeps_word_timed_events_with_chunk_start_for_entry_animation(self) -> None:
        style = process_video.STYLES["opusclip"]
        words = [
            process_video.Word("the", 1.00, 1.10),
            process_video.Word("forex", 1.12, 1.32),
            process_video.Word("miner", 1.34, 1.54),
            process_video.Word("ea", 1.56, 1.76),
        ]

        events = process_video.caption_events(words, style)

        self.assertEqual(len(events), 4)
        self.assertEqual(events[0].lines, (("THE", "FOREX"), ("MINER", "EA")))
        self.assertTrue(all(event.chunk_start == events[0].chunk_start for event in events))
        self.assertTrue(all(event.chunk_end == events[0].chunk_end for event in events))


if __name__ == "__main__":
    unittest.main()

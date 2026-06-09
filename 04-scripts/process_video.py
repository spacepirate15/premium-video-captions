#!/usr/bin/env python3
"""Transcribe a vertical video and burn modern word-highlight captions."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "01-raw-videos"
OUT_DIR = ROOT / "02-processed-videos"
LOG_DIR = ROOT / "logs"
TEMP_ASS = ROOT / "04-scripts" / "temp_subtitles.ass"
TRANSCRIPT_DIR = LOG_DIR / "transcripts"
EMOJI_DIR = ROOT / "03-assets" / "emojis"

CANVAS_W = 1080
CANVAS_H = 1920
CAPTION_TOP_RATIO = 0.40

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class CaptionStyle:
    name: str
    font: str
    size: int
    primary: str
    highlight: str
    outline: str
    shadow: str
    border_style: int
    outline_width: float
    shadow_depth: float
    margin_v: int
    uppercase: bool
    max_words: int
    max_chars: int
    line_break_after: int
    active_bold: bool = True
    description: str = ""
    variant: str = "active-box"
    caption_top_ratio: float = CAPTION_TOP_RATIO
    emoji_scale: float = 0.98


@dataclass(frozen=True)
class CaptionEvent:
    start: float
    end: float
    lines: tuple[tuple[str, ...], ...]
    active_line: int
    active_index: int
    emoji: str | None
    chunk_start: float = 0.0
    chunk_end: float = 0.0


STYLES: dict[str, CaptionStyle] = {
    "evo": CaptionStyle(
        name="evo",
        font="Arial Black",
        size=84,
        primary="&H00FFFFFF",
        highlight="&H00000000",
        outline="&H00000000",
        shadow="&H33000000",
        border_style=1,
        outline_width=5,
        shadow_depth=3,
        margin_v=0,
        uppercase=False,
        max_words=3,
        max_chars=24,
        line_break_after=3,
        description="Transparent premium captions with active-word highlight background.",
    ),
    "evo-red": CaptionStyle(
        name="evo-red",
        font="Arial Black",
        size=76,
        primary="&H00FFFFFF",
        highlight="&H001D42FF",
        outline="&H00000000",
        shadow="&H66000000",
        border_style=1,
        outline_width=5,
        shadow_depth=3,
        margin_v=0,
        uppercase=True,
        max_words=4,
        max_chars=22,
        line_break_after=2,
        description="Bold Reels look with red active word and thick black stroke.",
    ),
    "opusclip": CaptionStyle(
        name="opusclip",
        font="Arial Black",
        size=86,
        primary="&H00FFFFFF",
        highlight="&H0000F5FF",
        outline="&H00000000",
        shadow="&H99000000",
        border_style=1,
        outline_width=8,
        shadow_depth=5,
        margin_v=0,
        uppercase=True,
        max_words=4,
        max_chars=28,
        line_break_after=2,
        description="OpusClip-style lower-third captions with active colored words and large stickers.",
        variant="opusclip",
        caption_top_ratio=0.66,
        emoji_scale=2.08,
    ),
    "neon": CaptionStyle(
        name="neon",
        font="Arial Black",
        size=76,
        primary="&H00FFFFFF",
        highlight="&H0000F5FF",
        outline="&H00000000",
        shadow="&H88000000",
        border_style=1,
        outline_width=5,
        shadow_depth=4,
        margin_v=0,
        uppercase=True,
        max_words=4,
        max_chars=22,
        line_break_after=2,
        description="White text, black stroke, yellow active word.",
    ),
    "telegram-clean": CaptionStyle(
        name="telegram-clean",
        font="Avenir Next",
        size=68,
        primary="&H00FFFFFF",
        highlight="&H0000D7FF",
        outline="&H00000000",
        shadow="&H77000000",
        border_style=1,
        outline_width=4,
        shadow_depth=2,
        margin_v=0,
        uppercase=False,
        max_words=5,
        max_chars=28,
        line_break_after=3,
        description="Cleaner mixed-case style for Telegram posts.",
    ),
    "luxury-gold": CaptionStyle(
        name="luxury-gold",
        font="Arial Black",
        size=74,
        primary="&H00FFFFFF",
        highlight="&H0000BFFF",
        outline="&H0020180A",
        shadow="&H88000000",
        border_style=1,
        outline_width=5,
        shadow_depth=3,
        margin_v=0,
        uppercase=True,
        max_words=4,
        max_chars=22,
        line_break_after=2,
        description="Premium gold highlight with dark stroke.",
    ),
}


EMOJI_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(profit|profits|gain|gains|revenue|money|\$|₹)\b", re.I), "💰"),
    (re.compile(r"\b(drawdown|loss|risk|under\s+\d+%|5%)\b", re.I), "📉"),
    (re.compile(r"\b(week|daily|month|today|yesterday)\b", re.I), "📆"),
    (re.compile(r"\b(algo|automated|automation|robot|bot)\b", re.I), "🤖"),
    (re.compile(r"\b(smart|built|consistency|consistent)\b", re.I), "✅"),
    (re.compile(r"\b(blink|miss|watch|see|look)\b", re.I), "👀"),
    (re.compile(r"\b(game|running|background)\b", re.I), "⚡"),
    (re.compile(r"\b(sample|free|gift|offer)\b", re.I), "🎁"),
    (re.compile(r"\b(sales|salesman|sell|buyer|client)\b", re.I), "🤝"),
    (re.compile(r"\b(start|launch|go|now)\b", re.I), "🚀"),
)

OPUS_EMOJI_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(results?|serious)\b", re.I), "✅"),
    (re.compile(r"\b(forex|miner|ea)\b", re.I), "⛏️"),
    (re.compile(r"\b(drawdown|risk|managed|under|maximum)\b", re.I), "⚠️"),
    (re.compile(r"\b(algo|automated|automation|fully|bot|robot)\b", re.I), "💯"),
    (re.compile(r"\b(precision|trading|launch|go)\b", re.I), "🚀"),
    (re.compile(r"\b(live|proof|see|watch|look)\b", re.I), "👀"),
    (re.compile(r"\b(bank|banked|dollars?|hundred|thousand|money|profit|profits|\$|₹)\b", re.I), "💲"),
    (re.compile(r"\b(now|right now|start)\b", re.I), "🚀"),
)

EMOJI_ASSETS: dict[str, str] = {
    "💰": "1f4b0",
    "💲": "1f4b2",
    "📉": "1f4c9",
    "📆": "1f4c6",
    "🤖": "1f916",
    "✅": "2705",
    "👀": "1f440",
    "⚡": "26a1",
    "⚠️": "26a0",
    "⛏️": "26cf",
    "💯": "1f4af",
    "⬆️": "2b06",
    "🎁": "1f381",
    "🤝": "1f91d",
    "🚀": "1f680",
}

FONT_FILES: dict[str, Path] = {
    "Arial Black": Path("/System/Library/Fonts/Supplemental/Arial Black.ttf"),
    "Avenir Next": Path("/System/Library/Fonts/Avenir Next.ttc"),
    "Impact": Path("/System/Library/Fonts/Supplemental/Impact.ttf"),
    "Arial Bold": Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
}

STYLE_COLOR_NAMES: dict[str, str] = {
    "evo": "transparent",
    "evo-red": "transparent",
    "neon": "transparent",
    "telegram-clean": "transparent",
    "luxury-gold": "transparent",
}

TWEMOJI_BASE_URL = (
    "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72"
)


def ass_time(seconds: float) -> str:
    seconds = max(seconds, 0.0)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - math.floor(seconds)) * 100))
    if cs >= 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def escape_ass(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def override_color(color: str) -> str:
    return color if color.endswith("&") else f"{color}&"


def newest_raw_video() -> Path:
    videos = [
        path
        for path in RAW_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    ]
    if not videos:
        raise FileNotFoundError(f"No video files found in {RAW_DIR}")
    return max(videos, key=lambda path: path.stat().st_mtime)


def find_executable(name: str) -> str:
    exe = shutil.which(name)
    if exe:
        return exe

    home = Path.home()
    candidates = [
        home / "miniconda3" / "bin" / name,
        home / "anaconda3" / "bin" / name,
        Path("/opt/homebrew/bin") / name,
        Path("/usr/local/bin") / name,
    ]
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)

    if name == "ffmpeg":
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass

    raise FileNotFoundError(f"Could not find {name}. Install FFmpeg or add it to PATH.")


def parse_rate(rate: str) -> float:
    if "/" in rate:
        return float(Fraction(rate))
    return float(rate)


def probe_video(input_path: Path) -> tuple[int, int, float]:
    ffprobe = find_executable("ffprobe")
    raw = subprocess.check_output(
        [
            ffprobe,
            "-hide_banner",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate",
            "-of",
            "json",
            str(input_path),
        ],
        text=True,
    )
    data = json.loads(raw)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"]), parse_rate(stream["avg_frame_rate"])


def transcribe_with_faster_whisper(input_path: Path, model_size: str) -> list[Word]:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(
        str(input_path),
        language="en",
        vad_filter=True,
        word_timestamps=True,
        beam_size=5,
    )

    words: list[Word] = []
    for segment in segments:
        for word in segment.words or []:
            text = word.word.strip()
            if text:
                words.append(Word(text=text, start=float(word.start), end=float(word.end)))
    return words


def transcribe_with_whisper_timestamped(input_path: Path, model_size: str) -> list[Word]:
    import whisper_timestamped as whisper

    audio = whisper.load_audio(str(input_path))
    model = whisper.load_model(model_size)
    result = whisper.transcribe(model, audio, language="en")

    words: list[Word] = []
    for segment in result["segments"]:
        for word in segment["words"]:
            text = word["text"].strip()
            if text:
                words.append(Word(text=text, start=float(word["start"]), end=float(word["end"])))
    return words


def transcribe(input_path: Path, model_size: str) -> list[Word]:
    try:
        words = transcribe_with_faster_whisper(input_path, model_size)
    except ModuleNotFoundError:
        words = transcribe_with_whisper_timestamped(input_path, model_size)

    if not words:
        raise RuntimeError("Transcription produced no words.")
    return words


def clean_word(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def merge_punctuation_words(words: list[Word]) -> list[Word]:
    merged: list[Word] = []
    for word in words:
        text = clean_word(word.text)
        if not text:
            continue
        if merged and re.match(r"^[,.;:!?%]", text):
            previous = merged[-1]
            merged[-1] = Word(
                text=f"{previous.text}{text}",
                start=previous.start,
                end=max(previous.end, word.end),
            )
        else:
            merged.append(Word(text=text, start=word.start, end=word.end))
    return merged


def pick_relevant_emoji(text: str, style: CaptionStyle | None = None) -> str | None:
    rules = OPUS_EMOJI_RULES if style and style.variant == "opusclip" else EMOJI_RULES
    for pattern, emoji in rules:
        if pattern.search(text):
            return emoji
    return None


def add_relevant_emoji(text: str, style: CaptionStyle | None = None) -> str:
    emoji = pick_relevant_emoji(text, style)
    return f"{text} {emoji}" if emoji else text


def chunk_words(words: list[Word], style: CaptionStyle) -> list[list[Word]]:
    chunks: list[list[Word]] = []
    current: list[Word] = []

    for word in words:
        proposed = current + [word]
        proposed_text = " ".join(w.text for w in proposed)
        sentence_boundary = bool(current and re.search(r"[.!?]$", current[-1].text))
        too_many_words = len(proposed) > style.max_words
        too_many_chars = len(proposed_text) > style.max_chars
        long_pause = bool(current and word.start - current[-1].end > 0.55)

        if current and (too_many_words or too_many_chars or long_pause or sentence_boundary):
            chunks.append(current)
            current = [word]
        else:
            current = proposed

    if current:
        chunks.append(current)
    return chunks


def visual_text(words: Iterable[str], style: CaptionStyle) -> str:
    cleaned = [clean_word(word) for word in words if clean_word(word)]
    if style.uppercase:
        cleaned = [word.upper() for word in cleaned]

    if len(cleaned) > style.line_break_after:
        left = " ".join(cleaned[: style.line_break_after])
        right = " ".join(cleaned[style.line_break_after :])
        return f"{left}\\N{right}"
    return " ".join(cleaned)


def render_chunk_text(chunk: list[Word], active_index: int, style: CaptionStyle) -> str:
    words = [word.text for word in chunk]
    rendered_parts: list[str] = []

    for index, raw_word in enumerate(words):
        text = clean_word(raw_word)
        if style.uppercase:
            text = text.upper()
        text = escape_ass(text)

        if index == active_index:
            bold = r"\b1" if style.active_bold else ""
            rendered_parts.append(
                rf"{{{bold}\c{override_color(style.highlight)}\3c{override_color(style.outline)}\fscx108\fscy108}}"
                f"{text}"
                rf"{{\b0\c{override_color(style.primary)}\fscx100\fscy100}}"
            )
        else:
            rendered_parts.append(text)

    if len(rendered_parts) > style.line_break_after:
        line_1 = " ".join(rendered_parts[: style.line_break_after])
        line_2 = " ".join(rendered_parts[style.line_break_after :])
        body = f"{line_1}\\N{line_2}"
    else:
        body = " ".join(rendered_parts)

    plain = visual_text(words, style)
    emoji_text = add_relevant_emoji(plain.replace(r"\N", " "), style)
    if emoji_text != plain.replace(r"\N", " "):
        body += escape_ass(emoji_text[-2:])

    return rf"{{\fad(45,45)\t(0,90,\fscx104\fscy104)}}{body}"


def caption_events(words: list[Word], style: CaptionStyle) -> list[CaptionEvent]:
    events: list[CaptionEvent] = []
    for chunk in chunk_words(words, style):
        visible = [clean_word(word.text) for word in chunk if clean_word(word.text)]
        if style.uppercase:
            visible = [word.upper() for word in visible]

        if len(visible) > style.line_break_after:
            lines = (
                tuple(visible[: style.line_break_after]),
                tuple(visible[style.line_break_after :]),
            )
        else:
            lines = (tuple(visible),)

        chunk_text = " ".join(word.text for word in chunk)
        emoji = pick_relevant_emoji(chunk_text, style)
        chunk_start = max(0.0, chunk[0].start - 0.05)
        chunk_end = max(chunk[-1].end, chunk[-1].end + 0.16)

        for index, word in enumerate(chunk):
            start = max(0.0, word.start - 0.03)
            next_start = chunk[index + 1].start if index + 1 < len(chunk) else word.end
            end = max(word.end, min(next_start, word.end + 0.12))
            if end <= start:
                end = start + 0.12

            if index >= style.line_break_after and len(lines) > 1:
                active_line = 1
                active_index = index - style.line_break_after
            else:
                active_line = 0
                active_index = index

            events.append(
                CaptionEvent(
                    start=start,
                    end=end,
                    lines=lines,
                    active_line=active_line,
                    active_index=active_index,
                    emoji=emoji,
                    chunk_start=chunk_start,
                    chunk_end=chunk_end,
                )
            )
    return events


def build_ass(words: list[Word], style: CaptionStyle, output_path: Path) -> None:
    chunks = chunk_words(words, style)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font},{style.size},{style.primary},{style.highlight},{style.outline},{style.shadow},-1,0,0,0,100,100,0,0,{style.border_style},{style.outline_width},{style.shadow_depth},2,95,95,{style.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events: list[str] = []
    for chunk in chunks:
        for index, word in enumerate(chunk):
            start = max(0.0, word.start - 0.03)
            next_start = chunk[index + 1].start if index + 1 < len(chunk) else word.end
            end = max(word.end, min(next_start, word.end + 0.12))
            if end <= start:
                end = start + 0.12
            text = render_chunk_text(chunk, index, style)
            events.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{text}")

    output_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def ass_to_rgb(color: str) -> str:
    value = color.removeprefix("&H").removesuffix("&")
    value = value.zfill(8)
    blue = value[2:4]
    green = value[4:6]
    red = value[6:8]
    return f"#{red}{green}{blue}"


def active_box_color(style: CaptionStyle) -> str:
    return {
        "evo": "#ffea00",
        "evo-red": "#ff3d4f",
        "neon": "#00f5ff",
        "telegram-clean": "#ffb000",
        "luxury-gold": "#ffc400",
    }.get(style.name, "#ffea00")


def active_text_color(style: CaptionStyle) -> str:
    return {
        "evo": "#050505",
        "evo-red": "#ffffff",
        "neon": "#020202",
        "telegram-clean": "#070707",
        "luxury-gold": "#050505",
    }.get(style.name, "#050505")


def font_file(style: CaptionStyle) -> Path:
    path = FONT_FILES.get(style.font, FONT_FILES["Arial Bold"])
    if path.exists():
        return path
    return FONT_FILES["Arial Bold"]


def text_width(font, text: str) -> int:
    return int(math.ceil(font.getlength(text))) if text else 0


def filter_quote(value: str | Path) -> str:
    text = str(value)
    return "'" + text.replace("\\", "\\\\").replace("'", r"\'").replace(":", r"\:") + "'"


def enable_expr(start: float, end: float) -> str:
    return filter_quote(f"between(t,{start:.3f},{end:.3f})")


def overlay_bounce_y(base_y: int, start: float) -> str:
    duration = 0.22
    expr = f"{base_y}-12*between(t,{start:.3f},{start + duration:.3f})*sin(3.14159*(t-{start:.3f})/{duration:.2f})"
    return filter_quote(expr)


def write_textfile(temp_dir: Path, index: int, text: str) -> Path:
    path = temp_dir / f"text_{index:04d}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def ensure_emoji_asset(emoji: str) -> Path | None:
    code = EMOJI_ASSETS.get(emoji)
    if not code:
        return None

    EMOJI_DIR.mkdir(parents=True, exist_ok=True)
    path = EMOJI_DIR / f"{code}.png"
    if path.exists():
        return path

    url = f"{TWEMOJI_BASE_URL}/{code}.png"
    try:
        urllib.request.urlretrieve(url, path)
    except Exception as exc:
        print(f"Warning: could not download emoji asset {emoji} from {url}: {exc}", file=sys.stderr)
        return None
    return path


def load_font(font_path: Path, size: int):
    from PIL import ImageFont

    return ImageFont.truetype(str(font_path), size)


def layout_event(event: CaptionEvent, style: CaptionStyle, font_path: Path) -> dict[str, object]:
    mode = STYLE_COLOR_NAMES[style.name]
    line_texts = [" ".join(line) for line in event.lines]
    font_size = style.size
    font = load_font(font_path, font_size)
    widths = [text_width(font, line) for line in line_texts]
    max_text_width = 900
    widest = max(widths or [1])
    if widest > max_text_width:
        font_size = max(50, int(style.size * (max_text_width / widest)))
        font = load_font(font_path, font_size)
        widths = [text_width(font, line) for line in line_texts]

    line_gap = max(8, int(font_size * 0.16))
    padding_x = 0
    padding_y = 0
    line_height = int(font_size * 1.08)
    text_h = len(line_texts) * line_height + max(0, len(line_texts) - 1) * line_gap
    box_w = max(widths or [0]) + padding_x * 2
    box_h = text_h + padding_y * 2
    top_y = int(CANVAS_H * 0.40)
    top_y = max(160, min(top_y, CANVAS_H - box_h - 180))
    box_x = (CANVAS_W - box_w) // 2

    line_positions: list[tuple[int, int, int]] = []
    for idx, width in enumerate(widths):
        x = (CANVAS_W - width) // 2
        y = top_y + padding_y + idx * (line_height + line_gap)
        line_positions.append((x, y, width))

    active_line_words = event.lines[event.active_line]
    prefix = " ".join(active_line_words[: event.active_index])
    if prefix:
        prefix = f"{prefix} "
    active_word = active_line_words[event.active_index]
    active_x = line_positions[event.active_line][0] + text_width(font, prefix)
    active_y = line_positions[event.active_line][1]
    active_w = text_width(font, active_word)
    active_h = int(font_size * 0.98)
    active_pad_x = max(10, int(font_size * 0.14))
    active_pad_y = max(5, int(font_size * 0.08))

    last_line_x, last_line_y, last_line_w = line_positions[-1]
    emoji_size = int(font_size * 0.98)
    emoji_x = min(CANVAS_W - emoji_size - 55, last_line_x + last_line_w + 16)
    emoji_y = last_line_y - int(font_size * 0.02)

    return {
        "font_size": font_size,
        "line_texts": line_texts,
        "line_positions": line_positions,
        "box": (box_x, int(top_y), int(box_w), int(box_h)),
        "active": (active_word, int(active_x), int(active_y)),
        "active_box": (
            int(active_x - active_pad_x),
            int(active_y + active_pad_y),
            int(active_w + active_pad_x * 2),
            int(active_h),
        ),
        "emoji": (int(emoji_x), int(emoji_y), emoji_size),
    }


def build_drawtext_filter(
    events: list[CaptionEvent],
    style: CaptionStyle,
    temp_dir: Path,
) -> tuple[str, list[Path]]:
    font_path = font_file(style)
    mode = STYLE_COLOR_NAMES[style.name]
    primary = ass_to_rgb(style.primary)
    outline = ass_to_rgb(style.outline)
    active_fill = active_box_color(style)
    active_text = active_text_color(style)

    filters: list[str] = [f"[0:v]format=yuv420p[v0]"]
    current_label = "v0"
    next_label_id = 1
    textfile_index = 0
    emoji_inputs: dict[str, int] = {}
    emoji_assets: list[Path] = []

    def next_label() -> str:
        nonlocal next_label_id
        label = f"v{next_label_id}"
        next_label_id += 1
        return label

    def add_filter(filter_body: str) -> None:
        nonlocal current_label
        label = next_label()
        filters.append(f"[{current_label}]{filter_body}[{label}]")
        current_label = label

    def textfile_for(text: str) -> Path:
        nonlocal textfile_index
        path = write_textfile(temp_dir, textfile_index, text)
        textfile_index += 1
        return path

    for event in events:
        layout = layout_event(event, style, font_path)
        font_size = int(layout["font_size"])  # type: ignore[arg-type]
        enable = enable_expr(event.start, event.end)

        line_texts = layout["line_texts"]  # type: ignore[assignment]
        line_positions = layout["line_positions"]  # type: ignore[assignment]
        for line_text, (x, y, _width) in zip(line_texts, line_positions, strict=True):
            path = textfile_for(line_text)
            size_ratio = font_size / style.size
            borderw = max(1, int(style.outline_width * size_ratio))
            shadowx = max(1, int(style.shadow_depth * size_ratio))
            shadowy = max(1, int(style.shadow_depth * size_ratio))
            add_filter(
                "drawtext="
                f"fontfile={filter_quote(font_path)}:"
                f"textfile={filter_quote(path)}:"
                f"fontsize={font_size}:fontcolor={primary}:"
                f"x={x}:y={y}:borderw={borderw}:bordercolor={outline}:"
                f"shadowx={shadowx}:shadowy={shadowy}:shadowcolor=black@0.45:"
                f"expansion=none:enable={enable}"
            )

        active_word, active_x, active_y = layout["active"]  # type: ignore[misc]
        active_box_x, active_box_y, active_box_w, active_box_h = layout["active_box"]  # type: ignore[misc]
        add_filter(
            "drawbox="
            f"x={active_box_x}:y={active_box_y}:w={active_box_w}:h={active_box_h}:"
            f"color={active_fill}@0.94:t=fill:enable={enable}"
        )
        active_path = textfile_for(active_word)
        add_filter(
            "drawtext="
            f"fontfile={filter_quote(font_path)}:"
            f"textfile={filter_quote(active_path)}:"
            f"fontsize={font_size}:fontcolor={active_text}:"
            f"x={active_x}:y={active_y}:borderw=0:bordercolor={outline}:"
            f"shadowx=0:shadowy=0:expansion=none:enable={enable}"
        )

        if event.emoji:
            asset = ensure_emoji_asset(event.emoji)
            if asset:
                if event.emoji not in emoji_inputs:
                    emoji_inputs[event.emoji] = len(emoji_assets) + 1
                    emoji_assets.append(asset)
                input_index = emoji_inputs[event.emoji]
                emoji_x, emoji_y, emoji_size = layout["emoji"]  # type: ignore[misc]
                emoji_label = f"e{next_label_id}"
                filters.append(f"[{input_index}:v]scale={emoji_size}:{emoji_size}[{emoji_label}]")
                label = next_label()
                filters.append(
                    f"[{current_label}][{emoji_label}]"
                    f"overlay=x={emoji_x}:y={overlay_bounce_y(emoji_y, event.start)}:"
                    f"enable={enable}:format=auto:shortest=1[{label}]"
                )
                current_label = label

    filters.append(f"[{current_label}]null[vout]")
    return ";".join(filters), emoji_assets


def burn_with_drawtext(input_path: Path, words: list[Word], style: CaptionStyle, output_path: Path, crf: int) -> None:
    ffmpeg = find_executable("ffmpeg")
    events = caption_events(words, style)
    with tempfile.TemporaryDirectory(prefix="caption-drawtext-") as temp_name:
        temp_dir = Path(temp_name)
        filter_complex, emoji_assets = build_drawtext_filter(events, style, temp_dir)
        cmd = [ffmpeg, "-y", "-i", str(input_path)]
        for asset in emoji_assets:
            cmd.extend(["-loop", "1", "-i", str(asset)])
        cmd.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[vout]",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                str(crf),
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )
        subprocess.run(cmd, check=True)


def pillow_text_bbox(draw, text: str, font, stroke_width: int = 0) -> tuple[int, int, int, int]:
    return draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)


def pillow_text_width(draw, text: str, font, stroke_width: int = 0) -> int:
    left, _top, right, _bottom = pillow_text_bbox(draw, text, font, stroke_width)
    return right - left


def pillow_text_height(draw, text: str, font, stroke_width: int = 0) -> int:
    _left, top, _right, bottom = pillow_text_bbox(draw, text, font, stroke_width)
    return bottom - top


def draw_text_top(draw, position: tuple[int, int], text: str, font, fill, stroke_width: int, stroke_fill) -> None:
    x, top_y = position
    left, top, _right, _bottom = pillow_text_bbox(draw, text, font, stroke_width)
    draw.text(
        (x - left, top_y - top),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def ease_out_back(progress: float) -> float:
    progress = max(0.0, min(progress, 1.0))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(progress - 1, 3) + c1 * pow(progress - 1, 2)


def load_emoji_image(emoji: str, size: int, cache: dict[tuple[str, int], object]):
    from PIL import Image

    key = (emoji, size)
    if key in cache:
        return cache[key]

    asset = ensure_emoji_asset(emoji)
    if not asset:
        return None

    image = Image.open(asset).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    cache[key] = image
    return image


def fit_pillow_font(style: CaptionStyle, lines: tuple[tuple[str, ...], ...], draw, font_path: Path):
    from PIL import ImageFont

    font_size = style.size
    max_width = int(CANVAS_W * 0.86)
    while font_size >= 54:
        font = ImageFont.truetype(str(font_path), font_size)
        stroke_width = max(3, int(round(font_size * 0.055)))
        line_widths = [pillow_text_width(draw, " ".join(line), font, stroke_width) for line in lines]
        if max(line_widths or [0]) <= max_width:
            return font, font_size, stroke_width, line_widths
        font_size -= 2

    font = ImageFont.truetype(str(font_path), font_size)
    stroke_width = max(3, int(round(font_size * 0.055)))
    line_widths = [pillow_text_width(draw, " ".join(line), font, stroke_width) for line in lines]
    return font, font_size, stroke_width, line_widths


OPUS_GREEN_WORDS = {
    "automated",
    "dollars",
    "ea",
    "managed",
    "percent",
    "precision",
    "proof",
    "results",
    "risk",
    "trading",
}

OPUS_YELLOW_WORDS = {
    "forex",
    "forexminers",
    "forexminers.com",
    "fully",
    "hundred",
    "live",
    "maximum",
    "now",
    "ten",
    "thousand",
    "under",
}

NUMBER_WORDS = {
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
    "hundred",
    "thousand",
    "million",
    "billion",
}


def opus_word_key(word: str) -> str:
    cleaned = clean_word(word).lower()
    cleaned = cleaned.replace(",", "")
    if re.fullmatch(r"[a-z0-9.-]+\.(com|in|net|org)", cleaned):
        return cleaned
    return re.sub(r"(^[^a-z0-9$₹%]+|[^a-z0-9$₹%.]+$)", "", cleaned)


def opus_active_color(word: str) -> tuple[int, int, int, int]:
    key = opus_word_key(word)
    if key in OPUS_GREEN_WORDS:
        return (0, 235, 43, 255)
    if key in OPUS_YELLOW_WORDS:
        return (255, 238, 0, 255)
    if re.search(r"[$₹]|\d|%", key):
        return (255, 238, 0, 255)
    if key in NUMBER_WORDS:
        return (255, 238, 0, 255)
    return (255, 238, 0, 255)


def opus_active_indices(event: CaptionEvent) -> set[tuple[int, int]]:
    active_word = event.lines[event.active_line][event.active_index]
    key = opus_word_key(active_word)
    indices = {(event.active_line, event.active_index)}

    if key in {"ten", "thousand"}:
        line = event.lines[event.active_line]
        for offset in (-1, 1):
            neighbor_index = event.active_index + offset
            if 0 <= neighbor_index < len(line):
                neighbor_key = opus_word_key(line[neighbor_index])
                if {key, neighbor_key} == {"ten", "thousand"}:
                    indices.add((event.active_line, neighbor_index))

    return indices


def draw_text_top_with_shadow(
    draw,
    position: tuple[int, int],
    text: str,
    font,
    fill: tuple[int, int, int, int],
    stroke_width: int,
    stroke_fill: tuple[int, int, int, int],
    shadow_offset: int,
) -> None:
    if shadow_offset:
        shadow_fill = (0, 0, 0, 175)
        draw_text_top(
            draw,
            (position[0] + shadow_offset, position[1] + shadow_offset),
            text,
            font,
            shadow_fill,
            stroke_width + 1,
            shadow_fill,
        )

    draw_text_top(draw, position, text, font, fill, stroke_width, stroke_fill)


def fit_opusclip_font(style: CaptionStyle, lines: tuple[tuple[str, ...], ...], draw, font_path: Path):
    from PIL import ImageFont

    font_size = style.size
    max_width = int(CANVAS_W * 0.92)
    while font_size >= 56:
        font = ImageFont.truetype(str(font_path), font_size)
        stroke_width = max(6, int(round(font_size * 0.09)))
        line_widths = [pillow_text_width(draw, " ".join(line), font, stroke_width) for line in lines]
        if max(line_widths or [0]) <= max_width:
            return font, font_size, stroke_width, line_widths
        font_size -= 2

    font = ImageFont.truetype(str(font_path), font_size)
    stroke_width = max(6, int(round(font_size * 0.09)))
    line_widths = [pillow_text_width(draw, " ".join(line), font, stroke_width) for line in lines]
    return font, font_size, stroke_width, line_widths


def draw_opusclip_caption_with_pillow(
    frame,
    event: CaptionEvent,
    style: CaptionStyle,
    t: float,
    emoji_cache: dict[tuple[str, int], object],
) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(frame, "RGBA")
    font_path = font_file(style)
    font, font_size, stroke_width, line_widths = fit_opusclip_font(style, event.lines, draw, font_path)
    stroke_fill = (0, 0, 0, 255)
    text_fill = (255, 255, 255, 255)
    shadow_offset = max(3, int(round(font_size * 0.055)))

    line_heights = [
        max(pillow_text_height(draw, word, font, stroke_width) for word in line)
        for line in event.lines
    ]
    line_gap = max(7, int(font_size * 0.08))
    top_y = int(CANVAS_H * style.caption_top_ratio)

    line_positions: list[tuple[int, int, int, int]] = []
    running_y = top_y
    for width, height in zip(line_widths, line_heights, strict=True):
        x = (CANVAS_W - width) // 2
        line_positions.append((x, running_y, width, height))
        running_y += height + line_gap

    if event.emoji:
        phase = max(0.0, t - event.chunk_start)
        pop_duration = 0.26
        scale = 1.0
        bounce_y = 0
        if phase < pop_duration:
            progress = phase / pop_duration
            scale = 0.74 + 0.26 * ease_out_back(progress)
            bounce_y = int(-16 * math.sin(math.pi * progress))

        emoji_size = max(96, int(font_size * style.emoji_scale * scale))
        emoji_image = load_emoji_image(event.emoji, emoji_size, emoji_cache)
        if emoji_image is not None:
            last_x, last_y, last_w, last_h = line_positions[-1]
            emoji_x = (CANVAS_W - emoji_size) // 2
            emoji_y = last_y + last_h + max(10, int(font_size * 0.08)) + bounce_y
            if event.emoji == "💲":
                emoji_y = top_y - int(font_size * 0.25) + bounce_y
            emoji_y = min(max(0, emoji_y), CANVAS_H - emoji_size - 24)
            frame.alpha_composite(emoji_image, (int(emoji_x), int(emoji_y)))

    active_indices = opus_active_indices(event)
    for line_index, (line, (line_x, line_y, _width, _height)) in enumerate(zip(event.lines, line_positions, strict=True)):
        x = line_x
        space_w = int(round(font.getlength(" ")))
        for word_index, word in enumerate(line):
            fill = opus_active_color(word) if (line_index, word_index) in active_indices else text_fill
            draw_text_top_with_shadow(
                draw,
                (x, line_y),
                word,
                font,
                fill,
                stroke_width,
                stroke_fill,
                shadow_offset,
            )
            x += pillow_text_width(draw, word, font, stroke_width) + space_w


def draw_caption_with_pillow(frame, event: CaptionEvent, style: CaptionStyle, t: float, emoji_cache: dict[tuple[str, int], object]) -> None:
    from PIL import ImageDraw

    if style.variant == "opusclip":
        draw_opusclip_caption_with_pillow(frame, event, style, t, emoji_cache)
        return

    draw = ImageDraw.Draw(frame, "RGBA")
    font_path = font_file(style)
    font, font_size, stroke_width, line_widths = fit_pillow_font(style, event.lines, draw, font_path)
    stroke_fill = (0, 0, 0, 255)
    text_fill = (255, 255, 255, 255)
    active_fill = tuple(int(active_text_color(style).lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)) + (255,)
    box_hex = active_box_color(style).lstrip("#")
    box_fill = tuple(int(box_hex[i : i + 2], 16) for i in (0, 2, 4)) + (228,)

    line_heights = [
        max(pillow_text_height(draw, word, font, stroke_width) for word in line)
        for line in event.lines
    ]
    line_gap = max(10, int(font_size * 0.18))
    top_y = int(CANVAS_H * CAPTION_TOP_RATIO)

    line_positions: list[tuple[int, int, int, int]] = []
    running_y = top_y
    for width, height in zip(line_widths, line_heights, strict=True):
        x = (CANVAS_W - width) // 2
        line_positions.append((x, running_y, width, height))
        running_y += height + line_gap

    for line, (x, y, _width, _height) in zip(event.lines, line_positions, strict=True):
        draw_text_top(draw, (x, y), " ".join(line), font, text_fill, stroke_width, stroke_fill)

    active_line = event.lines[event.active_line]
    active_word = active_line[event.active_index]
    line_x, line_y, _line_w, line_h = line_positions[event.active_line]
    prefix = " ".join(active_line[: event.active_index])
    prefix_width = pillow_text_width(draw, prefix + (" " if prefix else ""), font, stroke_width) if prefix else 0
    active_x = line_x + prefix_width
    active_bbox = pillow_text_bbox(draw, active_word, font, stroke_width)
    active_w = active_bbox[2] - active_bbox[0]
    active_h = active_bbox[3] - active_bbox[1]
    pad_x = max(12, int(font_size * 0.14))
    pad_y = max(8, int(font_size * 0.10))
    box_x = active_x - pad_x
    box_y = line_y - pad_y
    box_w = active_w + pad_x * 2
    box_h = active_h + pad_y * 2
    draw.rectangle((box_x, box_y, box_x + box_w, box_y + box_h), fill=box_fill)
    draw_text_top(draw, (active_x, line_y), active_word, font, active_fill, 0, active_fill)

    if not event.emoji:
        return

    phase = max(0.0, t - event.start)
    pop_duration = 0.22
    base_emoji_size = max(58, int(line_h * 0.96))
    scale = 1.0
    bounce_y = 0
    if phase < pop_duration:
        progress = phase / pop_duration
        scale = 0.72 + 0.28 * ease_out_back(progress)
        bounce_y = int(-12 * math.sin(math.pi * progress))
    emoji_size = max(42, int(base_emoji_size * scale))
    emoji_image = load_emoji_image(event.emoji, emoji_size, emoji_cache)
    if emoji_image is None:
        return

    last_x, last_y, last_w, last_h = line_positions[-1]
    emoji_x = last_x + last_w + max(12, int(font_size * 0.12))
    if emoji_x + emoji_size > CANVAS_W - 46:
        emoji_x = CANVAS_W - emoji_size - 46
    emoji_y = last_y + max(0, (last_h - emoji_size) // 2) + bounce_y
    emoji_y = max(0, emoji_y)
    frame.alpha_composite(emoji_image, (int(emoji_x), int(emoji_y)))


def burn_with_pillow(input_path: Path, words: list[Word], style: CaptionStyle, output_path: Path, crf: int) -> None:
    from PIL import Image

    ffmpeg = find_executable("ffmpeg")
    width, height, fps = probe_video(input_path)
    if (width, height) != (CANVAS_W, CANVAS_H):
        raise RuntimeError(f"Expected {CANVAS_W}x{CANVAS_H} input, got {width}x{height}.")

    events = caption_events(words, style)
    frame_size = width * height * 3
    decoder = subprocess.Popen(
        [
            ffmpeg,
            "-hide_banner",
            "-v",
            "error",
            "-i",
            str(input_path),
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        stdout=subprocess.PIPE,
    )
    encoder = subprocess.Popen(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{width}x{height}",
            "-r",
            f"{fps:.6f}",
            "-i",
            "-",
            "-i",
            str(input_path),
            "-map",
            "0:v",
            "-map",
            "1:a?",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_path),
        ],
        stdin=subprocess.PIPE,
    )

    assert decoder.stdout is not None
    assert encoder.stdin is not None
    event_index = 0
    emoji_cache: dict[tuple[str, int], object] = {}
    frame_index = 0
    try:
        while True:
            raw = decoder.stdout.read(frame_size)
            if not raw:
                break
            if len(raw) != frame_size:
                raise RuntimeError("Decoded partial frame; source video may be truncated.")

            t = frame_index / fps
            while event_index < len(events) and events[event_index].end < t:
                event_index += 1

            frame = Image.frombytes("RGB", (width, height), raw).convert("RGBA")
            if event_index < len(events):
                event = events[event_index]
                if event.start <= t <= event.end:
                    draw_caption_with_pillow(frame, event, style, t, emoji_cache)

            encoder.stdin.write(frame.convert("RGB").tobytes())
            frame_index += 1
    finally:
        decoder.stdout.close()
        encoder.stdin.close()

    decoder_status = decoder.wait()
    encoder_status = encoder.wait()
    if decoder_status != 0:
        raise subprocess.CalledProcessError(decoder_status, decoder.args)
    if encoder_status != 0:
        raise subprocess.CalledProcessError(encoder_status, encoder.args)


def write_transcript(words: list[Word], input_path: Path) -> Path:
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    transcript_path = TRANSCRIPT_DIR / f"{input_path.stem}.json"
    transcript_path.write_text(
        json.dumps([word.__dict__ for word in words], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return transcript_path


def read_cached_transcript(input_path: Path) -> list[Word] | None:
    transcript_path = TRANSCRIPT_DIR / f"{input_path.stem}.json"
    if not transcript_path.exists():
        return None
    data = json.loads(transcript_path.read_text(encoding="utf-8"))
    return [Word(text=item["text"], start=float(item["start"]), end=float(item["end"])) for item in data]


def list_styles() -> None:
    for style in STYLES.values():
        print(f"{style.name:15} {style.description}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="Input video. Defaults to newest file in 01-raw-videos.")
    parser.add_argument("--style", default="evo", choices=sorted(STYLES), help="Caption style to render.")
    parser.add_argument("--model", default="base", help="Whisper model size for transcription.")
    parser.add_argument("--output", help="Output path. Defaults to 02-processed-videos/captioned_<stem>_<style>.mp4")
    parser.add_argument("--ass", default=str(TEMP_ASS), help="ASS subtitle path to write.")
    parser.add_argument("--crf", type=int, default=14, help="H.264 quality. Lower is higher quality.")
    parser.add_argument("--force-transcribe", action="store_true", help="Ignore cached transcript JSON and transcribe again.")
    parser.add_argument("--list-styles", action="store_true", help="Print installed caption styles and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_styles:
        list_styles()
        return 0

    input_path = Path(args.input).expanduser().resolve() if args.input else newest_raw_video()
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    style = STYLES[args.style]
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else OUT_DIR / f"captioned_{input_path.stem}_{style.name}.mp4"
    )
    ass_path = Path(args.ass).expanduser().resolve()

    print(f"Input: {input_path}")
    print(f"Style: {style.name}")
    print(f"Output: {output_path}")
    words = None if args.force_transcribe else read_cached_transcript(input_path)
    if words:
        transcript_path = TRANSCRIPT_DIR / f"{input_path.stem}.json"
        print(f"Using cached transcript: {transcript_path}")
    else:
        print("Transcribing...")
        words = transcribe(input_path, args.model)
        transcript_path = TRANSCRIPT_DIR / f"{input_path.stem}.json"
    words = merge_punctuation_words(words)
    transcript_path = write_transcript(words, input_path)
    print(f"Transcript words: {len(words)}")
    print(f"Transcript JSON: {transcript_path}")

    print(f"Writing subtitles: {ass_path}")
    build_ass(words, style, ass_path)

    print("Burning captions with Pillow anti-aliased renderer...")
    burn_with_pillow(input_path, words, style, output_path, args.crf)
    print(f"Done: {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)

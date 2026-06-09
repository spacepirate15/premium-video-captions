# Premium Video Captions

Premium Video Captions is a small local workspace for turning vertical short-form videos into burned-in, word-timed caption edits. It is built around Python, FFmpeg, Whisper transcription, and a Pillow-based renderer that composites text, active-word highlights, and emoji overlays into each frame.

The repository is designed as a reusable template: drop raw videos into `01-raw-videos/`, run the caption script, and collect rendered MP4s from `02-processed-videos/`.

## Quick Install

Recommended clone-based install:

```bash
git clone https://github.com/spacepirate15/premium-video-captions.git
cd premium-video-captions
bash scripts/setup.sh
```

One-command bootstrap for macOS/Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/spacepirate15/premium-video-captions/main/scripts/install.sh | bash
```

The installer clones the repository into `$HOME/premium-video-captions`, creates a local `.venv`, installs Python dependencies, checks FFmpeg/FFprobe, creates local artifact folders, and runs smoke tests. It does not use `sudo`.

## What It Does

- Transcribes speech into word-level timestamps with Whisper.
- Groups captions into short, punchy chunks for social video.
- Renders active spoken-word highlights.
- Supports multiple caption styles, including `evo`, `opusclip`, `neon`, `telegram-clean`, and `luxury-gold`.
- Uses a Pillow compositing path for cleaner caption edges than stacked FFmpeg `drawtext` filters.
- Caches transcripts locally so repeated styling passes do not require retranscription.

## Repository Layout

```text
.
|-- 01-raw-videos/          # Local input videos, ignored by Git
|-- 02-processed-videos/    # Local rendered videos, ignored by Git
|-- 03-assets/emojis/       # Downloaded emoji PNG cache, ignored by Git
|-- 04-scripts/             # Caption renderer, wrapper script, tests, requirements
|-- logs/transcripts/       # Local transcript cache, ignored by Git
|-- .agents/                # Optional agent skill for this workflow
`-- video_captions_blueprint.md
```

## Requirements

- Python 3.11, 3.12, or 3.13
- FFmpeg and FFprobe
- A 1080x1920 source video for the current premium renderer

On macOS:

```bash
brew install ffmpeg
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r 04-scripts/requirements.txt
```

If you want the optional Whisper fallback stack, install:

```bash
python -m pip install -r 04-scripts/requirements-full.txt
```

## Usage

List available styles:

```bash
04-scripts/caption_video.sh --list-styles
```

Render the newest video in `01-raw-videos/` with the default style:

```bash
04-scripts/caption_video.sh --style evo --model base
```

Render a specific file:

```bash
04-scripts/caption_video.sh 01-raw-videos/example.mp4 --style opusclip --model base
```

The output is written to:

```text
02-processed-videos/captioned_<source_stem>_<style>.mp4
```

The transcript cache is written to:

```text
logs/transcripts/<source_stem>.json
```

Use `--force-transcribe` when the transcript cache should be ignored.

## Quality Notes

The preferred renderer is `burn_with_pillow()` in `04-scripts/process_video.py`. It decodes frames, draws the full caption group into an RGBA overlay, alpha-composites emoji and text in one pass, then encodes the result with FFmpeg.

That design avoids common caption defects from layered `drawtext` filters: clipped glyph tops, fuzzy active-word boxes, color spill, and inconsistent emoji sizing.

## Tests

Run the focused unit tests:

```bash
python -m unittest discover -s 04-scripts -p "test_*.py"
python scripts/check_repo_hygiene.py
```

These tests cover caption style registration, word timing, emoji rule selection, and OpusClip-style event grouping. They do not render a full video; full render verification still requires inspecting extracted frames from an actual output MP4.

## Contributing

Improvements are welcome through pull requests. Useful changes include better font discovery, more caption styles, faster rendering, safer setup, and visual regression tooling.

Every pull request should pass CI and include reproducible evidence. Rendering changes need human review because tests can prove logic, but they cannot fully judge whether a caption style looks polished.

## Public-Repo Hygiene

Raw videos, rendered videos, transcript JSON, generated ASS subtitles, downloaded emoji PNGs, Python caches, and local agent lock files are ignored by Git. This keeps private content and bulky generated artifacts out of the public repository.

## License

MIT. See `LICENSE`.

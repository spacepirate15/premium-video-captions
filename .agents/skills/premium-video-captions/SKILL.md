---
name: premium-video-captions
description: Use when rendering short-form vertical videos with premium word-by-word captions, active word highlight boxes, same-size emoji, and strict edge-quality verification.
---

# Premium Video Captions

## Overview

Use this skill for reel-style caption rendering in this workspace when the output must look premium, sharp, and free of clipped or grainy text edges.

The preferred renderer is the workspace Pillow compositing pipeline in `04-scripts/process_video.py`, invoked through `04-scripts/caption_video.sh`. Do not use FFmpeg `drawtext` as the final premium renderer unless the user explicitly asks for a quick draft.

## Required Rendering Standard

Use these defaults unless the user gives a different creative direction:

- Canvas: 1080x1920 vertical video.
- Caption position: top edge of the caption group at 40 percent below the top of the frame.
- Background: transparent overall; only the active spoken word gets a highlight rectangle.
- Layout: one compact caption line when possible, maximum three spoken words per segment, maximum width around 86 percent of the frame.
- Text: bold, high-contrast, anti-aliased, with stroke measured from the real glyph bounding box.
- Active word: black text on yellow highlight by default, with padding calculated from `textbbox`, not guessed from font size.
- Emojis: render as image assets, same visual height as the words, alpha-composited in the same frame as text.
- Emoji animation: small scale/bounce tied to the active word timing; keep it tasteful and readable.
- Encoding: H.264 MP4, yuv420p, `+faststart`, CRF 14 or better for final output.

The key rule: compose the whole caption group into one transparent overlay per frame, then alpha-composite that overlay into the video frame before encoding. Separate FFmpeg text, box, and emoji layers can create top-edge spillover, chroma fringing, or clipped highlights.

## Workspace Workflow

1. List styles before rendering:

```bash
04-scripts/caption_video.sh --list-styles
```

2. Render the final premium Evo style:

```bash
04-scripts/caption_video.sh --style evo --model base
```

This overwrites the default output for the latest raw video:

```text
02-processed-videos/captioned_<source_stem>_evo.mp4
```

3. If quality is being debugged, prefer the Pillow renderer in `burn_with_pillow()` over `burn_with_drawtext()`. The Pillow path should:

- decode source frames as RGB rawvideo;
- draw text, highlight boxes, and emoji into one RGBA frame;
- use `ImageDraw.textbbox()` for glyph bounds;
- include stroke width in the bounding-box calculation;
- align highlight rectangles to the measured active glyph top and bottom;
- alpha-composite emoji through PIL, not font emoji fallback;
- encode the processed raw frames with FFmpeg.

## Edge-Quality Verification

Never claim a caption-edge issue is fixed only because FFmpeg exited successfully. Extract and inspect still frames from the final MP4.

Use caption-heavy timestamps across the video:

```bash
ffmpeg -hide_banner -y -ss 00:00:06.60 -i 02-processed-videos/captioned_example_evo.mp4 -frames:v 1 /tmp/caption_qc_06_60.png
ffmpeg -hide_banner -y -ss 00:00:12.20 -i 02-processed-videos/captioned_example_evo.mp4 -frames:v 1 /tmp/caption_qc_12_20.png
ffmpeg -hide_banner -y -ss 00:00:22.20 -i 02-processed-videos/captioned_example_evo.mp4 -frames:v 1 /tmp/caption_qc_22_20.png
```

Then inspect crops around the caption band:

```bash
ffmpeg -hide_banner -y -i /tmp/caption_qc_06_60.png -vf crop=900:260:120:650 /tmp/caption_crop_06_60.png
ffmpeg -hide_banner -y -i /tmp/caption_qc_12_20.png -vf crop=900:260:80:700 /tmp/caption_crop_12_20.png
ffmpeg -hide_banner -y -i /tmp/caption_qc_22_20.png -vf crop=900:260:90:670 /tmp/caption_crop_22_20.png
```

Open the full frames and crops with the image viewer. Check the top edge of every word, active highlight box, and emoji:

- no clipped glyph tops;
- no black or colored spill above highlight boxes;
- no grainy halo around white letters;
- no emoji square background, jagged mask, or size mismatch;
- no full caption card behind the words;
- caption group still begins around 40 percent from the frame top.

If any of these fail, adjust the Pillow layout or encoding quality and re-render. Do not accept a drawtext-only workaround for the final premium output.

## Troubleshooting

If text looks clipped at the top, the highlight or glyph y-position is probably using approximate font metrics. Recalculate with `ImageDraw.textbbox()` including the configured stroke width.

If white outlines look grainy, ensure the final renderer is Pillow compositing, not separate FFmpeg drawtext filters, and keep CRF at 14 or lower.

If emoji edges look wrong, ensure Twemoji PNG assets are loaded and resized with `Image.Resampling.LANCZOS`, then alpha-composited into the same RGBA frame as the text.

If the caption is too high or low, adjust only `CAPTION_TOP_RATIO`; the premium default is `0.40`.

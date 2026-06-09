# Installed Caption Styles

Use:

```bash
bash 04-scripts/caption_video.sh --style evo
```

The script defaults to the newest video in `01-raw-videos/` and writes to
`02-processed-videos/`.

## Styles

`evo`
: Transparent premium kinetic captions at 40% screen height. White text with black stroke; the spoken word gets a tight yellow highlight background.

`evo-red`
: Uppercase Reels caption with white text, thick black stroke, and red active word.

`opusclip`
: OpusClip-style lower-third caption template. Uppercase white text uses a heavy black outline; the currently spoken word is colored yellow or green directly, without a highlight box. Relevant stickers render large below or behind the caption group.

`neon`
: Uppercase white text with black stroke and yellow active word.

`telegram-clean`
: Mixed-case cleaner social caption with softer sizing and orange active word.

`luxury-gold`
: Uppercase premium caption with gold active word and dark stroke.

To render a specific file instead of the newest raw video:

```bash
bash 04-scripts/caption_video.sh 01-raw-videos/example.mp4 --style neon
```

To apply the OpusClip-derived template:

```bash
bash 04-scripts/caption_video.sh 01-raw-videos/example.mp4 --style opusclip
```

## Notes

- Captions are grouped into short punchy chunks.
- One precise emoji is added when a chunk clearly matches a keyword, such as profit, risk, automation, free sample, or sales.
- Emoji overlays render at roughly word height and use a small bounce on entry.
- The default `evo` position starts around 40% down from the top of a 9:16 frame.
- The `opusclip` style uses a lower-third position around 66% down from the top, active spoken-word coloring, and larger sticker-style emoji placement to match the reference MP4.

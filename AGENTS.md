# Agent Instructions

This repository is a local-first caption rendering workspace.

- Treat `01-raw-videos/`, `02-processed-videos/`, and `logs/transcripts/` as local artifact folders, not source folders.
- Do not commit raw media, rendered media, transcripts, generated ASS files, Python caches, `.DS_Store`, credentials, or machine-local lock state.
- Use `04-scripts/caption_video.sh` as the main entrypoint.
- Prefer the Pillow renderer in `04-scripts/process_video.py` for final output quality.
- Run `python -m pytest` after code changes.
- If rendering behavior changes, verify with real frame extraction and visual inspection before claiming a visual issue is fixed.

# Contributing

Contributions are welcome when they keep the renderer practical, local-first, and easy to verify.

## Before Opening a Pull Request

Run the local checks:

```bash
python -m unittest discover -s 04-scripts -p "test_*.py"
python scripts/check_repo_hygiene.py
```

If you changed rendering behavior, run a real render and inspect extracted frames around caption-heavy timestamps.

Do not commit raw videos, rendered videos, transcript JSON, generated subtitle files, Python caches, local credentials, or machine-specific paths.

## Pull Request Standard

A pull request is more likely to be accepted when it includes:

- a clear user-visible benefit;
- focused code changes rather than broad rewrites;
- tests for logic changes;
- before/after evidence for rendering changes;
- no private media, generated artifacts, credentials, or copied proprietary assets.

Maintainers should reject changes that are hype-only, unverifiable, unsafe, or unrelated to premium caption rendering.

## Useful Areas for Improvement

- Better cross-platform font discovery.
- More caption style presets.
- Optional non-1080x1920 input normalization.
- Faster full-video rendering without sacrificing edge quality.
- Automated visual regression checks for caption crops.

## Review Policy

All outside contributions should go through pull requests. CI must pass before merge, and rendering changes need human review because caption quality is partly visual. Tests can catch regressions; they cannot tell whether a caption style actually looks premium.

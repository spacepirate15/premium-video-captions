# Contributing

Contributions are welcome when they keep the renderer practical, local-first, and easy to verify.

Before opening a pull request:

1. Run the unit tests.

```bash
python -m pytest
```

2. If you changed rendering behavior, run a real render and inspect extracted frames around caption-heavy timestamps.

3. Do not commit raw videos, rendered videos, transcript JSON, generated subtitle files, Python caches, local credentials, or machine-specific paths.

Useful areas for improvement:

- Better cross-platform font discovery.
- More caption style presets.
- Optional non-1080x1920 input normalization.
- Faster full-video rendering without sacrificing edge quality.
- Automated visual regression checks for caption crops.

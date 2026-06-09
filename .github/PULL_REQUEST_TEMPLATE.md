## What Changed

Describe the change plainly.

## Why

Explain the user-visible improvement or bug fixed.

## Verification

Include commands run and results.

Required:

- [ ] `python -m unittest discover -s 04-scripts -p "test_*.py"`
- [ ] `python scripts/check_repo_hygiene.py`

If rendering behavior changed:

- [ ] Rendered a real 1080x1920 sample locally
- [ ] Inspected caption-heavy frames or crops
- [ ] Did not commit raw videos, rendered videos, transcripts, or generated media

## Risk

Call out any tradeoffs, known gaps, or behavior that still needs manual review.

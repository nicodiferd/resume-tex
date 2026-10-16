# CLAUDE.md

Public repo: the resume of Nicolo DiFerdinando. See README.md for the pipeline.

## Hard rules

1. `data/profile.yaml` is the source of truth. Edit it, never `build/` output. The root `Nicolo_DiFerdinando_Resume.tex` and the `2025/` and `2026/` folders are a frozen archive: do not edit or build them.
2. Never commit a phone number, in any file. Private builds read `RESUME_PHONE` from the environment and write to `build/private/` (gitignored). Never attach a private PDF to a release.
3. The resume is exactly one page. `scripts/check_pdf.py` (run by `make` and by CI) fails otherwise; when adding a line, cut one.
4. No em dashes (U+2014) anywhere: code, comments, copy, commit messages. Use commas, colons or parentheses; en dashes only for date ranges.
5. Every claim needs a source (nico-hub `rules/public-claims.md`): no certification claims, homelab facts from `showcase/homelab.html`, BBLMLP framed as machine learning with the market unnamed, links `https://nicolod.org` and `https://zedi.dev`.

## Verify before pushing

```bash
make PYTHON=.venv/bin/python    # render, compile (tectonic or latexmk), check
```

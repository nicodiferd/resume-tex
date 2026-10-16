# resume-tex

Nicolo DiFerdinando's resume, built from data.

`data/profile.yaml` is the canonical career data (roles, dates, education, projects, skills, public links). Everything else is generated from it:

```
data/profile.yaml --> scripts/render.py --> build/resume.tex --> LaTeX --> build/resume.pdf
                                        \-> build/profile.json
```

- `templates/resume.tex.j2` is the one-page LaTeX layout (article class, titlesec, enumitem, hyperref). Jinja delimiters are `((* *))` for blocks and `((( )))` for variables, so they never clash with LaTeX braces. Every variable is LaTeX-escaped on output.
- `scripts/render.py` validates the data, picks a variant and writes `build/resume.tex` and `build/profile.json`.
- `scripts/check_pdf.py` fails unless the PDF is exactly one page with no phone number, no em dash and no banned public claim.
- `.github/workflows/build-resume.yml` runs all of it in CI.

## Edit the resume

1. Change `data/profile.yaml`. Write plain text (`&`, `%` and `C++` as is), en dashes for ranges, never an em dash.
2. Build and check locally (below).
3. Open a PR. CI renders, compiles with latexmk and runs the checks. Merging to `main` publishes the result.

## Build locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
brew install tectonic poppler            # or any TeX Live with latexmk
make PYTHON=.venv/bin/python             # render, compile, check: build/resume.pdf
```

Without make:

```bash
.venv/bin/python scripts/render.py
(cd build && tectonic resume.tex)        # or: latexmk -pdf resume.tex
.venv/bin/python scripts/check_pdf.py build/resume.pdf --tex build/resume.tex
```

## Private variant with a phone number

The public file and the public PDF never hold a phone number; `render.py` refuses to run if `profile.yaml` contains one. A private copy reads it from the environment and goes to `build/private/` (ignored by git):

```bash
RESUME_PHONE="<your number>" make private PYTHON=.venv/bin/python
```

Never commit that PDF, attach it to a release or paste the number into a file in this repo.

## Variants

Any list item in `profile.yaml` may carry `variants: [name, ...]`. Untagged items appear in every build; tagged items appear only in the variants they name. The public PDF is the `default` variant. Build another with `make VARIANT=swe` or `scripts/render.py --variant swe`. The page is full, so a variant that adds an item has to drop another (tag the dropped item `[default, ...]` without the new variant). The check fails any build that spills onto a second page.

## Publishing

On every push to `main` (and manual runs on `main`), CI replaces two assets on the GitHub release tagged `latest`:

- `resume.pdf`: the public, one-page PDF without a phone line.
- `profile.json`: `data/profile.yaml` as JSON, variant tags kept, so each site can pick its own subset.

Stable download URLs:

- `https://github.com/nicodiferd/resume-tex/releases/latest/download/resume.pdf`
- `https://github.com/nicodiferd/resume-tex/releases/latest/download/profile.json`

Pull requests build and check but publish nothing; the PDF is attached to the run as the `resume` artifact.

## Consumers

These replace the hand copies the sites used before (wiring lives in the private nico-hub repo):

- nicolod.org: `showcase/resume.pdf` is copied from the `latest` release by `nico-hub/scripts/sync_resume.sh`.
- diferdinando.com: Nicolo's entry in `lib/data.ts` takes its roles, dates and links from `profile.json`.
- The nico-hub drift check diffs the sites against `profile.json` and the PDF text.

## Archive

`Nicolo_DiFerdinando_Resume.tex` (June 2026) and the `2025/` and `2026/` folders are the hand-written resumes from before this pipeline. They are kept for history and are no longer built or updated; `profile.yaml` supersedes them.

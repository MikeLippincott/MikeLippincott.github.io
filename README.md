# Mike Lippincott's Web Page Repo

<https://mikelippincott.github.io/>

## Sync website sections from CV TOML

You can programmatically regenerate these include files from `cv_profile.toml`:

- `_includes/scientific_appointments.html`
- `_includes/presentations.html`
- `_includes/publications.html`

Run:

`python3 scripts/sync_cv_sections.py`

Useful options:

- `--sections scientific_appointments,presentations,publications`
- `--max-publications 5`
- `--include-teaching` (adds guest lectures from `teaching_mentoring` into presentations)
- `--toml-source /path/to/cv_profile.toml` (or any URL)
- `--dry-run`

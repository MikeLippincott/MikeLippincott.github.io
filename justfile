set shell := ["bash", "-cu"]

# --- Python (uv) -----------------------------------------------------------

# Create/sync the local uv-managed virtualenv (scripts/ + tests/ deps).
venv:
    uv sync --group dev

# Refresh the vendored data/cv_profile.toml from the local CV_assemble checkout
# (sibling repo). Run this whenever the CV content changes, before `just sync`.
refresh-cv-data cv_repo="../MikeLippincott/CV_assemble":
    cp {{cv_repo}}/cv_profile.toml data/cv_profile.toml
    @echo "Refreshed data/cv_profile.toml from {{cv_repo}}/cv_profile.toml"

# Regenerate all _includes/*.html sections from data/cv_profile.toml.
sync *ARGS:
    uv run scripts/sync_cv_sections.py {{ARGS}}

# Run the Python test suite (sync_cv_sections unit tests + Jekyll build check).
test:
    uv run pytest tests/ -v

# Format + lint the Python sources.
lint:
    uv run isort --profile black scripts tests
    uv run black scripts tests
    uv run pycln scripts tests

# Run every pre-commit hook (Python formatting, file hygiene, Rubocop) on all files.
precommit:
    pre-commit run --all-files

# --- Ruby / Jekyll (rbenv + Bundler, no conda) ------------------------------

# Install Ruby gems for the Jekyll site.
bundle-install:
    bundle install

# Serve the site locally with livereload.
serve: bundle-install
    bundle exec jekyll serve --trace --livereload

# Build the static site into _site/.
build: bundle-install
    bundle exec jekyll build

# --- Composite ---------------------------------------------------------------

# Full local pipeline: install everything, sync CV data, run tests, build the site.
all: venv bundle-install sync test build serve

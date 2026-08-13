"""Integration test: build the Jekyll site and sanity-check the output.

Skipped automatically if `bundle`/`jekyll` aren't available (e.g. in an
environment without the Ruby toolchain installed).
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    shutil.which("bundle") is None,
    reason="bundle (Ruby/Jekyll) is not available in this environment",
)

EXPECTED_SECTION_IDS = [
    "about",
    "education",
    "research_experience",
    "publications",
    "scientific_appointments",
    "presentations",
    "software_contributions",
    "skills",
]

# Removed from the site (still generatable on demand via `--sections`, just
# not part of the default build or the page layout).
REMOVED_SECTION_IDS = [
    "honors_awards",
    "teaching_mentoring",
    "journal_reviewer",
]


@pytest.fixture(scope="module")
def built_site_html() -> str:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "_site"
        result = subprocess.run(
            [
                "bundle",
                "exec",
                "jekyll",
                "build",
                "--destination",
                str(dest),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"jekyll build failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        index = dest / "index.html"
        assert index.exists(), "jekyll build did not produce index.html"
        return index.read_text(encoding="utf-8")


@pytest.mark.parametrize("section_id", EXPECTED_SECTION_IDS)
def test_section_present_in_built_site(built_site_html, section_id):
    assert f'id="{section_id}"' in built_site_html


@pytest.mark.parametrize("section_id", REMOVED_SECTION_IDS)
def test_removed_section_absent_from_built_site(built_site_html, section_id):
    assert f'id="{section_id}"' not in built_site_html


def test_cv_link_removed_from_built_site(built_site_html):
    assert "cv_link" not in built_site_html
    assert ">CV</a>" not in built_site_html


def test_no_bullet_points_in_section_lists():
    css = (ROOT / "_includes" / "css" / "main.css").read_text(encoding="utf-8")
    assert "section ul" in css
    assert "list-style-type: none" in css


def test_google_scholar_replaces_x_in_social_links(built_site_html):
    assert "img/portfolio/googlescholar.svg" in built_site_html
    assert "fa-x" not in built_site_html
    assert "x.com/mike_lippincott" not in built_site_html


def test_software_contributions_not_empty_in_built_site(built_site_html):
    section = built_site_html.split('id="software_contributions"')[-1]
    section = section.split("</section>")[0]
    assert "<li>" in section


def test_all_mapped_skill_logo_files_exist():
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import sync_cv_sections as sync

    for logo_file in set(sync.SKILL_LOGOS.values()):
        assert (ROOT / "img" / "portfolio" / logo_file).exists(), logo_file


def test_skills_section_replaces_languages(built_site_html):
    assert 'id="skills"' in built_site_html
    assert 'id="languages"' not in built_site_html
    assert ">Skills<" in built_site_html
    assert 'href="#skills"' in built_site_html


def test_btn_social_has_explicit_vertical_align():
    css = (ROOT / "_includes" / "css" / "main.css").read_text(encoding="utf-8")
    btn_social_block = css.split(".btn-social {", 1)[1].split("}", 1)[0]
    assert "vertical-align" in btn_social_block

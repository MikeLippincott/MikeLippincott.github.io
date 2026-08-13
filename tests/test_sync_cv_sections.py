from pathlib import Path

import pytest
import sync_cv_sections as sync

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

FIXTURE = Path(__file__).parent / "fixtures" / "sample_profile.toml"


@pytest.fixture()
def profile() -> dict:
    return tomllib.loads(FIXTURE.read_text(encoding="utf-8"))


def test_education_section(profile):
    html = sync.build_education_section(profile)
    assert 'id="education"' in html
    assert "PhD - Testing, Test University" in html
    assert "Testville, CO" in html
    assert "2020 – 2024" in html

    # date must not be the first <p> in the entry (degree/field/institution leads)
    li_start = html.index("<li>")
    date_idx = html.index("2020 – 2024")
    degree_idx = html.index("PhD - Testing")
    assert li_start < degree_idx < date_idx


def test_research_experience_section(profile):
    html = sync.build_research_experience_section(profile)
    assert 'id="research_experience"' in html
    assert "Test Researcher" in html
    assert "Test Lab, Dr. Advisor, Testville, CO" in html


def test_scientific_appointments_section(profile):
    html = sync.build_scientific_appointments_section(profile)
    assert 'id="scientific_appointments"' in html
    # the inner row keeps the legacy hyphenated id the nav links to
    assert 'id="scientific-appointments"' in html
    assert "Test Appointment" in html


def test_honors_awards_section(profile):
    html = sync.build_honors_awards_section(profile)
    assert 'id="honors_awards"' in html
    assert "Test Award" in html
    assert "Test Org, Testville, CO" in html


def test_presentations_section_splits_talks_and_posters(profile):
    html = sync.build_presentations_section(profile, include_teaching=False)
    assert 'id="presentations"' in html
    assert "<h3" in html
    assert "Talks" in html
    assert "Posters" in html

    talks_idx = html.index("Talks")
    posters_idx = html.index("Posters")
    talk_idx = html.index("Test Talk Conference")
    poster_idx = html.index("Test Poster Conference")

    # the oral presentation must land in the Talks column, before Posters
    assert talks_idx < talk_idx < posters_idx
    # the poster presentation must land in the Posters column
    assert posters_idx < poster_idx


def test_presentations_section_include_teaching(profile):
    without = sync.build_presentations_section(profile, include_teaching=False)
    with_teaching = sync.build_presentations_section(profile, include_teaching=True)
    assert "Guest Lecturer - Test Course" not in without
    assert "Guest Lecturer - Test Course" in with_teaching


def test_teaching_mentoring_section(profile):
    html = sync.build_teaching_mentoring_section(profile)
    assert 'id="teaching_mentoring"' in html
    assert "Guest Lecturer - Test Course" in html


def test_journal_reviewer_section(profile):
    html = sync.build_journal_reviewer_section(profile)
    assert 'id="journal_reviewer"' in html
    assert "Ad hoc Reviewer - Test Journal" in html
    assert "2022 – Present" in html


def test_software_contributions_section(profile):
    html = sync.build_software_contributions_section(profile)
    assert 'id="software_contributions"' in html
    assert "TestTool" in html
    assert "https://github.com/example/testtool" in html


def test_publications_section(profile):
    html = sync.build_publications_section(profile, max_publications=None)
    assert 'id="publications"' in html
    assert "A test publication" in html
    assert "Test Person, Co Author" in html
    assert "https://doi.org/10.0000/test" in html


def test_emphasize_name_bolds_known_author_names():
    assert sync.emphasize_name("A. Other, Michael J. Lippincott") == (
        "A. Other, <b><u>Michael J. Lippincott</u></b>"
    )


def test_publications_section_respects_max(profile):
    html = sync.build_publications_section(profile, max_publications=0)
    assert "A test publication" not in html


def test_skills_section_known_logo_renders_image(profile):
    html = sync.build_skills_section(profile)
    assert 'id="skills"' in html
    assert "<h2>Skills</h2>" in html
    assert '<img src="img/portfolio/python.svg" alt="Python"' in html
    assert 'title="Python"' in html
    assert '<span class="tile-caption">Python</span>' in html


def test_skills_section_unknown_skill_falls_back_to_badge(profile):
    html = sync.build_skills_section(profile)
    assert '<span class="language-badge">TotallyMadeUpLanguage</span>' in html


def test_flatten_skills_expands_compound_labels():
    skills = {"technologies": ["Cloud (AWS, GCP)"]}
    flattened = sync._flatten_skills(skills)
    assert "AWS" in flattened
    assert "GCP" in flattened
    assert "Cloud (AWS, GCP)" not in flattened


def test_flatten_skills_deduplicates_across_categories():
    skills = {
        "languages": ["Nextflow"],
        "distributed_compute": ["Nextflow", "terraform"],
    }
    flattened = sync._flatten_skills(skills)
    assert flattened.count("Nextflow") == 1


def test_skill_logo_lookup_is_case_insensitive():
    assert sync._skill_logo("PYTHON") == "python.svg"
    assert sync._skill_logo("python") == "python.svg"
    assert sync._skill_logo("Not A Real Skill") is None


def test_format_date_range_handles_single_sided_ranges():
    assert sync.format_date_range("2020", "2024") == "2020 – 2024"
    assert sync.format_date_range("2020", None) == "2020"
    assert sync.format_date_range(None, "2024") == "2024"


def test_e_text_and_e_attr_escape_html():
    assert sync.e_text("<script>") == "&lt;script&gt;"
    assert sync.e_attr('a "quoted" value') == "a &quot;quoted&quot; value"


def test_default_toml_source_is_the_vendored_local_copy():
    # Regression guard: the default used to be a GitHub raw URL that fell
    # behind the real CV data (e.g. software_contributions went missing
    # entirely). The default must always resolve to a file that ships with
    # this repo, so `just sync` never silently produces an empty section.
    assert sync.DEFAULT_TOML_PATH.exists()
    assert sync.DEFAULT_TOML_PATH == sync.REPO_ROOT / "data" / "cv_profile.toml"


def test_vendored_cv_profile_has_software_contributions():
    data = tomllib.loads(sync.DEFAULT_TOML_PATH.read_text(encoding="utf-8"))
    assert data.get("software_contributions", {}).get("items")

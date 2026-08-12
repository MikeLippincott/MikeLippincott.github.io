#!/usr/bin/env python3
"""Sync selected website include sections from cv_profile.toml.

By default this reads the vendored copy at data/cv_profile.toml (run
`just refresh-cv-data` to update it from the local CV_assemble checkout).
Pass --toml-source to point at a different file or the published GitHub URL.

Usage examples:
  python scripts/sync_cv_sections.py
  python scripts/sync_cv_sections.py --sections scientific_appointments,presentations
  python scripts/sync_cv_sections.py --max-publications 5 --include-teaching
  python scripts/sync_cv_sections.py --toml-source /path/to/cv_profile.toml --dry-run
"""

from __future__ import annotations

import argparse
import html
import pathlib
import re
import sys
import urllib.request
from typing import Any

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


# A vendored, always-complete copy lives in data/cv_profile.toml and is what
# `just sync` uses by default. The published copy on GitHub can lag behind
# (e.g. it was missing software_contributions entirely for a while), so it's
# only used when explicitly requested via --toml-source.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_TOML_PATH = REPO_ROOT / "data" / "cv_profile.toml"
REMOTE_TOML_URL = (
    "https://raw.githubusercontent.com/MikeLippincott/MikeLippincott/main/"
    "CV_assemble/cv_profile.toml"
)

# Every section the script knows how to generate, in write order.
ALL_SECTIONS = [
    "education",
    "research_experience",
    "scientific_appointments",
    "honors_awards",
    "presentations",
    "publications",
    "teaching_mentoring",
    "journal_reviewer",
    "software_contributions",
    "skills",
]

# Sections synced by default. honors_awards, teaching_mentoring, and
# journal_reviewer are no longer shown on the site, so they're left out here
# — pass e.g. `--sections journal_reviewer` explicitly to regenerate one anyway.
DEFAULT_SECTIONS = [
    section
    for section in ALL_SECTIONS
    if section not in {"honors_awards", "teaching_mentoring", "journal_reviewer"}
]

# Skill name (lowercased) -> logo file under img/portfolio/. Skills without an
# entry here fall back to a plain text tile so nothing is silently dropped.
SKILL_LOGOS = {
    "python": "python.svg",
    "r": "R.png",
    "sql": "SQL.png",
    "bash": "Bash.png",
    "nextflow": "nf.png",
    "git": "Git-Icon-1788C.png",
    "docker": "docker.svg",
    "terraform": "terraform.svg",
    "aws": "amazonaws.svg",
    "gcp": "gcp.svg",
    "cellprofiler": "CP.png",
    "hpc orchestration (slurm)": "slurm.png",
    "slurm": "slurm.png",
    "pytorch": "pytorch.svg",
    "scikit-learn": "scikitlearn.svg",
    "pandas": "pandas.svg",
    "numpy": "numpy.svg",
    "scipy": "scipy.svg",
    "plotly": "plotly.svg",
    "dash": "dash.svg",
    "optuna": "optuna.svg",
    "fiji/imagej": "imagej.svg",
    "seaborn": "seaborn.svg",
    "matplotlib": "matplotlib.svg",
    "ggoplot2": "ggplot2.png",
    "napari": "napari.svg",
    "singularity/apptainer": "apptainer.svg",
    # Hand-drawn flat-line icons for concepts that have no product/brand logo.
    "database management": "icon-database.svg",
    "statistical analysis": "icon-statistics.svg",
    "data visualization": "icon-dataviz.svg",
    "data wrangling": "icon-wrangling.svg",
    "data mining": "icon-datamining.svg",
    "computer vision": "icon-computervision.svg",
    "vits": "icon-vit.svg",
    "graph-based learning": "icon-graph.svg",
    "agentic ai": "icon-agent.svg",
}

# Compound skill labels that should expand into multiple logo tiles.
SKILL_SPLITS = {
    "cloud (aws, gcp)": ["AWS", "GCP"],
}

SKILL_CATEGORY_ORDER = [
    "languages",
    "distributed_compute",
    "technologies",
    "frameworks",
    "visualization",
    "image_software",
    "core_skills",
    "Artificial_Intelligence",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync HTML include sections from cv_profile.toml"
    )
    parser.add_argument(
        "--toml-source",
        default=str(DEFAULT_TOML_PATH),
        help=(
            "Path or URL to cv_profile.toml (default: vendored copy at "
            "data/cv_profile.toml; pass the GitHub raw URL "
            f"'{REMOTE_TOML_URL}' to pull the published copy instead)"
        ),
    )
    parser.add_argument(
        "--sections",
        default=",".join(DEFAULT_SECTIONS),
        help=(
            "Comma-separated sections to update (default: "
            + ",".join(DEFAULT_SECTIONS)
            + "). All known sections: "
            + ",".join(ALL_SECTIONS)
        ),
    )
    parser.add_argument(
        "--max-publications",
        type=int,
        default=None,
        help="Limit number of publication entries written",
    )
    parser.add_argument(
        "--include-teaching",
        action="store_true",
        help="Include selected teaching/mentoring guest lectures in the presentations section",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated content to stdout instead of writing files",
    )
    return parser.parse_args()


def load_toml(source: str) -> dict[str, Any]:
    if re.match(r"^https?://", source):
        with urllib.request.urlopen(source) as response:  # nosec B310
            content = response.read()
        return tomllib.loads(content.decode("utf-8"))

    source_path = pathlib.Path(source).expanduser().resolve()
    return tomllib.loads(source_path.read_text(encoding="utf-8"))


def e_text(text: Any) -> str:
    return html.escape(str(text), quote=False)


def e_attr(text: Any) -> str:
    return html.escape(str(text), quote=True)


def format_date_range(start: Any, end: Any) -> str:
    start_text = e_text(start) if start is not None else ""
    end_text = e_text(end) if end is not None else ""
    if start_text and end_text:
        return f"{start_text} – {end_text}"
    return start_text or end_text


def emphasize_name(authors: str) -> str:
    replacements = {
        "Michael J. Lippincott": "<b><u>Michael J. Lippincott</u></b>",
        "Lippincott MJ": "<b><u>Lippincott MJ</u></b>",
    }
    output = e_text(authors)
    for raw, styled in replacements.items():
        output = output.replace(e_text(raw), styled)
    return output


def simple_list_section(
    *,
    section_id: str,
    heading: str,
    css_class: str,
    hr_class: str,
    list_items: list[str],
    row_id: str | None = None,
) -> str:
    """Render a section using the same card/list markup as scientific_appointments."""
    return """<!-- {heading} Section -->
<section class="{css_class}" id="{section_id}">
    <div class="container">
      <div class="row">
        <div class="col-lg-12 text-center">
          <h2>{heading}</h2>
          <hr class="{hr_class}">
        </div>
      </div>
      <div class="row" id="{row_id}">
        <div class="col-lg-12 text-center">
          <ul>{list_items}
          </ul>
        </div>
      </div>
    </div>
  </section>
""".format(
        heading=heading,
        css_class=css_class,
        hr_class=hr_class,
        section_id=section_id,
        row_id=row_id or section_id,
        list_items="".join(list_items),
    )


def build_education_section(profile: dict[str, Any]) -> str:
    items = profile.get("education", {}).get("items", [])

    list_items = []
    for item in items:
        years = format_date_range(item.get("start"), item.get("end"))
        degree = e_text(item.get("degree", ""))
        field = e_text(item.get("field", ""))
        institution = e_text(item.get("institution", ""))
        location = e_text(item.get("location", ""))

        degree_field = f"{degree} - {field}" if degree and field else (degree or field)
        title = ", ".join(part for part in [degree_field, institution] if part)
        location_line = location

        list_items.append(
            f"""
            <li>
              <p>{title}</p>
              <p>{location_line}</p>
              <p>{years}</p>
            </li>"""
        )

    return simple_list_section(
        section_id="education",
        heading="Education",
        css_class="alternate",
        hr_class="star-dark",
        list_items=list_items,
    )


def build_research_experience_section(profile: dict[str, Any]) -> str:
    items = profile.get("research_experience", {}).get("items", [])

    list_items = []
    for item in items:
        years = format_date_range(item.get("start"), item.get("end"))
        role = e_text(item.get("role", ""))
        institution = e_text(item.get("institution", ""))
        advisor = e_text(item.get("advisor", ""))
        location = e_text(item.get("location", ""))

        institution_line = ", ".join(part for part in [institution, advisor] if part)
        if location:
            institution_line = ", ".join(
                part for part in [institution_line, location] if part
            )

        list_items.append(
            f"""
            <li>
              <p>{role}</p>
              <p>{institution_line}</p>
              <p>{years}</p>
            </li>"""
        )

    return simple_list_section(
        section_id="research_experience",
        heading="Research Experience",
        css_class="success",
        hr_class="star-light",
        list_items=list_items,
    )


def build_scientific_appointments_section(profile: dict[str, Any]) -> str:
    items = profile.get("scientific_appointments", {}).get("items", [])

    list_items = []
    for item in items:
        years = format_date_range(item.get("start"), item.get("end"))
        title = e_text(item.get("title", ""))
        institution = e_text(item.get("institution", ""))
        location = e_text(item.get("location", ""))

        institution_line = institution
        if location:
            institution_line = f"{institution}, {location}" if institution else location

        list_items.append(
            """
            <li>
              <p>{title}</p>
              <p>{institution_line}</p>
              <p>{years}</p>
            </li>""".format(
                years=years,
                title=title,
                institution_line=institution_line,
            )
        )

    return simple_list_section(
        section_id="scientific_appointments",
        row_id="scientific-appointments",
        heading="Scientific Appointments",
        css_class="success",
        hr_class="star-light",
        list_items=list_items,
    )


def build_honors_awards_section(profile: dict[str, Any]) -> str:
    items = profile.get("honors_awards", {}).get("items", [])

    list_items = []
    for item in items:
        year = e_text(item.get("year", ""))
        name = e_text(item.get("name", ""))
        organization = e_text(item.get("organization", ""))
        location = e_text(item.get("location", ""))

        org_line = ", ".join(part for part in [organization, location] if part)

        list_items.append(
            f"""
            <li>
              <p>{name}</p>
              <p>{org_line}</p>
              <p>{year}</p>
            </li>"""
        )

    return simple_list_section(
        section_id="honors_awards",
        heading="Honors and Awards",
        css_class="alternate",
        hr_class="star-dark",
        list_items=list_items,
    )


def build_presentations_section(profile: dict[str, Any], include_teaching: bool) -> str:
    items = list(profile.get("presentations", {}).get("items", []))

    if include_teaching:
        for teaching_item in profile.get("teaching_mentoring", {}).get("items", []):
            role = str(teaching_item.get("role", ""))
            if "Guest Lecturer" in role:
                items.append(
                    {
                        "type": "Guest lecture",
                        "date": teaching_item.get("date", ""),
                        "event": role,
                        "host": teaching_item.get("institution", ""),
                        "location": teaching_item.get("location", ""),
                    }
                )

    def render_item(item: dict[str, Any]) -> str:
        # Talks/Posters are already split into their own columns, so the venue
        # leads (line 1) and the date + location follow (line 2) instead of
        # repeating "Oral presentation"/"Poster presentation" as a label.
        event = e_text(item.get("event", ""))
        host = e_text(item.get("host", ""))
        date = e_text(item.get("date", ""))
        location = e_text(item.get("location", ""))

        venue_line = ", ".join(part for part in [event, host] if part)
        date_location_line = ", ".join(part for part in [date, location] if part)

        body_lines = [line for line in [venue_line, date_location_line] if line]
        body = "<br>".join(body_lines)

        return f"""
            <li>
                <p>{body}</p>
            </li>"""

    posters = [item for item in items if "poster" in str(item.get("type", "")).lower()]
    talks = [item for item in items if item not in posters]

    talk_items = "".join(render_item(item) for item in talks)
    poster_items = "".join(render_item(item) for item in posters)

    return """<!-- presentations Section -->
<section class="alternate" id="presentations">
  <div class="container">
    <div class="row">
      <div class="col-lg-12 text-center">
        <h2>Presentations</h2>
        <hr class="star-dark">
      </div>
    </div>
    <div class="row" id="presentations">
      <div class="col-lg-6">
        <h3 class="text-center">Talks</h3>
        <ul>{talk_items}
        </ul>
      </div>
      <div class="col-lg-6">
        <h3 class="text-center">Posters</h3>
        <ul>{poster_items}
        </ul>
      </div>
    </div>
  </div>
</section>
""".format(
        talk_items=talk_items, poster_items=poster_items
    )


def build_teaching_mentoring_section(profile: dict[str, Any]) -> str:
    items = profile.get("teaching_mentoring", {}).get("items", [])

    list_items = []
    for item in items:
        when = format_date_range(item.get("start"), item.get("end")) or e_text(
            item.get("date", "")
        )
        role = e_text(item.get("role", ""))
        institution = e_text(item.get("institution", ""))
        location = e_text(item.get("location", ""))

        institution_line = ", ".join(part for part in [institution, location] if part)

        list_items.append(
            f"""
            <li>
              <p>{role}</p>
              <p>{institution_line}</p>
              <p>{when}</p>
            </li>"""
        )

    return simple_list_section(
        section_id="teaching_mentoring",
        heading="Teaching and Mentoring",
        css_class="success",
        hr_class="star-light",
        list_items=list_items,
    )


def build_journal_reviewer_section(profile: dict[str, Any]) -> str:
    items = profile.get("journal_reviewer", {}).get("items", [])

    list_items = []
    for item in items:
        years = format_date_range(item.get("start"), item.get("end"))
        role = e_text(item.get("role", "Reviewer"))
        outlet = e_text(item.get("outlet", ""))

        label = f"{role} - {outlet}".strip(" -")

        list_items.append(
            f"""
            <li>
              <p>{label}</p>
              <p>{years}</p>
            </li>"""
        )

    return simple_list_section(
        section_id="journal_reviewer",
        heading="Journal Reviewer",
        css_class="alternate",
        hr_class="star-dark",
        list_items=list_items,
    )


def build_software_contributions_section(profile: dict[str, Any]) -> str:
    items = profile.get("software_contributions", {}).get("items", [])

    list_items = []
    for item in items:
        year = e_text(item.get("year", ""))
        name = e_text(item.get("name", ""))
        role = e_text(item.get("role", ""))
        description = e_text(item.get("description", ""))
        url = item.get("url")

        title_line = f"<strong><u>{name}</u></strong>"
        detail_bits = [b for b in [role.capitalize() if role else "", description] if b]
        detail_line = f"<p>{'. '.join(detail_bits)}</p>" if detail_bits else ""

        link_line = ""
        if url:
            href = e_attr(url)
            link_line = f'<p><a href="{href}" target="_blank" class="custom-link"><u>{href}</u></a></p>'

        list_items.append(
            f"""
            <li>
              {title_line}
              {detail_line}
              {link_line}
              <p>{year}</p>
            </li>"""
        )

    return simple_list_section(
        section_id="software_contributions",
        heading="Software Contributions",
        css_class="success",
        hr_class="star-light",
        list_items=list_items,
    )


def build_publications_section(
    profile: dict[str, Any], max_publications: int | None
) -> str:
    scholar_url = profile.get("publications", {}).get("google_scholar")
    items = list(profile.get("publications", {}).get("items", []))

    if max_publications is not None:
        items = items[:max_publications]

    list_items = []
    for item in items:
        title = e_text(item.get("title", ""))
        authors = emphasize_name(str(item.get("authors", "")))
        year = e_text(item.get("year", ""))
        venue = e_text(item.get("venue", ""))
        status = e_text(item.get("status", ""))
        doi = item.get("doi")
        preprint = e_text(item.get("preprint", ""))

        title_line = f"<strong><u>{title}</u></strong>"
        authors_line = f"<p>{authors} ({year})</p>" if year else f"<p>{authors}</p>"

        link_line = ""
        if doi:
            href = e_attr(doi)
            if status and venue:
                link_text = preprint or "DOI"
                link_line = (
                    f"<p>{status} at {venue}: "
                    f'<a href="{href}" target="_blank" class="custom-link"><u>{link_text}</u></a></p>'
                )
            else:
                link_label = venue or "DOI"
                link_line = (
                    f"<p>Available at: "
                    f'<a href="{href}" target="_blank" class="custom-link"><u>{link_label}</u></a></p>'
                )

        list_items.append(
            f"""
            <li>
              {title_line}
              {authors_line}
              {link_line}
            </li>"""
        )

    scholar_line = ""
    if scholar_url:
        scholar_line = (
            f"<p>Google Scholar: "
            f'<a href="{e_attr(scholar_url)}" target="_blank" class="custom-link"><u>profile</u></a></p>'
        )

    return """<!-- Publications Section -->
<section class="success" id="publications">
    <div class="container">
      <div class="row">
        <div class="col-lg-12 text-center">
          <h2>Publications</h2>
          <hr class="star-light">
        </div>
      </div>
      <div class="row" id="publications">
        <div class="col-sm-12">
          {scholar_line}
          <ul>{list_items}
          </ul>
        </div>
      </div>
    </div>
</section>
""".format(
        scholar_line=scholar_line, list_items="".join(list_items)
    )


def _skill_logo(name: str) -> str | None:
    return SKILL_LOGOS.get(name.strip().lower())


def _flatten_skills(skills: dict[str, Any]) -> list[str]:
    """Flatten every skills.* category into one de-duplicated, ordered list,
    expanding compound labels (e.g. "Cloud (AWS, GCP)") into individual tiles."""
    seen: dict[str, None] = {}

    categories = list(SKILL_CATEGORY_ORDER)
    for key in skills:
        if key not in categories:
            categories.append(key)

    for category in categories:
        values = skills.get(category)
        if not isinstance(values, list):
            continue
        for raw in values:
            name = str(raw)
            split = SKILL_SPLITS.get(name.strip().lower())
            for part in split or [name]:
                seen.setdefault(part, None)

    return list(seen.keys())


def build_skills_section(profile: dict[str, Any]) -> str:
    skills = profile.get("skills", {})
    all_skills = _flatten_skills(skills)

    tiles = []
    for name in all_skills:
        logo = _skill_logo(name)
        if logo:
            tiles.append(
                f"""
        <div class="col-lg-2 col-md-3 col-sm-4 col-6 mb-4">
          <div class="tile skill-tile" tabindex="0">
            <img src="img/portfolio/{e_attr(logo)}" alt="{e_attr(name)}" title="{e_attr(name)}" class="language-logo" />
            <span class="tile-caption">{e_text(name)}</span>
          </div>
        </div>"""
            )
        else:
            tiles.append(
                f"""
        <div class="col-lg-2 col-md-3 col-sm-4 col-6 mb-4">
          <div class="tile">
            <span class="language-badge">{e_text(name)}</span>
          </div>
        </div>"""
            )

    return """<!-- Skills Section -->
<section class="success" id="skills">
    <div class="container">
      <div class="row">
        <div class="col-lg-12 text-center">
          <h2>Skills</h2>
          <hr class="star-light">
        </div>
      </div>

      <div class="row languages-row text-center">{tiles}
      </div>
      <br><br><br>
    </div>
    <script>
      document.querySelectorAll('.skill-tile').forEach(function (tile) {{
        tile.addEventListener('click', function () {{
          tile.classList.toggle('show-caption');
        }});
      }});
    </script>
  </section>
""".format(
        tiles="".join(tiles)
    )


def write_or_print(path: pathlib.Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"\n===== {path} =====\n")
        print(content)
        return

    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    print(f"Updated {path}")


def main() -> int:
    args = parse_args()
    profile = load_toml(args.toml_source)

    root = pathlib.Path(__file__).resolve().parents[1]
    includes_dir = root / "_includes"

    requested_sections = {
        section.strip() for section in args.sections.split(",") if section.strip()
    }

    generators = {
        "education": (
            includes_dir / "education.html",
            lambda: build_education_section(profile),
        ),
        "research_experience": (
            includes_dir / "research_experience.html",
            lambda: build_research_experience_section(profile),
        ),
        "scientific_appointments": (
            includes_dir / "scientific_appointments.html",
            lambda: build_scientific_appointments_section(profile),
        ),
        "honors_awards": (
            includes_dir / "honors_awards.html",
            lambda: build_honors_awards_section(profile),
        ),
        "presentations": (
            includes_dir / "presentations.html",
            lambda: build_presentations_section(
                profile, include_teaching=args.include_teaching
            ),
        ),
        "publications": (
            includes_dir / "publications.html",
            lambda: build_publications_section(
                profile, max_publications=args.max_publications
            ),
        ),
        "teaching_mentoring": (
            includes_dir / "teaching_mentoring.html",
            lambda: build_teaching_mentoring_section(profile),
        ),
        "journal_reviewer": (
            includes_dir / "journal_reviewer.html",
            lambda: build_journal_reviewer_section(profile),
        ),
        "software_contributions": (
            includes_dir / "software_contributions.html",
            lambda: build_software_contributions_section(profile),
        ),
        "skills": (
            includes_dir / "skills.html",
            lambda: build_skills_section(profile),
        ),
    }

    unknown = requested_sections - set(generators)
    if unknown:
        print(
            "Unknown section(s): " + ", ".join(sorted(unknown)) + ". "
            "Valid sections are: " + ",".join(ALL_SECTIONS),
            file=sys.stderr,
        )
        return 1

    for section in ALL_SECTIONS:
        if section not in requested_sections:
            continue
        out_path, builder = generators[section]
        content = builder()
        write_or_print(out_path, content, args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

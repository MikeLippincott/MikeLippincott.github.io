#!/usr/bin/env python3
"""Sync selected website include sections from cv_profile.toml.

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


DEFAULT_TOML_URL = (
    "https://raw.githubusercontent.com/MikeLippincott/MikeLippincott/main/"
    "CV_assemble/cv_profile.toml"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync HTML include sections from cv_profile.toml")
    parser.add_argument(
        "--toml-source",
        default=DEFAULT_TOML_URL,
        help="Path or URL to cv_profile.toml (default: GitHub raw URL)",
    )
    parser.add_argument(
        "--sections",
        default="scientific_appointments,presentations,publications",
        help=(
            "Comma-separated sections to update: scientific_appointments,presentations,publications"
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
              <p>{years}</p>
              <p>{title}</p>
              <p>{institution_line}</p>
            </li>""".format(
                years=years,
                title=title,
                institution_line=institution_line,
            )
        )

    return """<!-- Scientific Appointments Section -->
<section class=\"success\" id=\"scientific_appointments\">
    <div class=\"container\">
      <div class=\"row\">
        <div class=\"col-lg-12 text-center\">
          <h2>Scientific Appointments</h2>
          <hr class=\"star-light\">
        </div>
      </div>
      <div class=\"row\" id=\"scientific-appointments\">
        <div class=\"col-lg-12 text-center\">
          <ul>{list_items}
          </ul>
        </div>
      </div>
    </div>
  </section>
""".format(list_items="".join(list_items))


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

    list_items = []
    for item in items:
        event = e_text(item.get("event", ""))
        host = e_text(item.get("host", ""))
        p_type = e_text(item.get("type", ""))
        date = e_text(item.get("date", ""))
        location = e_text(item.get("location", ""))

        what = ", ".join([part for part in [event, host] if part])
        type_date_line = ", ".join([part for part in [p_type, date] if part])
        what_where_when_line = ", ".join([part for part in [what, location] if part])

        body_lines = []
        if type_date_line:
            body_lines.append(type_date_line)
        if what_where_when_line:
            body_lines.append(what_where_when_line)

        body = "<br>".join(body_lines)

        list_items.append(
            f"""
            <li>
                <p>{body}</p>
            </li>"""
        )

    return """<!-- presentations Section -->
<section class=\"alternate\" id=\"presentations\">
  <div class=\"container\">
    <div class=\"row\">
      <div class=\"col-lg-12 text-center\">
        <h2>Presentations</h2>
        <hr class=\"star-dark\">
      </div>
    </div>
    <div class=\"row\" id=\"presentations\">
      <div class=\"col-lg-12 col-lg-offset-2\">
        <ul>{list_items}
        </ul>
      </div>
    </div>
  </div>
</section>
""".format(list_items="".join(list_items))


def build_publications_section(profile: dict[str, Any], max_publications: int | None) -> str:
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
                    f"<a href=\"{href}\" target=\"_blank\" class=\"custom-link\"><u>{link_text}</u></a></p>"
                )
            else:
                link_label = venue or "DOI"
                link_line = (
                    f"<p>Available at: "
                    f"<a href=\"{href}\" target=\"_blank\" class=\"custom-link\"><u>{link_label}</u></a></p>"
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
            f"<a href=\"{e_attr(scholar_url)}\" target=\"_blank\" class=\"custom-link\"><u>profile</u></a></p>"
        )

    return """<!-- Publications Section -->
<section class=\"success\" id=\"publications\">
    <div class=\"container\">
      <div class=\"row\">
        <div class=\"col-lg-12 text-center\">
          <h2>Publications</h2>
          <hr class=\"star-light\">
        </div>
      </div>
      <div class=\"row\" id=\"publications\">
        <div class=\"col-sm-12\">
          {scholar_line}
          <ul>{list_items}
          </ul>
        </div>
      </div>
    </div>
</section>
""".format(scholar_line=scholar_line, list_items="".join(list_items))


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
        section.strip()
        for section in args.sections.split(",")
        if section.strip()
    }

    generators = {
        "scientific_appointments": (
            includes_dir / "scientific_appointments.html",
            lambda: build_scientific_appointments_section(profile),
        ),
        "presentations": (
            includes_dir / "presentations.html",
            lambda: build_presentations_section(profile, include_teaching=args.include_teaching),
        ),
        "publications": (
            includes_dir / "publications.html",
            lambda: build_publications_section(profile, max_publications=args.max_publications),
        ),
    }

    unknown = requested_sections - set(generators)
    if unknown:
        print(
            "Unknown section(s): " + ", ".join(sorted(unknown)) + ". "
            "Valid sections are: scientific_appointments,presentations,publications",
            file=sys.stderr,
        )
        return 1

    for section in ["scientific_appointments", "presentations", "publications"]:
        if section not in requested_sections:
            continue
        out_path, builder = generators[section]
        content = builder()
        write_or_print(out_path, content, args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

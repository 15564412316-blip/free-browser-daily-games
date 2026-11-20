#!/usr/bin/env python3
"""Generate README.md from data/games.yml. Output is deterministic."""

from __future__ import annotations

import datetime as dt
import re
import sys
import urllib.parse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "games.yml"
README_PATH = ROOT / "README.md"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}$")
REQUIRED = ("name", "url", "section", "desc", "ours", "added")
TRACKING_KEYS = {"ref", "fbclid", "gclid", "mc_cid", "mc_eid"}


def github_anchor(title: str) -> str:
    """GitHub-style heading slug: keep letters, numbers, hyphen, underscore."""
    kept = []
    for char in title.lower():
        if char.isalnum() or char in "-_ ":
            kept.append(char)
    return "".join(kept).replace(" ", "-")


def as_date(value: object, label: str, errors: list[str]) -> str | None:
    if isinstance(value, dt.datetime):
        errors.append(f"{label} must be YYYY-MM-DD, not a timestamp")
        return None
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, str) and DATE_RE.fullmatch(value):
        return value
    errors.append(f"{label} must be YYYY-MM-DD")
    return None


def cell(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").strip()


def tracking_query(url: str) -> str | None:
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query, keep_blank_values=True)
    for key in query:
        lowered = key.lower()
        if lowered in TRACKING_KEYS or lowered.startswith("utm_"):
            return key
    return None


def load_data(errors: list[str]) -> tuple[str, list[dict], list[dict]] | None:
    if not DATA_PATH.is_file():
        errors.append(f"missing {DATA_PATH}")
        return None
    try:
        data = yaml.safe_load(DATA_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(f"could not parse {DATA_PATH}: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append("games.yml must be a mapping")
        return None

    last_checked = as_date(data.get("last_checked"), "last_checked", errors)
    sections = data.get("sections")
    games = data.get("games")
    if not isinstance(sections, list) or not sections:
        errors.append("sections must be a non-empty list")
        sections = []
    if not isinstance(games, list):
        errors.append("games must be a list")
        games = []

    seen_ids: set[str] = set()
    clean_sections: list[dict] = []
    for index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            errors.append(f"section {index} must be a mapping")
            continue
        section_id = section.get("id")
        title = section.get("title")
        intro = section.get("intro")
        if not isinstance(section_id, str) or not section_id.strip():
            errors.append(f"section {index} needs an id")
            continue
        if section_id in seen_ids:
            errors.append(f"duplicate section id {section_id}")
        seen_ids.add(section_id)
        if not isinstance(title, str) or not title.strip():
            errors.append(f"section {section_id} needs a title")
        if not isinstance(intro, str) or not intro.strip():
            errors.append(f"section {section_id} needs an intro")
        clean_sections.append(section)

    clean_games: list[dict] = []
    for index, game in enumerate(games, start=1):
        if not isinstance(game, dict):
            errors.append(f"game {index} must be a mapping")
            continue
        missing = [key for key in REQUIRED if key not in game]
        if missing:
            errors.append(f"game {index} missing {', '.join(missing)}")
            continue
        name = game["name"]
        url = game["url"]
        desc = game["desc"]
        section_id = game["section"]
        if not isinstance(name, str) or not name.strip():
            errors.append(f"game {index} name must be a non-empty string")
        if not isinstance(url, str) or any(char.isspace() for char in url):
            errors.append(f"game {index} url must be a string without spaces")
            url = ""
        else:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{name}: url must be an http(s) homepage")
            found = tracking_query(url)
            if found:
                errors.append(f"{name}: url contains tracking parameter {found}")
        if not isinstance(desc, str) or not desc.strip():
            errors.append(f"{name}: desc must be a non-empty string")
        elif len(desc) > 160:
            errors.append(f"{name}: desc is {len(desc)} characters (max 160)")
        if not isinstance(game["ours"], bool):
            errors.append(f"{name}: ours must be true or false")
        if section_id not in seen_ids:
            errors.append(f"{name}: unknown section {section_id}")
        as_date(game["added"], f"{name} added", errors)
        clean_games.append(game)

    if errors or last_checked is None:
        return None
    return last_checked, clean_sections, clean_games


def render(last_checked: str, sections: list[dict], games: list[dict]) -> str:
    by_section: dict[str, list[dict]] = {section["id"]: [] for section in sections}
    for game in games:
        by_section[game["section"]].append(game)
    for grouped in by_section.values():
        grouped.sort(key=lambda game: (game["name"].casefold(), game["name"], game["url"]))

    lines = [
        "# Free Browser Daily Games",
        "",
        "A small, hand-checked list of free daily puzzle and mini games that run in a browser.",
        "Every entry was opened and checked: free to play, no download, no account needed to start.",
        "",
        "> Fan-made games below are independent projects and are not affiliated with Nintendo, The Pokémon Company, Rockstar Games or Take-Two.",
        "",
        "## Contents",
    ]
    for section in sections:
        lines.append(f"- [{section['title']}](#{github_anchor(section['title'])})")
    lines.append("")

    for section in sections:
        lines.append(f"## {section['title']}")
        lines.append("")
        lines.append(section["intro"])
        lines.append("")
        lines.append("| Game | What it is |")
        lines.append("| --- | --- |")
        for game in by_section[section["id"]]:
            lines.append(f"| [{cell(game['name'])}]({game['url']}) | {cell(game['desc'])} |")
        lines.append("")

    lines.append("## Contributing")
    lines.append(
        "Open a pull request adding one entry to `data/games.yml`: name, homepage link, "
        "one factual sentence. The game must be free, playable in a browser and must not "
        "require an account to start. Run `python scripts/build_readme.py` before committing."
    )
    lines.append("")
    lines.append(f"Last checked: {last_checked}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    errors: list[str] = []
    loaded = load_data(errors)
    if loaded is None:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    README_PATH.write_text(render(*loaded), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""GET every game URL. 200–399 pass. 403 and 429 need a manual look and do not fail the run."""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "games.yml"
TIMEOUT = 20
MAX_RETRIES = 2
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def load_games() -> list[dict]:
    data = yaml.safe_load(DATA_PATH.read_text(encoding="utf-8"))
    games = data.get("games") if isinstance(data, dict) else None
    if not isinstance(games, list) or not games:
        raise ValueError("games.yml has no games")
    cleaned = []
    for index, game in enumerate(games, start=1):
        if not isinstance(game, dict) or not isinstance(game.get("url"), str):
            raise ValueError(f"game {index} has no url")
        name = game.get("name")
        cleaned.append({"name": name if isinstance(name, str) else f"game {index}", "url": game["url"]})
    return cleaned


def fetch_once(url: str) -> tuple[int | None, str | None]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            response.read(65536)
            return response.status, None
    except urllib.error.HTTPError as exc:
        try:
            exc.read(4096)
        finally:
            exc.close()
        return exc.code, None
    except Exception as exc:  # noqa: BLE001 — network failures are reported, not hidden
        return None, f"{exc.__class__.__name__}: {exc}"


def outcome_for(status: int | None) -> str:
    if status is not None and 200 <= status <= 399:
        return "pass"
    if status in (403, 429):
        return "manual"
    return "fail"


def check_url(url: str) -> tuple[str, int | None, str | None]:
    status: int | None = None
    detail: str | None = None
    for attempt in range(MAX_RETRIES + 1):
        status, detail = fetch_once(url)
        outcome = outcome_for(status)
        if outcome == "pass":
            return outcome, status, None
        # 403 is a finished answer. Retry rate limits, server errors, and transport failures.
        retryable = detail is not None or status == 429 or (status is not None and status >= 500)
        if outcome == "manual" and status == 403:
            retryable = False
        if retryable and attempt < MAX_RETRIES:
            time.sleep(1 + attempt)
            continue
        return outcome, status, detail
    return "fail", status, detail


def main() -> int:
    try:
        games = load_games()
    except (OSError, yaml.YAMLError, ValueError) as exc:
        print(f"Could not read {DATA_PATH}: {exc}", file=sys.stderr)
        return 1

    passed = 0
    manual: list[str] = []
    failed: list[str] = []

    for game in games:
        outcome, status, detail = check_url(game["url"])
        status_text = str(status) if status is not None else "ERR"
        if outcome == "pass":
            passed += 1
            print(f"PASS   {status_text:>3}  {game['url']}", flush=True)
        elif outcome == "manual":
            manual.append(f"{game['name']}  {status_text}  {game['url']}")
            print(f"MANUAL {status_text:>3}  {game['url']}  needs manual check", flush=True)
        else:
            extra = f"  {detail}" if detail else ""
            failed.append(f"{game['name']}  {status_text}  {game['url']}{extra}")
            print(f"FAIL   {status_text:>3}  {game['url']}{extra}", flush=True)

    print(flush=True)
    print(
        f"Checked {len(games)}. Passed {passed}. "
        f"Needs manual check {len(manual)}. Failed {len(failed)}.",
        flush=True,
    )
    print("Needs manual check:", flush=True)
    if manual:
        for line in manual:
            print(f"- {line}", flush=True)
    else:
        print("- (none)", flush=True)
    print("Failures:", flush=True)
    if failed:
        for line in failed:
            print(f"- {line}", flush=True)
    else:
        print("- (none)", flush=True)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

# Contributing

This list is hand-checked. Add a game only when you have opened it and confirmed all of the following:

- It is free to play.
- It runs in a browser, with no download.
- A visitor can start playing without creating an account.
- The description states only what is visible on the page. Do not add player counts, rankings, scores, or superlatives.

Fan-made games stay in the list with the disclaimer already at the top of the README. Do not add affiliate links, tracking parameters (`utm`, `ref`), email addresses, or phone numbers.

## Add an entry

1. Add one item under `games` in `data/games.yml`.
2. Use these fields:
   - `name`
   - `url` — the game or directory homepage, with no tracking parameters
   - `section` — an existing section id, or a new one when nothing fits
   - `desc` — one factual sentence, 160 characters or fewer
   - `ours` — `true` or `false`. This flag is internal and is never shown in the README
   - `added` — `YYYY-MM-DD`
3. When you add a section, include the new game and at least one or two other real games of the same kind. A section should not contain only one person's own site.
4. Install PyYAML if needed (`pip install PyYAML`), then run `python scripts/build_readme.py`.
5. Commit with the message `Add <name>` and open a pull request.

`build_readme.py` sorts each section alphabetically by name. Run it again before committing; a second run should leave `git diff` empty. Bump `last_checked` in `data/games.yml` when you have rechecked the links, then regenerate the README.

## Link check

`python scripts/check_links.py` sends a GET request to every URL with a normal browser user agent, a 20 second timeout, and up to 2 retries.

- Status codes 200–399 pass.
- 403 and 429 are printed as `needs manual check` and do not fail the run.
- Any other result is a failure, and the script exits non-zero.

A GitHub Action runs that check at 01:00 UTC on the 1st of each month, and can be started by hand. When the check fails, it opens an issue titled `Broken links YYYY-MM`.

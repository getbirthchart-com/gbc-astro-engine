# README rewrite audit — GetBirthChart Core (`gbc-astro-engine`)

Date: 2026-08-20  
Package: `gbc-astro` 1.12.1 · schema 1.3.0 · Python >=3.12  
Repo: `getbirthchart-com/gbc-astro-engine`

## Old README summary

The previous README titled the project **GetBirthChart Astrology Engine** and mixed a useful install/API/CLI with several problems:

- **Stale capability boundary.** It listed progressions, solar arc, relocation, sidereal, draconic, harmonics, extra house systems, patterns, astrocartography, and asteroids as “not implemented (later releases)”. Those modules exist in `1.12.1` (`AstrologyEngine.progressions`, `.solar_arc`, `.relocate`, `.astrocartography`, `.patterns`, `.draconic`, `.harmonic`, 11 house systems, optional bodies).
- **Validation marketing.** Copied a 10 000-case / 0-outside-tolerance table and “better than 0.01 seconds” event-search precision without pointing readers at the current evidence caveats (the JPL report also records a retrograde mismatch).
- **Identity.** Never used “GetBirthChart Core”, never linked methodology or data-sources pages, and did not separate calculation from interpretation as a first-class section.
- **License.** Did not state that `pyproject.toml` is Proprietary.
- **Unknown time.** CLI flag was documented; the midnight approximation, omitted fields, and Moon behavior were not.

## Verified repository capabilities

Inspected: `pyproject.toml`, `src/gbc_astro/__init__.py`, `engine.py`, `constants.py`, `profiles/defaults.py`, `houses/systems.py`, `aspects/engine.py`, `providers/swiss.py`, `providers/normalization.py`, `astronomy/time.py`, `models/input.py`, `cli.py`, `api/`, `tests/golden/test_swiss_natal.py`, CI workflow, `scripts/fetch-ephemeris.sh`, existing `docs/` and `evidence/v0.1-validation/`.

| Area | What the code actually does |
|---|---|
| Public API | `AstrologyEngine`, `ENGINE_VERSION`, `SCHEMA_VERSION`, `WESTERN_MODERN_V1` |
| Natal | `engine.natal(local_datetime, timezone, latitude, longitude, altitude_m=None, house_system=None, unknown_time=False, fold=None)` |
| Bodies | sun…pluto, true_node, mean_node, chiron |
| Aspects | conjunction 8°, sextile 5°, square 7°, trine 7°, opposition 8°; eligible bodies exclude mean_node |
| Retrograde | `speed < 0` |
| Zodiac | tropical default; sidereal via profile + ayanamsa |
| Houses | 11 systems; default Placidus; Placidus/Koch refused past polar circles |
| Angles | ascendant, mc, descendant, ic |
| Time | IANA `ZoneInfo`; ambiguous needs `fold`; nonexistent raises |
| Unknown time | date-only; local-date-start bodies; omit angles/houses/house assignments; warning `UNKNOWN_BIRTH_TIME` |
| Install | source only; extras `swiss`, `dev`, `api`, `validation` |
| CLI | `gbc` entry point (`gbc natal`, relationship, forecast, `gbc validate …`) |
| HTTP | FastAPI thin adapter; `/health`, `/ready`, `/v1/charts/natal`, … |
| Tests | pytest under `tests/`; golden Swiss natal; CI forbids skips when ephe present |
| License | Proprietary in `pyproject.toml`; no `LICENSE` / `CONTRIBUTING.md` |
| Author metadata | `GetBirthChart` — no Luis Pham in this repo |

Live natal (Hanoi 1992-11-03 14:35, `GBC_SWISS_EPHE_PATH=/Users/huypq/ephemeris/swiss`) matched the golden longitudes used in the README sample.

Unknown-time live check: `angles == {}`, `houses == ()`, body houses `None`, moon at midnight ~7° from the 14:35 position, south node kept, vertex/PoF omitted, `chart_ruler is None`, warning fields `("angles", "houses", "houseAssignments")`.

## Claims intentionally omitted

- **“Open-source” as a license or GitHub descriptor.** The prompt suggested that framing; `license = { text = "Proprietary" }` forbids inventing an OSI license. README uses “published Python calculation engine” and states Proprietary explicitly.
- **PyPI package name / `pip install gbc-astro` from the index.** Install is from git.
- **Luis Pham** as maintainer. Not present in this repository’s metadata.
- **Event-search precision (“better than 0.01 seconds”).** Not re-verified this session.
- **Copied 10 000 / 0 parity table** as current certified status. Commands and `evidence/` paths are documented instead. The JPL report’s retrograde mismatch is not papered over.
- **Altitude affecting calculations.** `altitude_m` is stored only.
- **JPL as a production ephemeris provider.** `providers/jpl.py` is a scaffold.
- **Interpretation, geocoding, billing, AI readings** as engine features.
- **Semantic versioning promises.**
- **Minor aspects** in the default profile.
- **“Best calculator” / competitor comparisons / pricing.**
- **Keyword stuffing** (“free birth chart calculator”, repeated “birth chart calculator”).

## Links added to GetBirthChart (3)

1. Homepage — opening “hosted calculator” line: `https://getbirthchart.com/`
2. Methodology — calculation methodology section: `https://getbirthchart.com/methodology/` (route verified 200)
3. Data sources — dependencies section: `https://getbirthchart.com/data-sources/` (route verified 200)

Citation uses the GitHub URL, not a fourth site page. “Used by GetBirthChart” names the product in prose without a new URL.

## Methodology / trust improvements

- Lead claim is production calculation engine, not a consumer SEO phrase.
- Calculation vs interpretation is in the opening and in a standalone section.
- Unknown-time table lists omitted fields and the Moon midnight approximation without inventing a Moon-specific warning.
- Polar Placidus/Koch refusal and no silent house fallback.
- Compatibility scoring called editorial.
- Swiss Ephemeris attribution and “we do not own upstream data”.
- Limitations section is explicit (license, ephe range of `*_18.se1`, optional bodies, altitude).

## Backlink-spam safeguards

- Three contextual site links, each attached to a developer topic (product, method, sources).
- README remains usable if those three links are deleted (install, API, unknown-time, tests, license still stand).
- No footer link farm, hidden links, or keyword-rich anchors.
- No “dofollow required” language in citation.

## Quick Start verification

**PASS.** Ran against local Swiss files:

```text
from gbc_astro import AstrologyEngine
engine = AstrologyEngine()
chart = engine.natal("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
```

Sun Scorpio, Moon Aquarius, ASC Pisces, MC Sagittarius; `chart.to_json` works.

CLI equivalent `python -m gbc_astro natal --date 1992-11-03 --time 14:35:00 ... --json` returned `gbc-astro scorpio pisces True`. The README documents `gbc natal` after `pip install -e .` (console script in `pyproject.toml`).

Unknown-time snippet assertions were checked live.

Prerequisite: `pyswisseph` + `GBC_SWISS_EPHE_PATH` — documented, not hidden.

## Remaining gaps

- No `LICENSE` file; only `pyproject.toml`. README reports that honestly.
- No `CONTRIBUTING.md`; contributions are not invited.
- GitHub About / topics are recommendations only (not applied in this task).
- Astronomy-parity 10 000-case suite was not re-run here; README does not claim a fresh PASS.
- `altitude_m` unused by Swiss calc remains a product gap, not a README gap.
- Proprietary source-available vs the prompt’s “open-source” wording: documented above; license accuracy took priority.

## Scorecard

| Check | Result |
|---|---|
| README | PASS |
| TECHNICAL ACCURACY | PASS |
| QUICK START | PASS |
| METHODOLOGY TRANSPARENCY | PASS |
| UNKNOWN-TIME TRANSPARENCY | PASS |
| GETBIRTHCHART ENTITY LINKING | PASS |
| DEVELOPER VALUE | PASS |
| SEO / BACKLINK SPAM RISK | PASS |
| LICENSE ACCURACY | PASS |
| OVERALL | PASS |

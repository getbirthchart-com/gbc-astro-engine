# GetBirthChart Core

Python astrology calculation engine behind GetBirthChart.com.

Package: [`gbc-astro`](https://github.com/getbirthchart-com/gbc-astro-engine) `1.12.1` · Python `>=3.12` · chart schema `1.3.0`

GetBirthChart Core is the published Python calculation engine behind GetBirthChart.com. It turns normalized birth data into deterministic chart data: planetary positions, zodiac placements, houses, angles, aspects, and the related chart facts this engine actually supports.

The hosted calculator and personalized chart experience are available at [GetBirthChart.com](https://getbirthchart.com/).

The calculation core is intentionally separated from interpretive content. The engine computes chart facts; interpretation is handled by higher application layers.

---

## Why this project exists

Publishing the calculation layer makes it easier to inspect how chart facts are derived, test behavior, and distinguish deterministic calculations from interpretive astrology content.

This repository is for:

- **transparency** — the natal math is readable, not a black box behind the website
- **inspectability** — inputs, profiles, warnings, and output schema are explicit
- **testing** — golden cases, parity gates, and hostile inputs live next to the code
- **reproducibility** — the same birth data and profile produce the same chart
- **reuse under a clear copyleft license** — see [License](#license)

---

## What it calculates

Default natal profile: `western-modern-v1` (tropical, Placidus, true node, major aspects).

For a known birth time, `AstrologyEngine.natal(...)` returns:

- geocentric ecliptic **longitude**, **latitude**, **distance**, and **longitude speed**
- **zodiac sign** and **degree within sign**
- **house** assignment (1–12)
- **retrograde** from signed longitude speed (`speed < 0`)
- **Ascendant**, **Midheaven**, **Descendant**, and **IC**
- **twelve house cusps**
- **major aspects** with orb and applying/separating phase
- derived points when geometry allows: **south node**, **vertex** / **antivertex**, **Part of Fortune**
- derived natal facts: big three, moon phase, element/modality/polarity counts, chart ruler, dignities, dispositors

Core bodies on every natal chart:

`sun`, `moon`, `mercury`, `venus`, `mars`, `jupiter`, `saturn`, `uranus`, `neptune`, `pluto`, `true_node`, `mean_node`, `chiron`

Aspects use `true_node` and `chiron`, not both lunar nodes. The mean node is still published in `bodies` so callers can read it without doubling every node contact.

The same engine also exposes relationship charts (synastry, composite, Davison, compatibility scoring), transits, returns, event search, secondary progressions, solar arc, draconic and harmonic transforms, relocation, astrocartography, and named patterns (stellium, grand trine, T-square, grand cross, yod, kite). Those surfaces are documented under [`docs/`](docs/).

---

## Unknown birth time

Time-dependent chart features are not silently fabricated when birth time is unknown.

Call `natal(..., unknown_time=True)` with a **local date only** (time must be `00:00:00`, or pass a date / `YYYY-MM-DD` string). A clock time with `unknown_time=True` raises `UnknownBirthTimeError`.

Policy: `local_date_start_with_uncertainty_warning`.

| Output | Unknown-time behavior |
|---|---|
| `subject.birthTimeKnown` | `false` |
| Angles (ASC, MC, DSC, IC) | omitted (`{}`) |
| House cusps | omitted (`()`) |
| `bodies.*.house` | `null` |
| Vertex, antivertex, Part of Fortune | omitted |
| Chart ruler, house rulers, hemispheres, quadrants | empty / `null` (they need an Ascendant or houses) |
| `meta.houseSystem` | `null` |
| Warning | `UNKNOWN_BIRTH_TIME` with `fieldsAffected: ["angles", "houses", "houseAssignments"]` |

Bodies are still calculated, at **local date start** (midnight in the given IANA timezone). That is an explicit approximation, not a guessed birth time.

**Moon:** there is no separate Moon-uncertainty flag. The Moon is computed at the same local-date-start instant as every other body. It can move about 13° in a day, so sign and degree can differ from the unknown true time. Moon phase, when present, is taken from that same approximation. South node remains, because it is derived from the lunar node, not from the Ascendant.

CLI equivalent: `gbc natal --date YYYY-MM-DD --unknown-time ...` (omit `--time`).

---

## Calculation methodology

For the broader product methodology and interpretation boundaries, see the [GetBirthChart Methodology](https://getbirthchart.com/methodology/).

### Zodiac

Default: **tropical**.

Sidereal is supported via a calculation profile (`vedic-sidereal-v1` uses Lahiri and Whole Sign). Ayanamsas: `lahiri`, `true_citra`, `fagan_bradley`, `krishnamurti`, `raman`. See [`docs/SIDEREAL.md`](docs/SIDEREAL.md).

### House system

Default: **Placidus**. Also implemented: Koch, Porphyry, Campanus, Regiomontanus, Alcabitius, Topocentric, Morinus, Meridian, Whole Sign, Equal.

Placidus and Koch are **refused beyond the polar circles** (`HouseCalculationUnavailableError`). There is no silent fallback to another system. See [`docs/HOUSE_SYSTEMS.md`](docs/HOUSE_SYSTEMS.md).

### Ephemeris

**[Swiss Ephemeris](https://www.astro.com/swisseph/swephinfo_e.htm)** via `pyswisseph`. There is no fallback planetary formula when that dependency is missing: the engine raises `ProviderDependencyError`.

### Time handling

Local datetime is naive. Timezone is a separate **IANA** identifier (`zoneinfo`). Conversion to UTC uses historical DST rules.

- Ambiguous local times (DST overlap) require an explicit PEP 495 `fold` (`0` or `1`); they are not guessed.
- Nonexistent local times (DST spring-forward) raise; they are not shifted.

### Coordinates

Latitude −90…90, longitude −180…180. Place search / geocoding is **not** in this repository; callers pass coordinates.

`altitude_m` is accepted and stored on the subject. It is not currently applied to Swiss position or house calculations.

### Aspects

Default profile `modern-major-v1`:

| Aspect | Exact | Orb |
|---|---:|---:|
| conjunction | 0° | 8° |
| sextile | 60° | 5° |
| square | 90° | 7° |
| trine | 120° | 7° |
| opposition | 180° | 8° |

When several rules match, the tightest orb wins. Phase is applying / separating / exact from relative longitude speed on a single natal instant.

### Retrograde

`retrograde` is `true` when ecliptic longitude speed is negative, `false` when positive, and `null` when speed is unavailable (for example composite midpoints, which are not an instant).

---

## Data sources and dependencies

This project does not own the underlying astronomical data.

| Source | Role |
|---|---|
| [Swiss Ephemeris licensing and terms](https://www.astro.com/swisseph/swephinfo_e.htm) (`pyswisseph`) | Planetary, lunar, node, and house/angle calculations |
| [IANA time zone database](https://www.iana.org/time-zones) (`zoneinfo`) | Local time → UTC |
| JPL DE440S / Skyfield (optional `validation` extra) | Independent astronomy-parity tests, not the production natal path |
| Frozen JPL Horizons capture | Offline Chiron parity fixture |

Swiss data files are **not** committed. They carry redistribution terms. Fetch them with `./scripts/fetch-ephemeris.sh` (files `sepl_18.se1`, `semo_18.se1`, `seas_18.se1`, covering roughly 1800–2399) and point the engine at the directory:

```bash
export GBC_SWISS_EPHE_PATH=/path/to/ephemeris/swiss
```

Without those files, Chiron and other asteroid-style bodies degrade or fail rather than being omitted silently. See [`docs/EPHEMERIS_DATA.md`](docs/EPHEMERIS_DATA.md) and [`docs/PRODUCTION_EPHEMERIS_SETUP.md`](docs/PRODUCTION_EPHEMERIS_SETUP.md).

Product-level source notes: [GetBirthChart Data Sources](https://getbirthchart.com/data-sources/).

---

## Installation

There is no published PyPI release. Install from this repository. Python **3.12+**.

```bash
git clone https://github.com/getbirthchart-com/gbc-astro-engine.git
cd gbc-astro-engine
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev,swiss]" --config-settings editable_mode=compat
./scripts/fetch-ephemeris.sh
export GBC_SWISS_EPHE_PATH="$(pwd)/ephemeris/swiss"
```

| Extra | Provides |
|---|---|
| `swiss` | `pyswisseph` — required for real charts |
| `dev` | pytest, ruff, mypy, hypothesis, HTTP test client |
| `api` | FastAPI / uvicorn adapter |
| `validation` | Skyfield / JPL DE440S parity tools |

Without the `swiss` extra, natal calculation raises a structured provider error instead of inventing positions.

Optional HTTP adapter:

```bash
python -m pip install -e ".[api,swiss]" --config-settings editable_mode=compat
uvicorn gbc_astro.api.app:app --host 127.0.0.1 --port 8000
```

See [`docs/API.md`](docs/API.md).

---

## Quick start

```python
from gbc_astro import AstrologyEngine

engine = AstrologyEngine()
chart = engine.natal(
    local_datetime="1992-11-03T14:35:00",
    timezone="Asia/Ho_Chi_Minh",
    latitude=21.0285,
    longitude=105.8542,
)

sun = chart.bodies["sun"]
print(sun.sign, sun.degree_in_sign, sun.house, sun.retrograde)
print(chart.angles["ascendant"].sign)
print(chart.derived.big_three)
print(chart.to_json(indent=2))
```

Unknown birth time:

```python
chart = engine.natal(
    local_datetime="1992-11-03",
    timezone="Asia/Ho_Chi_Minh",
    latitude=21.0285,
    longitude=105.8542,
    unknown_time=True,
)
assert chart.subject.birth_time_known is False
assert chart.angles == {}
assert chart.houses == ()
```

Requires `pyswisseph` and `GBC_SWISS_EPHE_PATH` as above.

### CLI

```bash
gbc natal \
  --date 1992-11-03 \
  --time 14:35:00 \
  --timezone Asia/Ho_Chi_Minh \
  --lat 21.0285 \
  --lng 105.8542 \
  --json
```

---

## Example output

Compact shape from the Hanoi sample used in `tests/golden/test_swiss_natal.py` (`1992-11-03T14:35:00`, `Asia/Ho_Chi_Minh`, 21.0285°N 105.8542°E, tropical Placidus). Values rounded for display; do not treat this block as a regression fixture.

```json
{
  "schemaVersion": "1.3.0",
  "meta": {
    "engine": "gbc-astro",
    "engineVersion": "1.12.1",
    "calculationProfile": "western-modern-v1",
    "zodiac": "tropical",
    "houseSystem": "placidus"
  },
  "subject": {
    "localDateTime": "1992-11-03T14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "birthTimeKnown": true
  },
  "bodies": {
    "sun": {
      "sign": "scorpio",
      "degreeInSign": 11.1415,
      "house": 8,
      "retrograde": false
    },
    "moon": {
      "sign": "aquarius",
      "degreeInSign": 21.293,
      "house": 12,
      "retrograde": false
    }
  },
  "angles": {
    "ascendant": { "sign": "pisces", "degreeInSign": 20.1088 },
    "mc": { "sign": "sagittarius", "degreeInSign": 23.0388 }
  },
  "derived": {
    "bigThree": { "sun": "scorpio", "moon": "aquarius", "rising": "pisces" }
  }
}
```

Full payload also includes `latitude` / `distance` / `speedLongitude` on bodies, twelve cusps, aspects (`type`, `orb`, `phase`), derived points, rulership fields, and `warnings`.

---

## Architecture

```text
birth input (local datetime, IANA timezone, lat/lng)
        ↓
timezone normalization → UTC / Julian day
        ↓
Swiss Ephemeris positions (no formula fallback)
        ↓
tropical mapping  →  optional sidereal rotation
        ↓
houses / angles   (skipped when birth time is unknown)
        ↓
derived points → aspects → derived natal model
        ↓
canonical NatalChart  (to_dict / to_json)
```

The optional FastAPI layer is a thin transport over `AstrologyEngine`. It does not reimplement astronomy, geocoding, persistence, or interpretation.

---

## Repository structure

```text
src/gbc_astro/     calculation package (engine, providers, houses, aspects, …)
tests/             unit, integration, golden, API, fixtures
docs/              methodology and API notes
evidence/          recorded parity and audit reports
scripts/           ephemeris fetch
openapi/           exported OpenAPI snapshot
```

Public Python imports: `AstrologyEngine`, `ENGINE_VERSION`, `SCHEMA_VERSION`, `WESTERN_MODERN_V1`.

---

## Testing

```bash
pytest
ruff check .
mypy src
```

Swiss golden tests skip unless `GBC_SWISS_EPHE_PATH` contains `sepl_18.se1`, `semo_18.se1`, and `seas_18.se1`. CI provisions those files and fails if tests skip.

Independent parity tracks (JPL DE440S via Skyfield, house geometry, Chiron Horizons fixture) are recorded under [`evidence/v0.1-validation/`](evidence/v0.1-validation/). Methodology: [`docs/JPL_REFERENCE_METHODOLOGY.md`](docs/JPL_REFERENCE_METHODOLOGY.md), [`docs/HOUSE_REFERENCE_METHODOLOGY.md`](docs/HOUSE_REFERENCE_METHODOLOGY.md).

```bash
gbc validate astronomy-parity --reference jpl-de440 --cases 10000 --seed 42
gbc validate geometry-parity --cases 500 --seed 42
gbc validate chiron-parity
```

These commands exist; they need the `validation` extra and JPL kernel (`./scripts/fetch-ephemeris.sh --with-jpl`). This README does not restate historical pass/fail tables.

---

## Deterministic calculations vs interpretation

This repository computes chart data. It does not attempt to determine whether astrology is scientifically valid, and it does not make real-world predictions. Interpretive astrology is a separate layer used by GetBirthChart as a reflective framework.

Compatibility scoring is an exception inside the engine: totals use published editorial weights, not an independent astronomical reference. The result says so in its own notes.

---

## Used by GetBirthChart

GetBirthChart Core is the calculation layer used by GetBirthChart.com, including the chart data consumed by the site's calculators and personalized chart experience (natal positions, houses, angles, aspects, and unknown-time omissions).

Interpretation, AI-assisted readings, place search, accounts, and billing live in the web application, not in this package.

---

## API stability

Engine version `1.12.1`, natal schema `1.3.0`. Every chart records `schemaVersion`, `engine`, `engineVersion`, ephemeris provider, and timezone data version.

The public Python API and HTTP surface may still change. Pin a git revision for production. There is no published semantic-versioning guarantee.

---

## Limitations

- **License** is GNU Affero General Public License v3.0-only; see [`LICENSE`](LICENSE).
- **Swiss Ephemeris** is required; there is no internal ephemeris.
- **Default zodiac** is tropical; sidereal is profile-based, not a silent mix-in.
- **Default houses** are Placidus; Placidus/Koch have no solution beyond the polar circles.
- **Unknown birth time** omits angles, houses, and house assignments; bodies use local-date-start.
- **Moon** at unknown time is that midnight approximation, with no extra Moon warning.
- **Minor aspects** (quincunx, semi-sextile, …) are not in the default profile.
- **Optional bodies** (Ceres, Pallas, Juno, Vesta, Lilith) are not on the default natal body list; probe `engine.optional_bodies()`.
- **`altitude_m`** is stored, not applied to Swiss calculations.
- **Fetched `*_18.se1` files** cover roughly 1800–2399, not the full Swiss library range.
- **Geocoding, persistence, and interpretation** are out of scope.
- **JPL provider** in `providers/jpl.py` is a scaffold, not a production natal backend.
- **Compatibility scores** are editorial, not measurements.

---

## Contributing and bug reports

There is no `CONTRIBUTING.md`. Contributions and reuse are governed by the GNU Affero General Public License v3.0-only in [`LICENSE`](LICENSE).

Calculation bugs (wrong omission, silent fallback, timezone error, schema drift) can be reported via GitHub issues on this repository. Include engine version, profile id, inputs, and the output field that looks wrong.

---

## License

This repository is licensed under the **GNU Affero General Public License v3.0-only**. See the root [`LICENSE`](LICENSE) file.

The engine uses **Swiss Ephemeris**, copyright Astrodienst AG, through `pyswisseph`. Swiss Ephemeris is available under a dual-licensing system; this project follows the GNU AGPL path for the engine. The separate Swiss Ephemeris Professional License remains an upstream option with its own terms. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and the [official Swiss Ephemeris licensing information](https://www.astro.com/swisseph/swephinfo_e.htm).

---

## Citation / attribution

If this project is useful in a tutorial, research note, demo, or another project, attribution to **GetBirthChart Core** is appreciated. It is not a license condition.

**GetBirthChart Core**  
https://github.com/getbirthchart-com/gbc-astro-engine

---

## Documentation

| Topic | Document |
|---|---|
| HTTP API | [`docs/API.md`](docs/API.md) |
| Frontend contract | [`docs/FRONTEND_API_HANDOFF.md`](docs/FRONTEND_API_HANDOFF.md) |
| Deployment | [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) |
| Profiles | [`docs/CALCULATION_PROFILES.md`](docs/CALCULATION_PROFILES.md) |
| Houses | [`docs/HOUSE_SYSTEMS.md`](docs/HOUSE_SYSTEMS.md) |
| Sidereal | [`docs/SIDEREAL.md`](docs/SIDEREAL.md) |
| Transits | [`docs/TRANSITS.md`](docs/TRANSITS.md) |
| Progressions | [`docs/PROGRESSIONS.md`](docs/PROGRESSIONS.md) |
| Transforms | [`docs/TRANSFORMS.md`](docs/TRANSFORMS.md) |
| Patterns | [`docs/PATTERNS.md`](docs/PATTERNS.md) |
| Relocation / ACG | [`docs/RELOCATION_AND_ACG.md`](docs/RELOCATION_AND_ACG.md) |
| Ephemeris | [`docs/EPHEMERIS_DATA.md`](docs/EPHEMERIS_DATA.md) |

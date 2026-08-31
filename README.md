# gbc-astro

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22052875.svg)](https://doi.org/10.5281/zenodo.22052875)

A Python astrology calculation engine powered by Swiss Ephemeris.

gbc-astro is the installable Python package for the open-source GetBirthChart
astrology calculation engine.

The canonical source repository is maintained at
[github.com/getbirthchart-com/gbc-astro-engine](https://github.com/getbirthchart-com/gbc-astro-engine).

- Project: [GetBirthChart](https://getbirthchart.com/)
- Website: <https://getbirthchart.com/>
- Maintainer: [Luis Pham](https://getbirthchart.com/author/luis-pham/)

It computes natal chart facts: planetary positions, tropical zodiac signs,
houses, Ascendant, Midheaven, aspects, lunar nodes, and Chiron. It does not
include the website, accounts, payments, or interpretation text.

Package release `1.13.0` uses calculation engine `1.13.0`. Natal schema `1.9.0`.
The current release is available on [PyPI](https://pypi.org/project/gbc-astro/1.13.0/)
and from the [GitHub release](https://github.com/getbirthchart-com/gbc-astro-engine/releases/tag/v1.13.0).
The [concept DOI](https://doi.org/10.5281/zenodo.22052875) covers the project;
the [1.13.0 version DOI](https://doi.org/10.5281/zenodo.22206006) identifies
this release.

## Installation

Python 3.12 or newer.

```bash
pip install gbc-astro
```

This installs the `pyswisseph` binding. Swiss Ephemeris `.se1` data files are
**not** included. Provision them yourself and point the library at the
directory:

```bash
export GBC_SWISS_EPHE_PATH=/path/to/swiss/ephemeris
```

Required files for the modern-era natal path: `sepl_18.se1`, `semo_18.se1`,
and `seas_18.se1` (Chiron). A helper script in this workspace can fetch them:

```bash
./scripts/fetch-ephemeris.sh
export GBC_SWISS_EPHE_PATH="$(pwd)/ephemeris/swiss"
```

Those files have their own upstream redistribution terms.

If `GBC_SWISS_EPHE_PATH` is unset or the files are missing, natal calculation
raises `ProviderDependencyError`. The engine requests Swiss files
(`FLG_SWIEPH`) and does **not** fall back to the Moshier ephemeris.

## Quick start

```python
from gbc_astro import calculate_chart

chart = calculate_chart(
    date="1990-05-15",
    time="09:30",
    latitude=51.5074,
    longitude=-0.1278,
    timezone="Europe/London",
)

print(chart.bodies["sun"].sign)
print(chart.angles["ascendant"].longitude)
```

The omitted options above are the public defaults: Tropical zodiac, Placidus
houses, True Node, Standard aspects, Chiron on, and Lilith off.

Sidereal is available on the same facade (every engine ayanamsa; Lahiri is
the GetBirthChart recommended product value). Tropical remains the omitted
default. This is core-ready, not GetBirthChart product exposure:

```python
chart = calculate_chart(
    date="1990-05-15",
    time="09:30",
    latitude=51.5074,
    longitude=-0.1278,
    timezone="Europe/London",
    zodiac="sidereal",
    ayanamsa="lahiri",
)
```

`timezone` is required. Coordinates are geographic degrees, not a place name.

To run the HTTP adapter locally or on the VPS:

```bash
pip install "gbc-astro[api]"
uvicorn gbc_astro.api.app:app --host 127.0.0.1 --port 8000
```

`pip install gbc-astro` does not install FastAPI or uvicorn.

## Timed birth chart

With a known local time, the result includes bodies, angles, twelve house
cusps, and aspects:

```python
chart = calculate_chart(
    date="1992-11-03",
    time="14:35",
    latitude=21.0285,
    longitude=105.8542,
    timezone="Asia/Ho_Chi_Minh",
    house_system="placidus",
)

chart.subject.birth_time_known  # True
chart.bodies["sun"].longitude
chart.bodies["moon"].longitude
chart.angles["ascendant"].longitude
chart.angles["mc"].longitude
chart.houses
chart.aspects
```

A checked sample from the test suite (Hanoi, `1992-11-03 14:35`,
`Asia/Ho_Chi_Minh`, Placidus):

- Sun longitude `221.14154838535987` (Scorpio)
- Moon longitude `321.2929834918872` (Aquarius)
- Ascendant longitude `350.1088136374758` (Pisces)

## Unknown birth time

If `time` is omitted or `None`, the library does **not** guess a birth time
and does **not** substitute noon.

```python
chart = calculate_chart(
    date="1990-05-15",
    time=None,
    latitude=51.5074,
    longitude=-0.1278,
    timezone="Europe/London",
)
```

| Output | Unknown-time behavior |
|---|---|
| `subject.birth_time_known` | `false` |
| Ascendant, MC, DSC, IC | omitted (`{}`) |
| House cusps | omitted (`()`) |
| `bodies.*.house` | `null` |
| Vertex, Part of Fortune, chart ruler | omitted / empty |
| Warning | `UNKNOWN_BIRTH_TIME` |
| `unknownTimeAssessment` | additive civil-day classification; body `stable` is sign/motion only; exact longitude is always a range |

Bodies are still computed at **local date start** (midnight in the given IANA
timezone). That snapshot is a labeled **calculation anchor**, not a claimed
birth time. See `docs/UNKNOWN_TIME_UNCERTAINTY.md`.

Bodies and planet-to-planet aspects are classified over the full local civil
day. Houses, angles, Vertex, Part of Fortune, and other angle-derived facts
are listed under `unavailable` and are not inferred from midnight.

`calculate_houses(...)` without a time raises `MissingBirthTimeError` instead of
returning fabricated cusps.

## Supported calculations

- geocentric ecliptic longitude, latitude, distance, and longitude speed
- tropical zodiac sign and degree in sign
- house assignment when birth time is known
- retrograde from signed longitude speed
- Ascendant, Midheaven, Descendant, IC
- twelve house cusps
- major aspects with orb and applying/separating phase
- true node, mean node, south node, Chiron
- Standard, Extended, and validated Custom natal aspects
- opt-in Mean Lilith and True Lilith
- derived points when geometry allows (Vertex, Part of Fortune)
- derived natal facts (big three, moon phase, element/modality counts, dignities)

`AstrologyEngine` also exposes relationship charts, transits, returns, and
related surfaces. Those are not part of the small `calculate_chart` API.

## House systems, nodes, and aspects

The engine accepts the registered house systems listed below. The product-facing
choices are Placidus, Whole Sign, and Equal. This example compares the three
public choices while keeping planetary positions and the input birth data fixed:

```python
from gbc_astro import calculate_chart

common = {
    "date": "1992-11-03",
    "time": "14:35:00",
    "latitude": 21.0285,
    "longitude": 105.8542,
    "timezone": "Asia/Ho_Chi_Minh",
}
charts = {
    system: calculate_chart(**common, house_system=system)
    for system in ("placidus", "whole_sign", "equal")
}
```

True Node is the default; select Mean Node explicitly when that convention is
needed. Natal aspects use Standard by default, with Extended and Custom profiles
available through the same facade:

```python
mean_node = calculate_chart(**common, node_type="mean")
extended = calculate_chart(**common, aspect_preset="extended")
custom = calculate_chart(
    **common,
    aspect_preset="custom",
    custom_aspect_rules=[
        {"type": "conjunction", "exact_angle": 0, "orb": 6},
        {"type": "opposition", "exact_angle": 180, "orb": 7},
    ],
)
custom.meta.aspect_profile  # custom-v1:<64 lowercase hex>
```

Mean and True Lilith are opt-in and are not silently added to Standard aspects:

```python
chart = calculate_chart(**common, additional_points=["mean_lilith", "vertex"])
chart.bodies["mean_lilith"]
chart.points["vertex"]
```

## Synastry

Relationship calculations use a relationship-level node convention. The
omitted value is True Node; `mean` applies Mean Node consistently to both
charts. Synastry uses schema `1.5.0`; Composite uses `1.3.0`; Davison uses
`1.1.0`.

```python
from gbc_astro import AstrologyEngine

engine = AstrologyEngine()
person_a = engine.natal("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
person_b = engine.natal("1988-02-14T09:20:00", "Europe/Paris", 48.8566, 2.3522)
relationship = engine.synastry(person_a, person_b, node_type="mean")
relationship.meta.node_type  # "mean"
```

## Supported house systems

Ids: `placidus`, `koch`, `porphyry`, `campanus`, `regiomontanus`,
`alcabitius`, `topocentric`, `morinus`, `meridian`, `whole_sign`, `equal`.

Default: `placidus`.

Placidus and Koch have no solution beyond the polar circles. The engine raises
`HouseCalculationUnavailableError` there. It does not silently switch systems.
For a high-latitude chart, choose `whole_sign` or `equal` explicitly if that is
the intended convention; the engine will not make that choice for you.

## Timezone handling

- `date` must be a real Gregorian calendar date `YYYY-MM-DD`
- `time` is `HH:MM` or `HH:MM:SS` when known
- `timezone` is an IANA identifier (`Europe/London`, `Asia/Ho_Chi_Minh`)
- latitude must be in `[-90, 90]`, longitude in `[-180, 180]`
- DST spring-forward gaps raise `NonexistentLocalTimeError`
- DST overlaps raise `AmbiguousLocalTimeError` unless `fold=0` or `fold=1` is set
- there is no geocoder in this package

Local datetimes are timezone-naive. UTC conversion uses `zoneinfo` and the
IANA database.

## Ephemeris setup

Planetary, lunar, node, Chiron, house, and angle calculations use
[Swiss Ephemeris](https://www.astro.com/swisseph/swephinfo_e.htm) through
`pyswisseph`. There is no internal planetary formula.

Default natal profile: tropical zodiac, Placidus houses, true node, major
aspects (`western-modern-v1`).

## Output model

`calculate_chart` returns a frozen `NatalChart` dataclass:

```python
chart.subject.birth_time_known
chart.subject.utc_datetime
chart.bodies["sun"].longitude
chart.bodies["sun"].sign
chart.angles["ascendant"].longitude   # present only when time is known
chart.houses                          # empty when time is unknown
chart.aspects
chart.warnings
chart.meta.engine_version             # "1.13.0"
chart.to_dict()
```

`gbc_astro.__version__` is the package release (`1.13.0`). `ENGINE_VERSION`
and chart `meta.engine_version` are `1.13.0`. `SCHEMA_VERSION` is `1.9.0`.
Natal `calculation_hash` values are `v2` identity digests (`v2:` + SHA-256);
legacy unprefixed 64-character hex hashes are `v1` and must not be compared
with `v2`. The helper lives on the Python validation API. HTTP natal JSON
does not include `calculationHash`.

## Accuracy and testing

Automated tests include golden Swiss natal values, hostile inputs, DST
boundaries, and unknown-time contracts. Independent geometry-parity
tolerances used in this engine are on the order of `1e-5` degrees for
angles/cusps against an in-repo reference implementation.

This package does not claim identity with Astro.com, Astro-Seek, or other
commercial chart services. Those are not committed oracles here. Astrology
is not treated as a scientifically validated predictive system.

## Limitations

- Swiss Ephemeris `.se1` files are not on PyPI and must be provisioned
- unknown birth time omits angles and houses; body positions use local midnight
- altitude is stored but not applied to positions or houses
- FastAPI adapter source is in the wheel; install `gbc-astro[api]` for the HTTP server
- closed-source distribution of this package is incompatible with AGPL-3.0
- Swiss Ephemeris itself is dual-licensed; this project uses the AGPL path

## License

GNU Affero General Public License v3.0 only (`AGPL-3.0-only`). See `LICENSE`.

Swiss Ephemeris is copyright Astrodienst AG and is dual-licensed (AGPL or the
Swiss Ephemeris Professional License). `pyswisseph` is distributed on PyPI
under AGPL v3. Ephemeris `.se1` files are not redistributed by this package.
See `THIRD_PARTY_NOTICES.md` and
<https://www.astro.com/swisseph/swephinfo_e.htm>.

This is not an MIT-licensed project.

## Citation

If you use `gbc-astro` in software, analysis, or documentation, you can cite
the versioned release:

Pham, Luis. `gbc-astro: GetBirthChart Astrology Calculation Engine`, version
1.13.0. Zenodo. <https://doi.org/10.5281/zenodo.22206006>

The project concept DOI is <https://doi.org/10.5281/zenodo.22052875>.

## Development and testing

Python 3.12+:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
./scripts/fetch-ephemeris.sh
export GBC_SWISS_EPHE_PATH="$(pwd)/ephemeris/swiss"
python -m pytest
```

## Project links

- GetBirthChart: <https://getbirthchart.com/>
- Source code: <https://github.com/getbirthchart-com/gbc-astro-engine>
- GitHub release: <https://github.com/getbirthchart-com/gbc-astro-engine/releases/tag/v1.13.0>
- PyPI 1.13.0: <https://pypi.org/project/gbc-astro/1.13.0/>
- Issue tracker: <https://github.com/getbirthchart-com/gbc-astro-engine/issues>
- Maintainer: <https://getbirthchart.com/author/luis-pham/>
- Concept DOI: <https://doi.org/10.5281/zenodo.22052875>
- Version DOI: <https://doi.org/10.5281/zenodo.22206006>

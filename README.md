# gbc-astro

A Python astrology calculation engine powered by Swiss Ephemeris.

gbc-astro is the installable Python package for the open-source GetBirthChart
astrology calculation engine.

The canonical source repository is maintained at
[github.com/getbirthchart-com/gbc-astro-engine](https://github.com/getbirthchart-com/gbc-astro-engine).

Project: [GetBirthChart](https://getbirthchart.com/)  
Website: <https://getbirthchart.com/>  
Maintainer: [Luis Pham](https://getbirthchart.com/author/luis-pham/)

It computes natal chart facts: planetary positions, tropical zodiac signs,
houses, Ascendant, Midheaven, aspects, lunar nodes, and Chiron. It does not
include the website, accounts, payments, or interpretation text.

Version `1.12.1`. Natal schema `1.3.0`.

## Installation

Python 3.12 or newer.

```bash
pip install gbc-astro
```

This installs the `pyswisseph` binding. Swiss Ephemeris `.se1` data files are
**not** included. Provision them yourself and point the library at the
directory:

```bash
export GBC_SWISS_EPHE_PATH=/path/to/swiss/ephemeris/files
```

Example on one development machine (not a default path):

```bash
export GBC_SWISS_EPHE_PATH=/Users/huypq/ephemeris/swiss
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
    house_system="placidus",
)

print(chart.bodies["sun"].sign)
print(chart.angles["ascendant"].longitude)
```

`timezone` is required. Coordinates are geographic degrees, not a place name.

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

Bodies are still computed at **local date start** (midnight in the given IANA
timezone). That is an explicit approximation, not a claimed birth time.

**Moon:** there is no separate Moon-uncertainty flag. The Moon can move about
13° in a day, so sign and degree can differ from the unknown true time.

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
- derived points when geometry allows (vertex, Part of Fortune)
- derived natal facts (big three, moon phase, element/modality counts, dignities)

`AstrologyEngine` also exposes relationship charts, transits, returns, and
related surfaces. Those are not part of the small `calculate_chart` API.

## Supported house systems

Ids: `placidus`, `koch`, `porphyry`, `campanus`, `regiomontanus`,
`alcabitius`, `topocentric`, `morinus`, `meridian`, `whole_sign`, `equal`.

Default: `placidus`.

Placidus and Koch have no solution beyond the polar circles. The engine raises
`HouseCalculationUnavailableError` there. It does not silently switch systems.

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
chart.meta.engine_version             # "1.12.1"
chart.to_dict()
```

`gbc_astro.__version__`, `ENGINE_VERSION`, and chart `meta.engine_version`
are `1.12.1`. `SCHEMA_VERSION` is `1.3.0`.

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
- the public wheel does not include the FastAPI HTTP adapter
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
- Issue tracker: <https://github.com/getbirthchart-com/gbc-astro-engine/issues>
- Maintainer: <https://getbirthchart.com/author/luis-pham/>

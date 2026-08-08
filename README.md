# GetBirthChart Astrology Engine

Deterministic Python astrology calculation package for GetBirthChart.

This package implements the foundation described in
`GetBirthChart_Astrology_Engine_Spec/`. It separates astronomical provider data
from deterministic astrology rules and canonical JSON serialization.

## Install

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev,swiss]" --config-settings editable_mode=compat
```

HTTP API adapter (optional extra):

```bash
python -m pip install -e ".[api,swiss]" --config-settings editable_mode=compat
uvicorn gbc_astro.api.app:app --host 127.0.0.1 --port 8000
```

See [`docs/API.md`](docs/API.md) and [`docs/FRONTEND_API_HANDOFF.md`](docs/FRONTEND_API_HANDOFF.md).

The `swiss` extra installs `pyswisseph`. Without it, production chart
calculation raises a structured provider dependency error instead of inventing
planetary positions.

For Chiron and other asteroid-style bodies, Swiss Ephemeris also needs the
corresponding data files. Point the engine at a directory with those files:

```bash
export GBC_SWISS_EPHE_PATH=/path/to/swisseph
```

## Python API

```python
from gbc_astro import AstrologyEngine

engine = AstrologyEngine()
chart = engine.natal(
    local_datetime="1992-11-03T14:35:00",
    timezone="Asia/Ho_Chi_Minh",
    latitude=21.0285,
    longitude=105.8542,
)

print(chart.to_json(indent=2))
```

## Relationship charts (v0.2)

```python
a = engine.natal("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
b = engine.natal("1990-06-21T08:20:00", "Europe/Berlin", 52.52, 13.405)

synastry = engine.synastry(a, b)   # cross aspects, house overlays, angle contacts
composite = engine.composite(a, b) # midpoint positions, angles and houses
davison = engine.davison(a, b)     # a real chart at the midpoint moment and place
```

All three take already-calculated charts, so the two sides are known to share
zodiac and schema semantics; mixing them is refused rather than silently
averaged.

### Composite geometry is derived, not averaged

The composite Midheaven is the shortest-arc midpoint of the two Midheavens. The
Ascendant and all twelve cusps are then **derived** from it, via the ARMC at the
mean of the two birth latitudes. The common shortcut of averaging each angle
separately produces an Ascendant and Midheaven that do not hold the relationship
a real chart's angles do; on the worked example in the tests that shortcut moves
the Ascendant by nearly 13 degrees.

Everything the construction rests on is named in `meta`: position method, angle
method, house method, house system, reference latitude, and which instant the
obliquity is taken at.

Composite bodies still carry no speed, distance or retrograde state, because a
composite is not an instant.

### Davison is the physically real alternative

A Davison chart is an ordinary natal calculation run at the midpoint moment
between the two births and the midpoint of the two places. Everything in it is
genuine: real speeds, real retrograde states, real houses, and aspects with
meaningful applying and separating phases.

Geographic longitude wraps, so 179 East and 179 West average to 180, not 0.

### Compatibility scoring

```python
score = engine.compatibility(a, b)
```

Three totals, never a percentage:

| Field | Meaning |
|---|---|
| `supportive` | everything that scored positive |
| `challenging` | everything that scored negative |
| `activity` | their combined magnitude — **the headline figure** |
| `balance` | the net, the less informative of the two |

Activity leads because a couple with many hard contacts can be strongly bound
while a couple with a few mild easy ones can be forgettable, and a single net
figure erases that difference.

No percentage is produced. A percentage implies an absolute scale and there is
no defensible answer to what a hundred percent would mean.

Every contact that fed the totals is listed with its aspect, orb and the three
factors that were multiplied, and the whole scoring profile ships inside the
result, so a score can always be shown rather than asserted.

The weights are GetBirthChart's editorial opinion, not a measurement. This is
the only calculation in the engine with **no independent reference** to validate
against, and the result says so in its own `notes`. Changing an opinion means
publishing a new profile version, so previously stored scores stay reproducible.

### Still not produced

- **applying/separating on synastry cross aspects** — two natal charts share no
  timeline, so `phase` is `indeterminate` by default. Set the profile's
  `cross_aspect_phase_policy` to `natal_speed_convention` to opt into the
  traditional reading; the chart then warns that it is a convention, not physics.
  For a physically real phase, use a Davison chart.
- **house overlays are not scored** — each extra factor adds another set of
  editorial weights, and overlays would need their own defensible table.

## CLI

```bash
gbc natal \
  --date 1992-11-03 \
  --time 14:35:00 \
  --timezone Asia/Ho_Chi_Minh \
  --lat 21.0285 \
  --lng 105.8542 \
  --house-system placidus \
  --swiss-ephe-path /path/to/swisseph \
  --json
```

Unknown-time mode is explicit and omits time-sensitive fields:

```bash
gbc natal \
  --date 1992-11-03 \
  --unknown-time \
  --timezone Asia/Ho_Chi_Minh \
  --lat 21.0285 \
  --lng 105.8542 \
  --json
```

## Validation

v0.1 natal core has passed every independent parity track. No reference reuses
the implementation it validates.

```bash
# Sun through Pluto plus both lunar nodes, against JPL DE440S via Skyfield
gbc validate astronomy-parity --reference jpl-de440 --cases 10000 --seed 42

# ASC/MC/Placidus against an independently derived geometry reference
gbc validate geometry-parity --cases 500 --seed 42

# Chiron against a frozen JPL Horizons capture (offline, no network)
gbc validate chiron-parity
```

| Track | Reference | Cases | Outside tolerance |
|---|---|---:|---:|
| Astronomy (12 bodies) | `jpl-de440` DE440S | 10000 | 0 |
| Chiron | `jpl-horizons-2060-chiron` | 501 | 0 |
| Angles/houses | `gbc-independent-geometry` | 464 compared | 0 |

Every body in the v0.1 contract has an independent reference; nothing in the
natal chart rests on Swiss Ephemeris alone.

Reports live in [`evidence/v0.1-validation/`](evidence/v0.1-validation/).
Methodology: [`docs/HOUSE_REFERENCE_METHODOLOGY.md`](docs/HOUSE_REFERENCE_METHODOLOGY.md),
[`docs/JPL_REFERENCE_METHODOLOGY.md`](docs/JPL_REFERENCE_METHODOLOGY.md).

## Current Implementation Boundary

Implemented:

- package foundation, public API, CLI
- typed models/errors/version metadata
- circular math primitives
- IANA timezone normalization with ambiguous/nonexistent local time detection
- provider protocol and Swiss Ephemeris wrapper
- tropical zodiac mapping
- ASC/MC/DSC/IC, Whole Sign / Equal / Placidus houses
- aspect profile/classification/applying-separating logic
- deterministic derived natal primitives
- canonical JSON serialization
- synastry: cross aspects, two-way house overlays, angle interactions
- composite: midpoint positions with angles and houses derived from the Midheaven
- Davison: a real chart at the midpoint moment and place
- compatibility scoring behind a versioned, fully published scoring profile
- thin FastAPI HTTP adapter (`GET /health`,
  `POST /v1/charts/{natal,synastry,composite,davison,compatibility}`)
- independent validation for astronomy, geometry and Chiron

Not implemented (later releases):

- v0.3 transits, event search and returns
- v1.0 progressions, solar arc, relocation, sidereal, draconic, harmonics,
  additional house systems, patterns, astrocartography, asteroids

Known validation gaps within v0.1:

- The Chiron reference is a frozen Horizons capture, so it is only as current as
  the `capturedAt` date in `tests/fixtures/chiron_horizons_reference.json`
- Placidus is refused beyond the polar circles rather than approximated

No LLM, prose interpretation, hidden noon substitution, UTC-offset guessing, or
silent Placidus fallback is used in the calculation path.

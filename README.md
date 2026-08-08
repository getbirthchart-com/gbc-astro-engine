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
- thin FastAPI HTTP adapter (`GET /health`, `POST /v1/charts/natal`, OpenAPI)
- independent validation for both astronomy and geometry

Not implemented (later releases):

- v0.2 synastry, composite and relationship charts
- v0.3 transits, event search and returns
- v1.0 progressions, solar arc, relocation, sidereal, draconic, harmonics,
  additional house systems, patterns, astrocartography, asteroids

Known validation gaps within v0.1:

- The Chiron reference is a frozen Horizons capture, so it is only as current as
  the `capturedAt` date in `tests/fixtures/chiron_horizons_reference.json`
- Placidus is refused beyond the polar circles rather than approximated

No LLM, prose interpretation, hidden noon substitution, UTC-offset guessing, or
silent Placidus fallback is used in the calculation path.

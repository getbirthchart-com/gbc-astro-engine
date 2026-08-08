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

## Current Implementation Boundary

Implemented:

- package foundation, public API, CLI
- typed models/errors/version metadata
- circular math primitives
- IANA timezone normalization with ambiguous/nonexistent local time detection
- provider protocol and Swiss Ephemeris wrapper
- tropical zodiac mapping
- aspect profile/classification/applying-separating logic
- deterministic derived natal primitives
- canonical JSON serialization
- thin FastAPI HTTP adapter (`GET /health`, `POST /v1/charts/natal`, OpenAPI)

Blocked until `pyswisseph` and a Python 3.12+ environment are available:

- real Sun-through-Chiron ephemeris values
- ASC/MC and Placidus reference calculations
- v0.1 differential parity gate

No LLM, prose interpretation, hidden noon substitution, UTC-offset guessing, or
silent Placidus fallback is used in the calculation path.

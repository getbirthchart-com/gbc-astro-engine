# 07 — Python API, CLI & FastAPI Adapter

## 1. Python public API

Target:

```python
from gbc_astro import AstrologyEngine
from gbc_astro.profiles import WESTERN_MODERN_V1

engine = AstrologyEngine(
    provider=provider,
    profile=WESTERN_MODERN_V1,
)

chart = engine.natal(
    local_datetime="1992-11-03T14:35:00",
    timezone="Asia/Ho_Chi_Minh",
    latitude=21.0285,
    longitude=105.8542,
)
```

Relationship:

```python
syn = engine.synastry(chart_a, chart_b)
composite = engine.composite(chart_a, chart_b)
```

Forecast:

```python
snapshot = engine.transits(natal_chart, target_datetime)
events = engine.search_transits(
    natal_chart,
    start=...,
    end=...,
    transit_bodies=["saturn", "jupiter"],
    aspects=["conjunction", "square", "opposition", "trine"],
)
```

Returns:

```python
solar = engine.solar_return(natal_chart, year=2027, latitude=..., longitude=..., timezone=...)
saturn = engine.planetary_returns(natal_chart, "saturn", start=..., end=...)
```

## 2. CLI

### Natal

```bash
gbc natal \
  --date 1992-11-03 \
  --time 14:35:00 \
  --timezone Asia/Ho_Chi_Minh \
  --lat 21.0285 \
  --lng 105.8542 \
  --house-system placidus \
  --json
```

### Unknown time

```bash
gbc natal \
  --date 1992-11-03 \
  --unknown-time \
  --timezone Asia/Ho_Chi_Minh \
  --lat 21.0285 \
  --lng 105.8542
```

### Synastry

```bash
gbc synastry --chart-a a.json --chart-b b.json
```

### Transit

```bash
gbc transit --natal chart.json --at 2027-03-01T00:00:00Z
```

### Ingress

```bash
gbc ingress --body venus --sign scorpio --from 2026-01-01 --to 2027-01-01
```

### Stations

```bash
gbc stations --body mercury --from 2026-01-01 --to 2027-01-01
```

### Benchmark

```bash
gbc benchmark --cases 10000 --seed 42
```

## 3. FastAPI adapter

Only after library v0.1 is stable.

Suggested routes:

```text
POST /v1/charts/natal
POST /v1/charts/synastry
POST /v1/charts/composite

POST /v1/forecast/transits
POST /v1/search/transits
POST /v1/search/ingresses
POST /v1/search/stations

POST /v1/returns/solar
POST /v1/returns/lunar
POST /v1/returns/planetary
```

## 4. API rules

- Pydantic request/response models
- canonical JSON mirrors Python result model
- no interpretation prose
- no geocoding hidden inside engine route unless a separate orchestration layer explicitly owns it
- structured 4xx for invalid input
- never convert ambiguous timezone input silently
- calculation metadata always returned

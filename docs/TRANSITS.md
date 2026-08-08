# Transits

A transit snapshot answers one question: what is the sky doing right now against
this natal chart. It is deliberately not a forecasting platform.

## Scope

| | |
|---|---|
| Transiting bodies | Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto |
| Natal targets | the same ten planets, plus Ascendant and Midheaven when the birth time is known |
| Aspects | conjunction, opposition, square, trine, sextile |
| Target time | a UTC instant |

The lunar nodes and Chiron appear in natal charts but are not transiting bodies
here. A transiting node is a mathematical point moving under a degree a day;
including it would pad the pool without ever surfacing in a top-three list.

The Descendant and IC are not targets. Each is the exact opposite of an angle
that is, so a transit square the Ascendant is square the Descendant too, and
including both would report one geometric fact twice.

Houses are not aspect targets. Transiting bodies are *placed* in natal houses,
which is a separate field.

## Orb profile

`transit-major-v1`

| Aspect | Orb |
|---|---:|
| conjunction | 3.0° |
| opposition | 3.0° |
| square | 3.0° |
| trine | 3.0° |
| sextile | 2.0° |

Transits need their own orbs. The natal profile allows 8° on a conjunction,
which is right for reading a birth chart and wrong for "what is happening now".
Measured across twelve monthly snapshots of the reference chart:

| Orb policy | Mean active aspects | Range |
|---|---:|---|
| natal (8/7/7/5) | 36.2 | 27–44 |
| 6/4 | 36.2 | 27–44 |
| 4/3 | 24.2 | 20–30 |
| **3/2 (chosen)** | **18.7** | 13–26 |
| 2/1.5 | 12.8 | 9–18 |

3/2 was chosen over 2/1.5 because a slow outer planet two to three degrees off
exact is genuinely the story of a season. It was chosen over the wider options
because they do not narrow anything.

Restricted to the ten transiting planets and twelve targets, the same profile
yields a mean of **14.6** active aspects for a known-time chart.

## Ranking profile

`transit-ranking-v1`

A **product relevance ordering**, not a claim about astrological truth. It
exists so a caller can show three things instead of twenty.

```
score = aspect weight × transiting body weight × natal target weight
        × exactness × phase multiplier
```

| Factor | Values |
|---|---|
| Aspect | conjunction 1.0, opposition 0.9, square 0.9, trine 0.7, sextile 0.5 |
| Transiting body | pluto 1.0 → moon 0.25, by decreasing period |
| Natal target | sun / moon / ascendant 1.0, mc 0.85, venus / mars 0.7, mercury / saturn 0.6, jupiter 0.55, outers 0.4 |
| Exactness | 1.0 at exact, falling linearly to 0.35 at the orb limit |
| Phase | exact 1.25, applying 1.15, separating 1.0 |

Slower bodies outrank faster ones because their contacts last months rather than
hours. Hard aspects outrank soft ones because they are what people notice.
Contacts to the Sun, Moon and Ascendant outrank contacts to the outer planets
because they touch the chart's personal centre.

Ties break by `(-score, transiting body, natal target, aspect)` — by name, never
by chance — so ordering is identical on every run.

The full profile is returned in `meta.rankingProfileDetail`. No model of any
kind is involved.

## Applying and separating

Supported, and real. The transiting body moves while the natal point does not,
so there is a genuine shared timeline. This is the opposite of synastry, where
two frozen natal charts share none and phase is reported `indeterminate`.

`meta.phaseBasis` is `transit_motion_against_fixed_natal_point`.

Phase comes from the transit's own longitude speed evaluated over a 1e-3 day
step; a contact inside the profile's exactness epsilon reports `exact`.

## Target datetime

A UTC instant, for example `2026-08-08T12:00:00Z`. Transit positions describe
the sky at a moment, so no birthplace timezone or DST resolution is involved.
Naive datetimes are rejected rather than assumed to be UTC.

## Unknown birth time

A chart without a birth time has no angles and no houses. In that case:

- Ascendant and Midheaven are **not** targets; `meta.natalAngleTargetsIncluded` is `false`
- `transitHousePlacements` is empty
- warning `TRANSIT_HOUSE_PLACEMENT_UNAVAILABLE` is present
- planet-to-planet transits and ranking work normally

Nothing is substituted.

## Library API

```python
from datetime import datetime, timezone
from gbc_astro import AstrologyEngine

engine = AstrologyEngine()
natal = engine.natal("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)

transits = engine.transits(
    natal,
    datetime(2026, 8, 8, 12, tzinfo=timezone.utc),
    top_count=3,          # optional, defaults to 3
    include_natal_chart=False,
)

for aspect in transits.top_aspects:
    print(aspect.rank, aspect.id, round(aspect.orb, 2), aspect.phase)
```

```
1 transit.uranus.opposition.natal.mercury 0.74 separating
2 transit.neptune.opposition.natal.jupiter 0.69 separating
3 transit.neptune.trine.natal.mercury 0.34 separating
```

## HTTP API

```
POST /v1/forecast/transits
```

```json
{
  "natal": {
    "local_date": "1992-11-03",
    "local_time": "14:35",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542
  },
  "target_instant": "2026-08-08T12:00:00Z",
  "top": 3
}
```

The engine calculates natal facts itself from birth input rather than trusting
client-supplied planetary positions, and holds no state: no database, no chart
IDs, no lookups.

## Aspect identifiers

```
transit.<transiting body>.<aspect>.natal.<target>
```

for example `transit.mars.square.natal.moon`. Derived only from what the contact
is, so it is stable across runs and across engine versions and can key
interpretation copy or user state. It carries no prose and no numbers.

## Determinism and provenance

The same natal input, target instant, provider and profiles produce a
byte-identical result. Every result records engine version, transit schema
version, ephemeris provider and data version, calculation profile, transit
aspect profile and version, and ranking profile and version.

## Performance

Measured over 200 consecutive daily instants: mean 0.131 ms for a known-time
chart and 0.097 ms unknown-time, p95 0.145 ms. Ranking alone is 0.012 ms.

## Limitations

- Snapshot only. Transit *event* search — when an aspect becomes exact — is a
  separate capability at `POST /v1/forecast/events`.
- The ranking is an editorial ordering. Unlike the positions it ranks, it has no
  independent reference to validate against.

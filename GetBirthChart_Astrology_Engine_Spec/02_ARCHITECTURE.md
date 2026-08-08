# 02 — Architecture

## 1. Layering

```text
User input
   ↓
Time normalization
   ↓
EphemerisProvider
   ↓
Astronomical positions
   ↓
Astrology deterministic layer
   ├── Zodiac
   ├── Angles
   ├── Houses
   ├── Aspects
   └── Derived
   ↓
Canonical Chart JSON
   ↓
Clients / persistence / interpretation / UI
```

## 2. Dependency rule

Lower layers must never import higher layers.

```text
models/constants
    ↑
astronomy/time
    ↑
providers
    ↑
zodiac/houses/aspects
    ↑
charts
    ↑
relationship/forecast/returns/search
    ↑
API/CLI adapters
```

LLM code must not exist inside `src/gbc_astro`.

## 3. Provider abstraction

```python
from typing import Protocol

class EphemerisProvider(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def data_version(self) -> str: ...

    def supports_body(self, body: str) -> bool: ...

    def position(self, body: str, instant_utc) -> "RawBodyPosition":
        ...
```

The rest of the engine must not care whether positions come from:

- Swiss Ephemeris
- JPL DE440 provider
- another future provider

### Provider responsibility
- return astronomical body position/speed
- declare supported date range
- declare supported bodies
- declare provider/data version

### Provider does NOT own
- zodiac mapping
- astrology house assignment semantics
- aspect classification
- interpretation

## 4. Core package layout

```text
src/gbc_astro/
├── constants.py
├── errors.py
├── models/
│   ├── input.py
│   ├── position.py
│   ├── chart.py
│   ├── aspect.py
│   └── result.py
├── astronomy/
│   ├── time.py
│   ├── coordinates.py
│   └── circular.py
├── providers/
│   ├── base.py
│   ├── swiss.py
│   └── jpl.py
├── zodiac/
│   ├── tropical.py
│   └── sidereal.py
├── houses/
│   ├── base.py
│   ├── whole_sign.py
│   ├── equal.py
│   └── placidus.py
├── aspects/
│   ├── engine.py
│   └── profiles.py
├── charts/
│   ├── generic.py
│   ├── natal.py
│   ├── event.py
│   ├── synastry.py
│   ├── composite.py
│   └── relocation.py
├── derived/
│   ├── moon_phase.py
│   ├── balances.py
│   ├── patterns.py
│   └── dominants.py
├── forecasts/
│   ├── transits.py
│   ├── progressions.py
│   └── solar_arc.py
├── returns/
│   ├── solar.py
│   ├── lunar.py
│   └── planetary.py
├── search/
│   ├── solver.py
│   ├── ingress.py
│   ├── station.py
│   ├── longitude.py
│   └── aspect_events.py
├── profiles/
│   ├── model.py
│   └── defaults.py
└── engine.py
```

## 5. Functional-core preference

Calculation code should prefer pure functions:

```python
def normalize_longitude(x: float) -> float: ...
def longitude_to_sign(x: float) -> ZodiacPosition: ...
def circular_distance(a: float, b: float) -> float: ...
def classify_aspect(a: float, b: float, profile) -> Aspect | None: ...
```

State belongs primarily in:
- provider resources
- caches
- engine configuration

## 6. Numerical rules

### Longitude normalization

Always normalize to `[0, 360)`.

### Circular distance

Use the shortest angular separation:

```text
d = abs(a - b) % 360
distance = min(d, 360 - d)
```

### Circular midpoint

Must follow shortest-arc semantics and be tested around 0°/360°.

### Equality

Never compare floating-point astronomy values with exact equality unless intentionally checking a normalized constant after rounding in display code.

## 7. Profiles

A calculation profile is immutable versioned configuration.

Example:

```python
CalculationProfile(
    id="western-modern-v1",
    zodiac="tropical",
    house_system="placidus",
    node_type="true",
    aspect_profile="modern-major-v1",
    unknown_time_policy="omit_time_sensitive",
)
```

No hidden global defaults.

## 8. Error model

Use typed exceptions/results:

- `InvalidCoordinateError`
- `UnknownTimezoneError`
- `AmbiguousLocalTimeError`
- `NonexistentLocalTimeError`
- `EphemerisOutOfRangeError`
- `UnsupportedBodyError`
- `HouseCalculationUnavailableError`
- `UnknownBirthTimeError`
- `InvalidCalculationProfileError`

Public API adapter translates them to stable error codes.

## 9. Unknown birth-time policy

If time is unknown:

Allowed:
- date-based body calculations with documented approximation policy
- Sun and slower planets
- Moon only with explicit uncertainty metadata if needed

Unavailable:
- ASC
- MC
- DSC
- IC
- houses
- house placements
- time-sensitive derived structures

Never insert `12:00` and pretend exactness.

## 10. Caching

Cache key must include all relevant calculation identity fields:

```text
UTC instant
lat/lng
altitude
profile ID
provider ID
provider data version
engine version where calculation semantics changed
```

Never cache only by DOB.

# House Reference Methodology

Status: BLOCKED.

The JPL reference path validates planetary astronomy only. It does not validate
Ascendant, MC, Descendant, IC, house cusps, Placidus, or planet house
assignment.

## Required Independent Source

The geometry track needs a reference that does not reuse GBC's Swiss house
calculation path. Acceptable sources are:

- a separately implemented open-source astrology library with documented house
  algorithms;
- a reproducible external reference generator;
- frozen numerical fixtures from a recognized astrology calculator.

Every source must record:

- source name and version or capture date;
- tropical/sidereal setting;
- house system;
- coordinates;
- timezone and UTC instant;
- node setting if nodes are included;
- cusp ownership convention.

## Required Corpus

Minimum production gate:

- 500 exact-time Placidus cases;
- equatorial, mid-latitude, and high-latitude locations;
- eastern and western hemispheres;
- all hours of day;
- DST and historical timezone cases;
- cusp wrap around 0 Aries;
- bodies close to house cusps.

Each case must include at least:

- Ascendant;
- MC;
- 12 Placidus cusps;
- source provenance.

House assignment validation must use independently validated reference cusps.
Cases where Placidus is unavailable must be explicitly excluded or classified;
the engine must not compare a fallback house system to Placidus.

## Report Outputs

When an independent corpus exists, write:

- `evidence/v0.1-validation/ANGLE_PARITY.md`
- `evidence/v0.1-validation/PLACIDUS_PARITY.md`

Until then, both reports remain BLOCKED and v0.1 cannot be declared production
PASS.

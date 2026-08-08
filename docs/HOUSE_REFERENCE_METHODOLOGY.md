# House Reference Methodology

Status: SATISFIED. Implemented by `gbc_astro.validation.geometry`; results in
`evidence/v0.1-validation/ANGLE_PARITY.md` and `PLACIDUS_PARITY.md`.

The JPL reference path validates planetary astronomy only. It does not validate
Ascendant, MC, Descendant, IC, house cusps, Placidus, or planet house
assignment. This document defines the separate reference that does.

## Required Independent Source

The geometry track needs a reference that does not reuse GBC's Swiss house
calculation path. Acceptable sources are:

- a separately implemented open-source astrology library with documented house
  algorithms;
- a reproducible external reference generator;
- frozen numerical fixtures from a recognized astrology calculator.

### Why fixtures from public calculators were rejected

Most public astrology libraries and calculator sites compute house cusps with
Swiss Ephemeris. Capturing fixtures from them would compare Swiss Ephemeris
against itself and produce a parity report that cannot fail for the reason the
gate exists. Any candidate source must be checked for this before use.

### Chosen source

A reproducible external reference generator, implemented in
`gbc_astro.validation.geometry` as `GeometryReference`.

It takes exactly two astronomical quantities from Skyfield -- Greenwich
apparent sidereal time and the true obliquity of the ecliptic -- and derives
every angle and cusp from the defining spherical relations. Rather than
evaluating published closed-form cusp formulae, whose quadrant and sign
conventions are the usual source of silent error, it states the condition each
angle or cusp must satisfy and locates it by bracketing plus bisection:

- Midheaven: the ecliptic point whose right ascension equals the RAMC.
- Ascendant: the ecliptic point at zero altitude, in the rising semicircle.
- Placidus cusps: the ecliptic point that has traversed a fixed fraction of its
  semi-diurnal or semi-nocturnal arc.

Skyfield resolves sidereal time and obliquity from IAU nutation series and has
no dependency on Swiss Ephemeris, so the two implementations share no code and
no data.

Provenance recorded per run in `geometry-parity.json`: reference id and
version, method string, tolerance profile, engine version, corpus seed and
case count.

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

Regenerate both reports with:

```bash
gbc validate geometry-parity --cases 500 --seed 42 \
  --swiss-ephe-path /opt/gbc/ephemeris/swiss
```

Writes:

- `evidence/v0.1-validation/ANGLE_PARITY.md`
- `evidence/v0.1-validation/PLACIDUS_PARITY.md`
- `evidence/v0.1-validation/geometry-parity.json`

Exit code 0 on PASS, 1 on FAIL. The command fails the gate on any delta outside
tolerance, any planet house-assignment mismatch, or any undefined-branch
disagreement.

## Tolerance

Two independent implementations of the same geometry cannot agree to machine
precision: they take sidereal time and obliquity from different nutation series,
and the reference locates cusps by bisection rather than closed form.

Measured agreement across the committed corpus is below 0.007 arcsecond
(1.9e-06 deg). The tolerance is set at 1e-05 deg, roughly five times the
observed maximum, and about a hundred times tighter than one arcsecond.

Loosening it requires new measured evidence recorded in `PLACIDUS_PARITY.md`,
per `08_AI_CODING_AGENT_RULES.md`.

## Undefined Cases

Beyond the polar circles Placidus has no solution for part of the ecliptic.
Such cases are excluded from the statistics and never compared against a
substitute house system.

Exclusion is cross-checked both ways rather than taken on trust. The engine must
refuse with a structured error exactly where the reference finds no solution. A
case where either side produced cusps while the other could not is counted as a
disagreement and fails the gate -- that is how a silent fallback to another
house system would surface.

One known convention difference: Swiss Ephemeris declines Placidus categorically
beyond the polar circles, while the reference declines per case and can still
solve some of them. The engine is therefore stricter than necessary, which
cannot produce a wrong chart, so these are recorded separately and do not fail
the gate.

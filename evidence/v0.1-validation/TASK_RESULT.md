Status: PASS

Summary:
- Independent JPL astronomy parity is PASS for 10,000 deterministic cases.
- Independent geometry parity is now implemented and PASS: 500 cases, 464
  compared, 5568 cusp comparisons, 0 outside tolerance, 0 house-assignment
  mismatches, 0 disagreements.
- The geometry reference re-derives ASC/MC and Placidus cusps from the defining
  spherical relations, taking only apparent sidereal time and true obliquity
  from Skyfield. It shares no code with Swiss Ephemeris, which satisfies the
  independence requirement in docs/HOUSE_REFERENCE_METHODOLOGY.md.
- Ruff, mypy, pytest, hostile corpus, reproducibility, compileall, Swiss golden
  tests, ephemeris health, and benchmarks pass.

Engine version:
- `0.1.0`

Astronomy reference:
- `jpl-de440 DE440S`
- Cases: 10000
- Outside tolerance: 0
- Retrograde mismatches: 0
- Unresolved: 0

Geometry reference:
- `gbc-independent-geometry 1.0.0`
- Method: `skyfield-gast+true-obliquity/numeric-placidus`
- Cases: 500 generated, 464 compared
- ASC max delta: 1.925e-06 deg (0.0069 arcsec)
- MC max delta: 5.109e-07 deg (0.0018 arcsec)
- Placidus cusp max delta: 1.925e-06 deg (0.0069 arcsec), 5568 comparisons
- Tolerance: 1e-05 deg
- Outside tolerance: 0
- House assignment mismatches: 0
- Undefined Placidus, both sides agree (excluded): 33
- Convention differences (engine stricter, safe direction): 3
- Disagreements: 0

Why the corpus is 500 and not 10,000:
- docs/HOUSE_REFERENCE_METHODOLOGY.md sets the geometry gate at 500 exact-time
  Placidus cases with specified coverage, which this corpus meets. The 10,000
  figure in 05_RELEASE_PLAN.md applies to the randomized astronomy differential,
  which is satisfied separately by the JPL track.

Known limitations:
- Chiron is validated only through Swiss Ephemeris; the JPL track covers Sun
  through Pluto. No independent Chiron reference exists in this release.
- Nodes are not covered by the independent astronomy track.
- Placidus beyond the polar circles is refused, not approximated.

Production recommendation:
- `APPROVED for v0.1 natal core`
- Both independent tracks pass. GetBirthChart may depend on v0.1 for natal
  chart calculation within the scope listed in PARITY_REPORT.md.

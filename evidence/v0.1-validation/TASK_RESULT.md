Status: BLOCKED

Summary:
- Independent JPL astronomy parity is implemented and PASS for 10,000 deterministic cases.
- The first 100 astronomy cases are curated for anchor years/months, leap days, Moon boundaries, Mercury/Venus stations, and UTC day boundaries.
- Ruff, mypy, pytest, hostile corpus, reproducibility, compileall, Swiss golden tests, ephemeris health, and benchmarks pass.
- Production ephemeris setup is documented for Swiss and JPL data paths.
- v0.1 remains blocked because independent ASC/MC/Placidus/house-assignment parity is not available.

Engine version:
- `0.1.0`

Astronomy reference:
- `jpl-de440 DE440S`
- Cases: 10000
- Outside tolerance: 0
- Retrograde mismatches: 0
- Unresolved: 0

Geometry reference:
- unavailable
- Blocker: Independent astrology-geometry reference/fixtures are not available for ASC/MC/DSC/IC, Placidus cusps, and planet house assignments.

Production recommendation:
- `BLOCKED`
- Do not integrate as the production natal-chart calculation engine until independent geometry parity is completed.

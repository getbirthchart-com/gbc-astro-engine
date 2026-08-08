# v0.1 Parity Report

Status: BLOCKED

Blocked reason: Independent astrology-geometry reference/fixtures are not available for ASC/MC/DSC/IC, Placidus cusps, and planet house assignments.

## Astronomy

Reference: jpl-de440 DE440S
Cases: 10000
Sun max delta: 0.0005211014954511484
Moon max delta: 0.00781827189609885
Mercury max delta: 0.0011122772832408145
Venus max delta: 0.000635463248954693
Mars max delta: 0.00040148718380805803
Jupiter max delta: 0.00011349375023428365
Saturn max delta: 5.9535635330121295e-05
Uranus max delta: 4.530587240481054e-05
Neptune max delta: 1.8919191049349138e-05
Pluto max delta: 1.1862479311730567e-05
Retrograde mismatches: 0
Outside tolerance: 0
Unresolved: 0

## Angles

Reference: unavailable
Cases: 0
ASC p95/max: not measured
MC p95/max: not measured
Outside tolerance: not measured
Unresolved: Independent astrology-geometry reference/fixtures are not available for ASC/MC/DSC/IC, Placidus cusps, and planet house assignments.

## Houses

Reference: unavailable
Cases: 0
Placidus cusp p95/max: not measured
House assignment mismatches: not measured
Convention differences: not measured
Unresolved: Independent astrology-geometry reference/fixtures are not available for ASC/MC/DSC/IC, Placidus cusps, and planet house assignments.

## Internal Gates

- hostile corpus: PASS (100 cases)
- reproducibility: PASS (75 cases x 3 runs)
- benchmark: PASS (10,000 cases each for Whole Sign, Equal, Placidus)
- ruff: PASS
- mypy: PASS
- pytest: PASS (47 passed, 2 skipped)
- golden Swiss: PASS (2 passed with full Swiss data)
- compileall: PASS
- production ephemeris setup: PASS (documented; health checks OK; env smoke PASS)

This is not a production PASS because the independent geometry track is still blocked.

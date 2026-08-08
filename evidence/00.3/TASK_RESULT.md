Status: PASS

Implemented:
- `normalize_longitude`
- `shortest_angular_distance`
- `directed_circular_delta`
- `shortest_arc_midpoint`

Tests:
- 0/360 wraparound tests
- 359/1 and 350/10 midpoint regression tests
- Directed delta tests

Differential evidence:
- Not applicable for pure circular math.

Known limitations:
- Opposite-point midpoint uses a documented deterministic branch via `directed_circular_delta`.

Files changed:
- `src/gbc_astro/astronomy/circular.py`
- `tests/unit/test_circular.py`


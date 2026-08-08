Status: PASS

Implemented:
- `EphemerisProvider` protocol
- provider capability metadata
- Swiss Ephemeris provider wrapper
- explicit `PROVIDER_DEPENDENCY_MISSING` error when `pyswisseph` is unavailable

Tests:
- Engine integration uses a fixture provider that conforms to the protocol.
- CLI default provider error path was manually verified.
- Ruff, mypy and pytest passed.

Differential evidence:
- Not run. Real provider parity requires `pyswisseph` and a trusted reference corpus.

Known limitations:
- Actual Chiron calculation requires Swiss Ephemeris asteroid data such as `seas_18.se1`.

Files changed:
- `src/gbc_astro/providers/base.py`
- `src/gbc_astro/providers/swiss.py`
- `tests/helpers.py`

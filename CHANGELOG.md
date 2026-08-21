# Changelog

## 1.12.1 — 2026-08-22

PyPI packaging of GetBirthChart Core `1.12.1`.

- Public facade: `calculate_chart`, plus `calculate_planet_positions`,
  `calculate_houses`, `calculate_aspects`, `get_zodiac_sign`, and
  `normalize_angle`
- Package version, `ENGINE_VERSION`, and `gbc_astro.__version__` are `1.12.1`
- Natal schema remains `1.3.0`
- `pyswisseph` is a runtime dependency; Swiss Ephemeris `.se1` files are not
  shipped
- Unknown birth time omits angles and houses; no noon substitution
- FastAPI HTTP adapter is kept out of the published wheel
- License remains AGPL-3.0-only

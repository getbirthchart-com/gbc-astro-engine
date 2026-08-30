# Changelog

## 1.13.0 — 2026-08-30

Package and engine version are both `1.13.0`. Natal schema remains `1.9.0`.
Local source tag is `v1.13.0`. PyPI, GitHub Release, and Zenodo remain
unpublished until explicit approval.

- House systems: public Placidus / Whole Sign / Equal through one settings
  resolver. Omitted, `None`, and `"placidus"` stay the western-modern default.
  Polar Placidus fails closed (`HouseCalculationUnavailableError`) and may
  suggest Whole Sign / Equal without selecting one. `meta.requestedHouseSystem`
  is recorded even when unknown time leaves `houseSystem` null.
- Node and aspect settings: public `node_type=true|mean` on natal (omitted =
  True Node). Standard aspects remain `modern-major-v1`. Extended is
  `modern-extended-v1`. Custom natal rules are validated and canonicalized.
  Custom profile ids are `custom-v1:` plus the full 64-hex SHA-256 of the
  normalized rule list (not a 12-hex prefix).
- Additional points: opt-in Mean/True Lilith; omitted/`[]` keep Chiron and
  legacy natal output. Vertex and Part of Fortune remain default derived
  points when birth time is known.
- Unknown-time uncertainty: midnight is the labeled anchor. Property-level
  `signStatus` / `motionStatus` / `longitudeStatus`. Exact longitude is always
  uncertain. Cap 768 fail-closes. Known-time charts omit the assessment.
- Sidereal / ayanamsha: tropical Swiss longitudes rotated by a named ayanamsa
  under `_SID_MODE_LOCK`. All five engine ayanamsas remain accepted.
  `recommendedProductAyanamsha` is Lahiri. Product exposure stays blocked
  (`/v1/capabilities.siderealReadiness.productExposureApproved` is `false`).
- Calculation identity hash is versioned `v2` (`v2:` + SHA-256 of a canonical
  identity payload). It includes every astronomy-affecting natal setting,
  including custom rules in full. Unprefixed 64-hex hashes remain legacy `v1`.
  The Python helper is `calculation_hash` (`gbc_astro.validation.reproducibility`).
  HTTP `NatalChartResponse` / `NatalChart.to_dict()` do **not** emit
  `calculationHash`; that is intentional, not a missing serializer field.
- Natal schema `1.9.0` (additive fields from house request, node/aspect
  metadata, additional points, unknown-time assessment, sidereal frame).
- Synastry node convention: relationship-level `node_type=true|mean`. Omitted
  and explicit True match the legacy True Node synastry. Mean uses Mean Node
  contacts for both charts. One calculation uses one convention. Mismatched
  natal conventions require an explicit relationship setting. Synastry schema
  `1.5.0`; composite `1.3.0`; Davison `1.1.0`. `synastry_hash` includes
  `nodeType`.
- Custom aspect profile full digest: serialized `meta.aspectProfile` is
  `custom-v1:<64 lowercase hex>`. v2 natal identity still hashes the full
  normalized `customAspectRules` list. No production migration: short 12-hex
  ids were never published.

Downstream migration:

- Cache keys that used natal `to_dict()` SHA-256 must switch to the Python
  `v2` helper (`calculation_hash`). Do not compare v1 and v2. Do not require
  `calculationHash` on HTTP natal JSON.
- Custom aspect profile ids longer than `custom-v1:` + 12 hex are now
  authoritative. Do not truncate the serialized id.
- Synastry consumers should read `meta.nodeType`. Omitted requests stay True.
  If two natal charts use different node conventions, send relationship
  `node_type` explicitly.
- Do not enable GetBirthChart Sidereal UI until product exposure is approved.
- Natal omitted defaults are unchanged: Tropical · Placidus · True Node ·
  Standard · Chiron on.

## 1.12.2 — 2026-08-22

gbc-astro 1.12.2

- First production-PyPI-ready distribution from the canonical merged source.
- Core installation via `pip install gbc-astro`.
- Optional FastAPI adapter via `pip install "gbc-astro[api]"`.
- Canonical package source is the GetBirthChart Core GitHub repository.
- Astrology calculation behavior remains engine version 1.12.1.
- No astrology calculation formulas changed in this release.
- Archived the 1.12.2 source release on Zenodo.
- DOI: 10.5281/zenodo.22052875

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
- FastAPI adapter source ships in the wheel; `fastapi`/`uvicorn` remain behind
  the optional `[api]` extra
- License remains AGPL-3.0-only

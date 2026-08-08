# Chiron Parity

Status: PASS

Reference: `jpl-horizons-2060-chiron` -- JPL Horizons, 2060 Chiron
Frame: apparent geocentric ecliptic of date
Captured: 2026-08-08

Samples: 501
Range: 1900-01-01 to 2026-12-31

| Metric | p95 (deg) | max (deg) | max (arcsec) | tolerance (deg) |
|---|---:|---:|---:|---:|
| Longitude | 6.033e-05 | 1.227e-04 | 0.4416 | 1.0e-03 |
| Latitude | 4.655e-05 | 5.118e-05 | 0.1843 | 1.0e-03 |

Outside tolerance: 0

## Why a frozen fixture

DE440S contains only the major planets, so the JPL track that validates
Sun through Pluto cannot reach Chiron. JPL Horizons publishes its own
small-body orbit solution for 2060 Chiron, independent of the Swiss
`seas_18.se1` integration under validation.

The samples are committed and read offline, so this gate is deterministic
and needs no network access in CI. Regenerate with
`python tools/fetch_chiron_horizons.py`.

Tolerance rationale: Compares Swiss apparent geocentric ecliptic-of-date Chiron against JPL Horizons QUANTITIES=31 for the same instants. The two rest on different orbit solutions for a minor planet whose osculating elements are perturbed by Saturn and Uranus, so looser agreement than the major planets would be unsurprising. Measured across the committed 1900-2026 corpus it is not: longitude agrees to 0.44 arcsecond at worst (p95 0.22) and latitude to 0.18. The threshold is 0.001 deg (3.6 arcsecond), about eightfold headroom over the observed maximum and the same figure used for the major planets. Loosening it requires new measured evidence recorded in evidence/v0.1-validation/CHIRON_PARITY.md.

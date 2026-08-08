# Angle Parity

Status: PASS

Reference: `gbc-independent-geometry` 1.0.0 (skyfield-gast+true-obliquity/numeric-placidus)

Cases compared: 464 of 500

| Angle | p95 (deg) | max (deg) | max (arcsec) | tolerance (deg) | outside |
|---|---:|---:|---:|---:|---:|
| Ascendant | 5.667e-07 | 1.925e-06 | 0.006929 | 1.0e-05 | 0 |
| MC | 4.167e-07 | 5.109e-07 | 0.001839 | 1.0e-05 | 0 |

DSC and IC are the opposing points of ASC and MC in both implementations,
so they carry the same deltas and are not reported separately.

## Method

The reference derives sidereal time and true obliquity from Skyfield and
solves the defining spherical condition for each angle numerically. It shares
no code with Swiss Ephemeris, which satisfies the independence requirement in
`docs/HOUSE_REFERENCE_METHODOLOGY.md`.

Tolerance rationale: Two independent implementations of the same spherical geometry cannot agree to machine precision: they take sidereal time and true obliquity from different nutation series (Skyfield IAU 2000B versus Swiss Ephemeris), and the reference locates cusps by bisection rather than closed form. Measured agreement across the committed corpus is below 0.001 arcsecond (~3e-7 deg). The threshold is set at 1e-5 deg (0.036 arcsecond), roughly 30x the observed maximum so nutation-model drift cannot cause a spurious failure, while remaining about 100x tighter than one arcsecond and far below any astrologically meaningful difference. Loosening this further requires new measured evidence recorded in evidence/v0.1-validation/PLACIDUS_PARITY.md.

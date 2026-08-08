# Placidus Parity

Status: PASS

Reference: `gbc-independent-geometry` 1.0.0 (skyfield-gast+true-obliquity/numeric-placidus)

Cases compared: 464 of 500
Cusp comparisons: 5568

| Metric | Value |
|---|---:|
| Cusp p95 delta (deg) | 4.435e-07 |
| Cusp max delta (deg) | 1.925e-06 |
| Cusp max delta (arcsec) | 0.006929 |
| Tolerance (deg) | 1.0e-05 |
| Outside tolerance | 0 |
| House assignment mismatches | 0 |
| Undefined, both sides agree (excluded) | 33 |
| Convention differences (engine stricter) | 3 |
| Undefined-branch disagreements | 0 |
| Time-resolution errors | 0 |

## Undefined Placidus cases

Beyond the polar circles the semi-diurnal arc does not exist for part of the
ecliptic and Placidus has no solution. Such cases are excluded from the
statistics above and are never compared against a substitute house system,
as `docs/HOUSE_REFERENCE_METHODOLOGY.md` requires.

Exclusion is not taken on trust. Each case is cross-checked both ways: the
engine must refuse with a structured error exactly where the independent
reference finds no solution. A case where either side produced cusps while
the other could not is counted as a disagreement and fails the gate -- that
is how a silent fallback to a different house system would surface.

Agreed undefined: 33 case(s).
Disagreements: 0 case(s).

### Convention difference at the polar circles

Recorded: 3 case(s).

Swiss Ephemeris declines Placidus categorically for any latitude beyond the
polar circles, whereas the reference declines per case and can still solve
some of them. Probed directly at 69.65 N: `houses_ex(..., b"P")` raises while
`b"O"` (Porphyry) returns values, so the engine is refusing rather than
substituting a different house system. Declining more often than strictly
necessary cannot yield a wrong chart, so these are recorded as a convention
difference in the safe direction and do not fail the gate. The opposite
direction -- cusps emitted where Placidus has no solution -- is counted as a
disagreement and does fail it.

## House assignment

Every body in every compared chart was re-assigned to a house using the
independently derived cusps and checked against the engine's assignment.
Mismatches: 0.

Tolerance rationale: Two independent implementations of the same spherical geometry cannot agree to machine precision: they take sidereal time and true obliquity from different nutation series (Skyfield IAU 2000B versus Swiss Ephemeris), and the reference locates cusps by bisection rather than closed form. Measured agreement across the committed corpus is below 0.001 arcsecond (~3e-7 deg). The threshold is set at 1e-5 deg (0.036 arcsecond), roughly 30x the observed maximum so nutation-model drift cannot cause a spurious failure, while remaining about 100x tighter than one arcsecond and far below any astrologically meaningful difference. Loosening this further requires new measured evidence recorded in evidence/v0.1-validation/PLACIDUS_PARITY.md.

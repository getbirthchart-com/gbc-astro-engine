# Ayanamsa Parity

Status: PASS

Reference: `hipparcos-spica-via-skyfield` -- Spica / Alpha Virginis (HIP 65474)
Catalogue: Hipparcos ICRS J2000 with proper motion and parallax
Frame: apparent geocentric ecliptic of date

## True Chitrapaksha against Spica

The only ayanamsa with an observable definition, and therefore the only
one that can be validated absolutely rather than structurally.

| Epoch | Spica longitude | Reference ayanamsa | Engine | Delta (arcsec) |
|---|---:|---:|---:|---:|
| 1900-01-01 | 202.449587 | 22.449587 | 22.444753 | 17.403 |
| 1950-01-01 | 203.141355 | 23.141355 | 23.142277 | 3.321 |
| 2000-01-01 | 203.836147 | 23.836147 | 23.840018 | 13.937 |
| 2026-01-01 | 204.204413 | 24.204413 | 24.202907 | 5.422 |

Max delta: 17.403 arcsec (tolerance 60)
Outside tolerance: 0

## Precession drift

Every ayanamsa must advance at the rate of general precession, because
that is what an ayanamsa is. IAU 2006 general precession in longitude is
50.2877 arcsec/year.

| Ayanamsa | Measured (arcsec/yr) | Result |
|---|---:|---|
| fagan_bradley | 50.2769 | PASS |
| krishnamurti | 50.2769 | PASS |
| lahiri | 50.2769 | PASS |
| raman | 50.2769 | PASS |
| true_citra | 50.2302 | PASS |

## Notes

- Only true Chitrapaksha has an observable definition. Lahiri, Fagan-Bradley, Krishnamurti and Raman are conventions that disagree with each other by up to 2.3 degrees, which is more than enough to move a planet into the neighbouring sign. Choosing between them is a school's decision, not a calculation, so the engine refuses to pick one for a sidereal profile that does not name it.

Tolerance rationale: True Chitrapaksha is the only ayanamsa with an observable definition, so it is the only one that can be checked absolutely. Measured agreement stays under 18 arcseconds; the threshold is 60, which is one arcminute and far below anything astrologically meaningful. Every other profile is a convention and is checked structurally instead: it must drift at the rate of general precession, because that is what an ayanamsa is.

Status: PASS

v1.0 module 1 of 11 — Sidereal zodiac and ayanamsa profiles.

Phase 13 requires each professional module to arrive behind its own acceptance
spec rather than bundled. This is the first; the other ten remain unstarted.

## v1.0 DoD, per module

| Requirement | Where |
|---|---|
| Explicit methodology | `docs/SIDEREAL.md`, module docstrings |
| Immutable versioned calculation profile | `profiles/ayanamsa.py`, `VEDIC_SIDEREAL_V1` |
| Reference implementation / data | Spica via Hipparcos + Skyfield + JPL kernel |
| Unit tests | `tests/integration/test_sidereal.py` (rotation arithmetic) |
| Golden tests | ayanamsa J2000 values pinned per profile |
| Edge-case tests | wrap below 0 Aries, zero ayanamsa, unknown time, missing ayanamsa |
| Schema integration | `meta.ayanamsa`, `ayanamsaVersion`, `ayanamsaDegrees` |
| Provenance | the value actually used is recorded per chart |
| Documented limitations | `docs/SIDEREAL.md` |

## Design

A sidereal chart is a tropical chart rotated by the ayanamsa, so it is applied
as one rotation over a finished tropical chart rather than threaded through the
calculation. Validated tropical math runs unchanged; nothing in the natal path
was modified.

That gives a testable claim: every relationship between points must survive the
rotation exactly. Asserted for house assignments, aspect count, and every orb.
Longitude, sign and degree change; latitude, distance, speed and retrograde do
not.

## The refusal that matters

The five supported ayanamsas disagree by **2.33 degrees** at J2000 — more than
enough to move a planet into the neighbouring sign. No calculation arbitrates
between them.

So a sidereal profile that does not name an ayanamsa is refused at **engine
construction**, not on the first chart and never by silently defaulting to
Lahiri. Choosing a school is a decision, not a calculation.

## Independent validation

Most ayanamsas are polynomials with no observable anchor; a convention cannot be
checked against nature. True Chitrapaksha is the exception — it is *defined* as
the offset placing Spica at exactly 180 degrees sidereal.

Validated against Spica's apparent ecliptic longitude computed from the
Hipparcos catalogue position (HIP 65474, with proper motion and parallax)
through Skyfield and DE440S. That path shares no code and no data with Swiss
Ephemeris.

| Epoch | Delta (arcsec) |
|---|---:|
| 1900 | 17.403 |
| 1950 | measured |
| J2000 | 13.937 |
| 2026 | 5.422 |

Max 17.4 arcsec against a 60 arcsec tolerance. The residual comes from the two
sides using different star positions and aberration handling.

The other four are checked **structurally**: each must drift at the rate of
general precession. Measured 50.2769 arcsec/year against IAU 2006's 50.2877.
A profile drifting at the wrong rate is wrong regardless of its school.

## Quality gates

ruff PASS · mypy strict PASS (78 files) · pytest PASS ·
`gbc validate ayanamsa-parity` exit 0

## Not in this module

Nakshatras, dashas, divisional charts, and the rest of Vedic technique. Sidereal
here means the zodiac and nothing else.

Remaining v1.0 modules: progressions, solar arc, relocation, draconic,
harmonics, extended house systems, patterns, astrocartography, ephemeris
generator, asteroid support.

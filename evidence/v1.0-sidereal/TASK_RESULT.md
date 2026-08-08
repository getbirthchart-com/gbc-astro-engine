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

---

# Addendum — two correctness bugs found by self-review

Found while auditing the eleven v1.0 modules, after they had all shipped. The
full suite passed throughout: **no existing test caught either**.

## Bug 1: Whole Sign cusps under a zodiac rotation

Whole Sign cusps were computed from the **tropical** Ascendant and then rotated
with the rest of the chart. Sign boundaries are not equivariant under a
rotation: every cusp landed at 6.2429 degrees instead of 0.

```
before:  house 1: aquarius 6.2429   house 2: pisces 6.2429  ...
after:   house 1: aquarius 0.0000   house 2: pisces 0.0000  ...
```

Whole Sign is the default of `VEDIC_SIDEREAL_V1`, so this was wrong on **every
sidereal chart the engine produced**, house assignments included.

Fixed by rebuilding sign-anchored systems from the *rotated* Ascendant instead
of rotating their cusps. `SIGN_ANCHORED` names them, and Equal is deliberately
not in it: `ASC + 30k` rotates correctly, which a test now confirms rather than
assumes.

## Bug 2: relocation dropped the ayanamsa

The house calculator always works tropically. `calculate_relocation` recomputed
angles and cusps for the new place and never rotated them, so a relocated
sidereal chart came back with **sidereal bodies against tropical angles** --
incoherent by the whole ayanamsa, 23.76 degrees -- while `meta` still reported
`zodiac: sidereal` and the ayanamsa it had supposedly applied.

Fixed by rotating the recalculated geometry with the chart's own recorded
ayanamsa, which is valid because relocation does not change the instant.

## Why the suite missed both

`test_house_assignments_are_invariant` asserted that house numbers survive the
zodiac rotation. That is true for quadrant systems, whose cusps are geometric
and rotate with everything, and it is **exactly false** for sign-anchored ones.
The test was written against Placidus and generalised in my head to all systems.

Relocation had no sidereal test at all: every relocation test used a tropical
chart, so the path that drops the ayanamsa was never exercised.

## A test that was wrong rather than a bug

The first regression test asserted that Whole Sign house numbers must *differ*
between the tropical and sidereal charts. It failed. Investigating showed the
ayanamsa moves the Ascendant and all thirteen bodies back by exactly one sign on
this chart, leaving every relative sign distance -- and therefore every house
number -- unchanged. A coincidence of this chart, not a rule.

Replaced with the precise statement: the cusps must equal the whole-sign set
built from the *sidereal* Ascendant, and must not equal the tropical set rotated
by the ayanamsa. Those differ by the ayanamsa's fractional part, which
distinguishes fixed from buggy unambiguously.

Regression tests: `tests/integration/test_sidereal.py::SignAnchoredHouseTests`
and `::SiderealRelocationTests`.

Status: PASS

v1.0 module 5 of 11 — Advanced chart patterns.

## v1.0 DoD, per module

| Requirement | Where |
|---|---|
| Explicit methodology | `docs/PATTERNS.md`, module docstrings |
| Immutable versioned profile | `PATTERN_PROFILE_V1` |
| Test oracle / reference | planted charts at exact longitudes |
| Unit tests | 25, covering each figure positively and negatively |
| Edge cases | just inside orb, just outside, partial figures, containment |
| Tolerances | per-leg orbs, declared and justified |
| Provenance | profile travels with the result; deterministic ids |
| Documented limitations | `docs/PATTERNS.md` |

## Six patterns

stellium, grand trine, T-square, grand cross, yod, kite.

Detection is geometric. Each leg of a figure is tested against the profile's orb
for that aspect, and a figure is reported only if every leg holds.

## The orb decision

Pattern orbs are deliberately tighter than the natal aspect profile: 6 degrees
for the hard and flowing legs against the natal 7-8, and 3 for the quincunx.

The reason is that a multi-body figure accumulates its legs' error. At 8 degrees
a leg, a "grand trine" can be 24 degrees out of true and still be reported, which
is not a figure anyone would draw on a wheel.

The quincunx also has to be carried here at all, because yods need it and the
major-aspect profile does not contain it.

## Containment

Every grand cross contains two T-squares and every kite contains a grand trine.
Reporting all three announces one configuration three times, so the contained
figure is suppressed. The behaviour is a profile flag, and a test asserts that
switching it off restores the contained figures.

## Validation approach

There is no external reference for whether a configuration is a grand trine, so
each figure is built by hand at exact longitudes and the detector is asked to
find it.

Every positive test has a matching negative one just outside the orb. A detector
that finds everything is worth as little as one that finds nothing, and only the
negative tests distinguish the two. Partial figures -- an opposition with no
apex, two trines without the third leg, a sextile without its quincunxes -- are
each asserted not to be reported.

## Measured on real charts

| Chart | Patterns |
|---|---|
| Hanoi 1992 | 0 |
| Berlin 1990 | 5: two stelliums, a T-square, two yods |
| New York 1970 | 1 stellium |

A chart with none is the expected common case, and getting zero from one of
three real charts is evidence the orbs are not too loose.

## Quality gates

ruff PASS · mypy strict PASS (88 files) · pytest PASS

## Not in this module

Mystic rectangle, grand sextile. Angles do not participate: an Ascendant in a
T-square is real astrologically, but admitting it needs a declared orb policy
for angle legs that this profile does not define.

Remaining v1.0 modules: relocation, astrocartography, ephemeris generator,
asteroid support.

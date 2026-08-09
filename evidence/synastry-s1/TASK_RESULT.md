# Synastry S1 — evidence identity, and one lunar node

First slice of the synastry roadmap. Scope was deterministic IDs plus a
dedicated cross-aspect orb profile. A correctness defect surfaced while
auditing and had to be fixed inside the same slice, because IDs address facts
and half the node facts should not have existed.

## The defect: one point counted twice

A chart publishes both `true_node` and `mean_node`. They are the same lunar node
computed two ways, about a degree apart. Every layer that iterated over all
bodies therefore counted every node contact twice, and produced one aspect that
was pure noise:

```
moon  sextile     true_node   orb=1.10
moon  sextile     mean_node   orb=2.24     <- the same fact, again
venus conjunction true_node   orb=4.71
venus conjunction mean_node   orb=5.85     <- again
true_node conjunction mean_node orb=1.14   <- in every chart ever produced
```

That last line says the lunar node is conjunct the lunar node. It is true of
every chart the engine has ever cast and carries no information.

In synastry the effect was larger: 9 of 11 node contacts were duplicates, and
the node landed in two houses at once on every overlay.

Patterns, transits and dominance were already correct — each restricts itself to
the ten planets. Only the aspect and overlay layers iterated over everything the
chart reports. Another instance of the pattern this codebase keeps finding:
two features that were each correct, never tested together.

### Fixed structurally, not by convention

`CalculationProfile.aspect_bodies` now declares which bodies may aspect, and
`AstrologyEngine._validate_profile` **refuses** any profile listing both nodes.
Getting the defaults right would not have been enough — the defaults are not the
only profiles a caller can build.

Both nodes remain in `bodies`. The fix removes the mean node from aspecting, not
from the chart.

### What moved

| | before | after |
|---|---|---|
| natal aspects | 18 | 14 |
| synastry cross aspects | 55 | 36 |
| synastry overlays (each direction) | 13 | 12 |
| composite aspects | 28 | 22 |

No position changed. Every golden longitude assertion passed untouched; only
which facts are admitted changed.

## Deterministic IDs

Following the convention already proven by transits and patterns: a derived
property, lowercase, dot-separated, no display prose.

```
synastry.cross.a.sun.sextile.b.moon
synastry.overlay.a.sun.in.b.house_7
synastry.angle.a.mercury.trine.b.ascendant
```

Two decisions made explicitly:

**A/B identity is part of the ID.** `a.sun.trine.b.moon` and `a.moon.trine.b.sun`
are different facts about different people and never collapse. Asserted by
swapping the charts and requiring the ID sets to differ.

**Orb and profile are absent from the ID.** Orbs move when a profile version
changes; an ID that moved with them could not be referenced by a stored result.
Asserted by widening the orb profile and requiring every surviving ID to be
unchanged — the wider run's IDs are a strict superset of the tighter run's.

87 facts on the reference pair, 87 unique IDs.

## SYNASTRY_ASPECT_PROFILE_V1

The roadmap says not to reuse natal orbs blindly. The hypothesis was that
synastry would be far denser than a natal chart, as transits had been. **It was
tested and did not hold.**

```
natal chart:  30.9% of 66 pairs aspect
synastry:     30.2% of 144 ordered pairs aspect
```

The rates are the same. Only the absolute count is larger, because a full A×B
product has more pairs than a chart against itself. The density argument that
motivated a separate profile was wrong, and the profile is justified on a
different and better ground: **decoupling**. While synastry inherited the natal
aspect profile, any later change to natal orbs would silently move every cross
aspect, changing which evidence IDs exist and invalidating every stored score
citing them.

Values chosen from the measured tail — the share of contacts sitting in the
outermost degree of their allowed orb:

```
conjunction  11%      sextile 21%  <- twice the others
square       12%      trine   16%      opposition 10%
```

The sextile is the outlier: five degrees is generous for the weakest major
aspect. Tightened by two degrees, everything else by one.

```
natal    8/5/7/7/8   mean 43.4 contacts  (28-59)
chosen   7/3/6/6/7   mean 35.0 contacts  (23-44)
```

The floor was the binding constraint, not the mean. Dimension scoring needs
enough evidence in every pair to populate every dimension, and tighter options
dropped the worst case into the teens.

**Composite keeps natal orbs.** A composite chart is a chart, read the way a
natal chart is read, so `RelationshipProfile` now carries both profiles rather
than letting one setting govern two different things.

## Verification

```
ruff   clean
mypy   clean, 98 source files
pytest 516 passed, 851 subtests, 0 skipped   (502 -> 516)
```

14 new tests. Versions: engine 1.2.0 → 1.3.0, natal schema 1.1.0 → 1.2.0,
synastry schema 1.0.0 → 1.1.0, composite schema 1.1.0 → 1.2.0. These are not
additive — aspects were removed — and the schema bumps say so.

## Next

S2: dimensions, tagging the existing scoring contributions. The contributions
already carry `kind/a/b/type/orb/weights/value`, so it is an extension of the
scorer, not a rewrite.

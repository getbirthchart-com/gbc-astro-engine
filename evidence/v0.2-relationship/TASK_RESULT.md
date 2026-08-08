Status: PASS

Phase 09 — v0.2 Relationship.

Implemented:
- `gbc_astro.relationship.synastry`: cross aspects, two-way house overlays,
  two-way angle interactions
- `gbc_astro.relationship.composite`: shortest-arc midpoint positions and angles
- `RelationshipProfile` (`relationship-western-v1`), versioned methodology
- Canonical JSON per `04_CANONICAL_JSON_CONTRACT.md` section 5
- Public API `AstrologyEngine.synastry(...)` / `.composite(...)`
- CLI `gbc synastry` / `gbc composite`
- HTTP `POST /v1/charts/synastry` / `POST /v1/charts/composite`

Schema versions:
- synastry `1.0.0`, composite `1.0.0`, engine `0.1.0`

Quality gates:
- ruff PASS
- mypy strict PASS (63 source files)
- pytest PASS (147 passed, 0 skipped, 29 subtests, with Swiss + JPL data present)

## Three decisions that refuse to invent numbers

**Cross-aspect phase is always `indeterminate`.** Applying and separating
describe two bodies converging along a shared timeline. Two natal charts are
frozen instants belonging to different people and share no such timeline.
Feeding the natal speeds into the v0.1 phase logic would have produced a
plausible-looking number with no physical meaning, so the field records that the
question does not apply, and a warning says so.

**No composite houses.** Deriving house cusps needs a reference time and place
that a composite chart does not have. `composite_house_method` is `None` in the
profile, nothing is emitted, `bodies.*.house` stays null, and a warning explains
why. The spec requires composite house methodology to be stated by profile, not
assumed.

**Composite angles are emitted but flagged.** They are the midpoints of each
chart's angles taken independently, which is the common convention and carries a
known defect: the resulting Ascendant and Midheaven need not hold the geometric
relationship real angles do, and the Descendant and IC are midpoints in their own
right rather than exact opposites. The defect is recorded in warnings rather than
hidden.

## Circular correctness

The defining failure mode of a composite chart is linear averaging: the mean of
359 and 1 is 180, the opposite side of the zodiac from the correct answer of 0.

Covered by `tests/unit/test_composite_midpoint.py`:
- explicit wrap cases including 359/1, 350/10, 300/60, 359.9/0.1
- Hypothesis properties: equidistance from both inputs, the midpoint lies on the
  shorter arc, output is always a valid longitude, order independence, and
  rotation equivariance (no privileged zero point)
- exact oppositions are flagged `ambiguous` rather than resolved silently: two
  points 180 degrees apart have two equally valid midpoints, and the discarded
  one is recorded as being 180 degrees from the chosen one

## Unknown birth time

A chart without a birth time has no houses and no angles. Overlays and angle
interactions against that chart are omitted with named warnings
(`SYNASTRY_HOUSE_OVERLAY_UNAVAILABLE`, `SYNASTRY_ANGLE_INTERACTIONS_PARTIAL`,
`COMPOSITE_ANGLES_UNAVAILABLE`). The other direction still runs. Nothing is
substituted.

## Refusals

Synastry and composite refuse two charts that differ in zodiac or schema
version, raising `INVALID_CALCULATION_PROFILE`. Cross aspects between a tropical
and a sidereal chart would be arithmetic on incompatible frames.

## Not in v0.2

- Davison relationship charts (architecture-ready, not implemented)
- composite house systems
- compatibility scoring: `03_CALCULATION_SPEC.md` forbids a percentage in the
  deterministic engine without a separately versioned scoring profile

## Contract change

`openapi/gbc-astro-v1.json` now publishes `/v1/charts/synastry` and
`/v1/charts/composite`. The frontend pins the contract by hash in
`.engine-version.json`, so it keeps building against v0.1.0 until it re-syncs
deliberately.

---

# Addendum — deriving what was previously refused

The three refusals above were about missing methodology, not missing capability.
Two of them are now implemented properly rather than declined.

## Composite houses and angles

Previously: angles were the independent midpoint of each of the two charts'
angles, houses were not produced at all.

Now:

```
composite MC = shortest-arc midpoint of the two Midheavens
ARMC         = right ascension of that Midheaven
angles+cusps = swe_houses_armc(ARMC, reference latitude, obliquity, system)
```

`swe_houses_armc` needs no instant, which is exactly why it fits a chart that
has none. The reference latitude is the plain mean of the two birth latitudes,
since latitude does not wrap. Obliquity does need an instant, so the profile
declares one: the midpoint of the two Julian Days, the same instant the Davison
chart uses.

The defect that made the old angles worth warning about is gone rather than
documented. Verified in tests: Descendant is exactly Ascendant + 180, IC is
exactly MC + 180, cusp 1 is exactly the Ascendant, cusp 10 is exactly the
Midheaven, and the twelve cusps advance in order and close the circle.

The correction is not cosmetic. On the committed golden pair the Ascendant moves
from 59.990 to 72.768 degrees, nearly 13 degrees, which is the size of the error
the averaging shortcut carried.

Composite bodies now carry a house number. They still carry no speed, distance
or retrograde state: a composite remains a construct, not an instant.

Schema: composite `1.1.0` (was `1.0.0`).

## Davison charts

A Davison chart is an ordinary natal calculation at the midpoint moment between
the two births and the midpoint of the two places. Nothing is constructed, so
everything is real: genuine speeds, retrograde states, houses, and aspects with
meaningful applying and separating phases.

Two traps, both covered by tests:

- **Geographic longitude wraps.** 179 East and 179 West average to 180, not 0.
  Latitude does not wrap and takes the plain mean.
- **Floating-point order dependence.** `shortest_arc_midpoint` is commutative in
  exact arithmetic but differs in the last bits between argument orders. Here the
  midpoint is not the answer but the *input* to a fresh chart calculation, so
  1e-14 degrees was enough to make `davison(a, b)` and `davison(b, a)` return
  different charts. Found by the order-independence test, fixed by sorting the
  inputs rather than rounding the output.

Both birth times must be known; a Davison chart with an unknown time is refused,
not approximated.

Schema: davison `1.0.0`.

## Cross-aspect phase, opt-in

Default remains `indeterminate`. Setting the profile's
`cross_aspect_phase_policy` to `natal_speed_convention` produces applying and
separating from the two natal speeds under the traditional synastry reading. The
chart then carries `SYNASTRY_PHASE_BY_CONVENTION` at `warning` severity stating
that this is a convention rather than physics, and the policy is echoed in
`meta.crossAspectPhasePolicy` so any stored chart records which reading produced
it.

## Still refused

Compatibility scoring. `03_CALCULATION_SPEC.md` allows it only behind a
separately versioned scoring profile, and the weights in such a profile are an
editorial decision, not a technical one.

## Surfaces

CLI `gbc davison`, HTTP `POST /v1/charts/davison`, and
`AstrologyEngine.davison(...)`.

Suite: 172 passed, 0 skipped.

---

# Addendum 2 — compatibility scoring

`03_CALCULATION_SPEC.md` permits a score only behind a separately versioned
scoring profile. `synastry-scoring-v1` is that profile.

## What the market does

Researched before choosing anything. Findings:

- There is **no standard**. Almost every service keeps its formula private, and
  two of them will disagree about the same couple.
- The *structure* is nonetheless consistent everywhere: weight each contact by
  aspect type, by which two bodies it joins, and by how tight the orb is.
- The one widely cited system that publishes its reasoning is Cafe Astrology's,
  which uses a +4..-4 per-contact scale and raw point totals, **not**
  percentages. Its author states plainly that "none of these weights are
  absolute" and that "total activity rather than final sum is the most telling
  value".
- The standard criticism is that changing one weight flips the result, which is
  a fair description of any such system.

Sources: cafeastrology.com/synastry-2.html,
cafeastrology.com/compatibility-report-scores.html,
en.wikipedia.org/wiki/Astrological_compatibility

## What was built

Structure follows the consensus. The numbers are GetBirthChart's own, declared
in `gbc_astro/profiles/scoring.py` and shipped inside every result.

Three totals, no percentage: `supportive`, `challenging`, and `activity` as the
headline, with `balance` as the net. A percentage would imply an absolute scale
that does not exist.

Every contact appears in `contributions` with its aspect, orb, and the three
factors multiplied to produce it, so the totals are reproducible by hand from
the published breakdown. A test asserts exactly that.

## A real bug the design caught

The first implementation scored all four angles independently and produced
`A.sun square B.ascendant` **and** `A.sun square B.descendant` as separate
lines. The Descendant is always exactly opposite the Ascendant, so those are one
geometric fact counted twice. Worse, a body conjunct the Descendant is opposite
the Ascendant, so the same configuration scored `+3` and `-2` simultaneously.

Angle contacts are now collapsed per axis. The surviving line is the conjunction
when either end has one, since being conjunct the Descendant is its own thing
rather than a weak opposition, and otherwise the axis's declared primary end.

Effect on the worked example: 91 scored contacts fell to 74, and activity fell
from 88.31 to 71.27. The difference was inflation, not signal.

## Honest limits, stated in the output itself

The result carries `notes` saying that the weights are an editorial opinion
rather than a measurement, and that unlike every other calculation in this
engine a score has **no independent reference** it can be validated against.
Tests check the things that can be wrong regardless of opinion: totals match the
published breakdown, no geometric fact is counted twice, the result does not
depend on argument order, and changing the profile changes the score.

House overlays are not scored in v1. Each additional factor adds another set of
editorial weights, and overlays would need their own defensible table rather
than an assumed one.

Schema: score `1.0.0`. Surfaces: `engine.compatibility()`, `gbc compatibility`,
`POST /v1/charts/compatibility`.

Suite: 190 passed, 0 skipped.

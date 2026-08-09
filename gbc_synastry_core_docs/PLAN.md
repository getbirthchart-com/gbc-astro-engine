# Synastry roadmap — implementation plan

Written after auditing the engine against `00`–`04`. The roadmap was drafted
without visibility into what the engine already does, and a large part of V1 and
V2 is already built and validated. This plan is therefore a gap analysis, not a
from-scratch build, and it reorders the phases where the existing code makes the
document's order wrong.

## 1. Already built

Verified by calling the running API, not by reading code.

| Roadmap item | Status | Where |
|---|---|---|
| Cross-chart aspects (V1 §4) | done, no IDs | `POST /v1/charts/synastry` → `crossAspects` |
| Angle contacts (V1 §6) | done, directional | `angleInteractions`, carries `bodyChart`/`angleChart` |
| House overlays (V1 §7) | done, both directions | `aBodiesInBHouses`, `bBodiesInAHouses` |
| Asymmetric unknown time (V1 §8) | done | A known / B unknown → `aInB=0`, `bInA=13`, warnings raised |
| Deterministic scoring (V1.5 §1–3) | partial | `POST /v1/charts/compatibility`, full contribution decomposition |
| Rulers/dispositors primitive (V1.5 §7) | done natally | `derived.chartRuler`, `houseRulers`, `dispositors` (v1.1.0) |
| Composite chart (V2 §1–3, §5–6) | done | `POST /v1/charts/composite` |
| Composite houses/angles (V2 §4) | **done, ahead of spec** | MC-derived, not midpointed cusps |
| Circular midpoint (V2 §2) | done + `ambiguous` flag at 180° | `midpoints[].ambiguous` |
| Secondary progressions (V2.5 §5–6) | done, externally validated | `POST /v1/forecast/progressions` |
| Transit engine (V2.5 §1) | done, ranked | `POST /v1/forecast/transits` |
| Explicit OpenAPI schemas (principle 7) | done | v1.2.0, all 17 routes |
| Provenance on every result (principle 8) | done | every `meta` block |

Two of these are worth calling out because the roadmap flags them as risky:

**Composite houses and angles** (V2 §4 — "high-risk, consider deferring"). Already
implemented and not by the shortcut the document warns against. The composite MC
is the circular midpoint of the two MCs, and the Ascendant and every cusp are
*derived* from it. Averaging each angle independently — the common approach —
produces an Ascendant and Midheaven that do not hold the geometric relationship
a real chart's angles do.

**Secondary progressions** (V2.5 §16 — "high sensitivity… do not mark PASS
without strong external numerical validation"). Already validated against
independent references, with the progressed-instant convention documented. The
largest stated risk in V2.5 is already retired.

## 2. Real gaps

### Blocking everything: deterministic IDs

The roadmap's evidence rule (`00` §"Evidence rule") requires every score, rank and
theme to reference canonical evidence IDs. Cross aspects, overlays and angle
contacts currently carry **no `id` field at all**.

Transits and patterns already do — `transit.uranus.opposition.natal.mercury`,
`pattern.grand_cross.mars.moon.neptune.venus` — so the convention exists and is
proven; synastry simply never adopted it.

Everything downstream is addressing: contributions reference evidence IDs,
evidence bundles collect them, report outlines order them, V2.5 activation marks
them. Retrofitting IDs after those consumers exist means changing all of them.
This is the first slice and nothing else should start before it.

### V1 remainder
- `SYNASTRY_ASPECT_PROFILE_V1` — cross-chart orbs currently reuse the natal
  aspect profile. §4 says explicitly not to reuse natal orbs blindly.
- Top strengths / challenges (§9)
- Dimension signals (§10)

### V1.5 remainder
- Dimensions (§1) — the existing contributions already carry
  `kind/a/b/type/orb/weights/value`, so this is tagging each contribution with a
  dimension, not a rewrite of the scorer.
- Relationship-type profiles (§5): romantic, friendship, family, work
- Coverage / missing-data normalization (§10)
- Directional themes (§8)
- Point contacts (§6) — see the capability note below
- Ruler interactions (§7) — the natal primitive landed in v1.1.0, so this is now
  unblocked

### V2 remainder
- Advanced relationship patterns (§7)
- Evidence-context builder (§11)
- Report outline builder (§12)

### V2.5 remainder
- Relationship transits + synastry activation (§1–3)
- Composite transits (§4)
- Progressed synastry, three labelled categories (§6–7)
- Progressed composite (§8)

## 3. A capability limit to decide before V1.5 §6

The roadmap asks for contacts to North Node, South Node, Chiron, **Vertex**,
**Part of Fortune** and **Lilith**.

What the engine actually has: `true_node`, `mean_node`, `chiron` as core bodies;
`mean_lilith` and `true_lilith` as optional asteroid-family bodies. **Vertex and
Part of Fortune do not exist**, and South Node is not a body — it is the node
opposed, which is a derivation the engine does not currently publish.

Vertex and Part of Fortune are both cheap and both time-sensitive (the Vertex is
a horizon intersection; the Part of Fortune is an arc from the Ascendant), so
they must be absent for unknown-time charts. They belong in the natal layer
before synastry can contact them. Either add them there first, or cut them from
scope explicitly — §6 says "do not expose experimental points merely because they
exist internally", and the inverse applies: do not promise contacts to points
that do not exist.

## 4. Sequencing — and where it differs from the roadmap

The document orders V1 → V1.5 → V2 → V2.5. Given what is already built, that
order puts two things in the wrong place.

**Strengths/challenges (V1 §9) should come after dimensions, not before.**
Ranking "top 5 strengths" is a question about which contacts matter most, and
dimension scores are exactly the machinery that answers it. Built first, the
ranking needs its own ad-hoc relevance weights; built second, it reads off
scores that already exist. The roadmap itself hints at this — V1.5 §9 is a
"ranking upgrade" replacing the V1 ranking barely a phase after writing it.

**Ruler interactions (V1.5 §7) are now unblocked and cheap.** They were
speculative when the roadmap was written; the natal rulership layer shipped in
v1.1.0.

Proposed order:

| Slice | Contents | Depends on |
|---|---|---|
| **S1** | Deterministic IDs on every synastry fact + `SYNASTRY_ASPECT_PROFILE_V1` | — |
| **S2** | Dimensions + dimension profile, tagging existing contributions | S1 |
| **S3** | Relationship-type profiles + coverage normalization | S2 |
| **S4** | Strengths/challenges ranking, reading off S2 scores | S2 |
| **S5** | Directional themes + ruler interactions | S1, v1.1 rulership |
| **S6** | Vertex + Part of Fortune in natal, then point contacts | natal work first |
| **S7** | Advanced relationship patterns | S1 |
| **S8** | Evidence-context builder + report outline | S1–S7 |
| **S9** | Relationship transits + synastry activation | S1, transit engine |
| **S10** | Composite transits | composite, transit engine |
| **S11** | Progressed synastry (three labelled categories) | progressions |
| **S12** | Progressed composite | S11 |

S1–S4 delivers what the product actually needs first: a scored, explainable,
evidence-backed synastry result. S9–S12 is the timing layer and can wait.

## 5. Where I would push back

**The overall 0–100 score (V1.5 §4) should be deferred, and the roadmap already
allows it.**

§4 lists a condition that is genuinely hard: the score must not reward charts
merely for having more available data. This is not a presentation problem, it is
a bias problem. A both-times-known pair produces house overlays, angle contacts
and ruler interactions that an unknown-time pair cannot produce at all, so any
sum-based total scores the second pair lower for a reason that has nothing to do
with the relationship. Coverage normalization is the named remedy and it is easy
to get wrong: dividing by the number of available signals rewards sparse charts
with one strong contact.

Dimension scores with an explicit `coverage` field per dimension are honest and
useful now. A single headline number is the part to hold back until the
normalization has been tested against fixtures built for exactly this — the
roadmap's own calibration fixtures (V2 §10) include "sparse unknown-time
geometry", which is the right test and belongs before the number, not after.

**Package structure.** The roadmap suggests a new `synastry/` package. The repo
already has `relationship/` holding synastry, composite, davison and scoring.
Adding a parallel package would split one domain across two, and the roadmap's
own note says "adapt to repository conventions". Extend `relationship/`.

**"Do not create an arbitrary overall percentage in V1" (V1 §"Absolute rules")**
is already satisfied and should stay that way: the existing compatibility
endpoint returns `supportive`, `challenging`, `activity` and `balance` with
bands, not a percentage.

## 6. First slice in detail — S1

Everything downstream references these IDs, so the format is worth fixing once.

Follow the convention already in use for transits and patterns: lowercase,
dot-separated, no display prose, derived entirely from the fact so the same fact
in the same pair always produces the same ID.

```
synastry.cross.a.sun.trine.b.moon
synastry.angle.a.venus.conjunction.b.ascendant
synastry.overlay.a.sun.in.b.house_7
synastry.ruler.a.house_7_ruler.conjunction.b.venus
```

Two decisions to make explicitly rather than let the implementation settle by
accident:

1. **A/B identity is part of the ID.** `a.sun.trine.b.moon` and
   `a.moon.trine.b.sun` are different facts about different people and must not
   collapse. The existing deduplication preserves this; the ID has to as well.
2. **The ID must not encode the orb or the profile.** Orbs change with the
   profile version, and an ID that changes when a threshold changes cannot be
   referenced by a stored result. Profile version belongs in provenance, which
   already exists.

Add `SYNASTRY_ASPECT_PROFILE_V1` in the same slice, since changing which
contacts exist after IDs are in use would invalidate stored references.

Deliverable: every cross aspect, angle contact and overlay carries a stable
`id`; a test asserts IDs are unique within a result, stable across runs, and
unchanged when the orb profile version changes but the geometry does not.


---

# Status — all slices complete

| Slice | Contents | Shipped |
|---|---|---|
| S1 | Deterministic IDs, `SYNASTRY_ASPECT_PROFILE_V1` | v1.3.0 |
| S2 | Dimensions, evidence rule | v1.4.0 |
| S3 | Relationship-type profiles | v1.5.0 |
| S4 | Strengths and challenges | v1.6.0 |
| S5 | Directional themes, ruler interactions | v1.7.0 |
| S6a | Vertex, Part of Fortune, south node (natal) | v1.8.0 |
| S6b | Cross-chart point contacts | v1.9.0 |
| S7 | Relationship patterns | v1.10.0 |
| S8 | Evidence contexts, report outline | v1.11.0 |
| S9–S12 | The timing layer | v1.12.0 |

V1, V1.5, V2 and V2.5 of the roadmap are complete.

## The one thing deliberately not built

The overall 0–100 compatibility score. The roadmap permits deferring it at V1.5
section 4, and the reason has not changed since S2: summing dimensions rewards
the pair that happens to have more available data, and dividing by availability
rewards the sparse pair with one strong contact. Dimension scores with explicit
per-dimension coverage are honest and useful now; a single headline number is
not, until it is tested against the calibration fixtures V2 section 10 asks for
— including sparse unknown-time geometry, which is exactly the case that breaks
both naive approaches.

## Bugs found along the way

Nine, none of them in the slice that was being built at the time. Every one was
a feature meeting another feature that nobody had run together:

1. **Both lunar nodes aspecting** (S1). The true and mean node are one point
   computed two ways, so every node contact was doubled and every chart ever
   cast carried a "node conjunct node" that was always true and said nothing.
2. **The scorer dividing by the wrong orb limit** (S2). My own, from S1: after
   splitting the synastry orb profile from the natal one, the scorer kept using
   the natal limits, so a near-miss scored as though it were close.
3. **Relocation carrying the source chart's derived block** (S6a). A chart
   relocated to London reported a Scorpio Ascendant beside a Pisces rising sign
   and house rulers for cusps it no longer had.
4. **The day/night test inverted** (S6a). Caught in a smoke test; it would have
   put the Lot of Fortune at the reflection of the right place on exactly the
   charts where the two conventions disagree.
5. **`_to_sidereal_geometry` dropping the vertex** (S6a), so sidereal charts had
   none at all.
6. **Cross yods citing nothing, permanently** (S7), because a yod is defined by
   quincunxes and the synastry profile does not treat a quincunx as a contact.
7. **Report sections citing every contribution** (S8). A communication section
   citing all fifty scored contacts is citing the whole chart and calling it
   communication — worse than citing nothing, because it looks specific.
8. **Activation ids not unique** (S9). One transit activating three contacts
   produced three rows with the same id.
9. **Thresholds producing 29.4 patterns per pair** (S7), which is not a list of
   notable patterns.

The recurring shape is worth naming, because it appeared four times in different
clothes: **the same geometry reported twice under two names.** Both nodes, ruler
interactions, reflected points, and pattern scoring each would have counted one
fact as two. The fix is always the same — cite the existing fact rather than
minting a new one — and it is now the default assumption for anything that
reframes geometry rather than producing it.

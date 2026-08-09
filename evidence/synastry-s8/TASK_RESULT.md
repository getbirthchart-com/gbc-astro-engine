# Synastry S8 — evidence contexts and report outline

The two things the roadmap asks the core to provide for "ask about us" (V2 §11)
and the couple report (V2 §12). Neither produces prose and neither calls a
model. Both select and order facts that already exist.

Two new routes: `POST /v1/charts/evidence` and `POST /v1/charts/report-outline`.
Nineteen paths to twenty-one.

## Bounded is part of the contract, not the caller's problem

An unbounded evidence context is how a prompt ends up carrying four hundred
contacts, most irrelevant to the question asked, and how a downstream model ends
up asserting whichever of them it happened to notice.

So the cap lives in the profile, and every context reports `availableCount`
beside what it returned plus a `truncated` flag. The top of a list must not be
mistakable for the whole of one.

```
topic           returned  available  truncated
overall            12        50        yes
communication       8         8        no
attraction         12        24        yes
patterns           12        17        yes
direction          12       112        yes
```

Selection is by magnitude with ties broken on the evidence id, so the same pair
and topic always give the same context.

## A defect caught before it shipped

The first outline gave every dimension section all fifty scored contributions. A
communication section citing every contact in the chart is citing the whole
chart and calling it communication — worse than citing nothing, because it looks
specific.

Fixed by filtering contributions on the section's own topic. Communication went
from 50 to 8, which matches that dimension's contact count exactly.

The same cap now applies per section: one section was carrying 133 evidence ids.

## An empty section is still a section

A pair with no birth times has no house overlays. Dropping the section would
read as a topic that did not apply to them; returning it as unavailable with a
specific reason reads as what it is — a question the geometry could not answer.
The same distinction the dimension scores draw between silent and neutral.

```
BOTH BIRTH TIMES UNKNOWN
  N/A  directional_dynamics   no directional contact was found; a chart without
                              houses has no house rulers to send
  N/A  house_overlays         one chart has no houses, so this overlay direction
                              is unavailable
```

Reasons are deduplicated within a section: both overlay directions share one, and
saying it twice reads as two separate problems.

## What the core does not do

No prose, no model, no rendering. Section identifiers, evidence identifiers,
score identifiers and priorities. The words belong to whatever renders them,
which is the division the roadmap asks for and the one that keeps the astrology
facts in the engine.

## Verification

```
ruff   clean
mypy   clean, 109 source files
pytest 618 passed, 1990 subtests, 0 skipped   (602 -> 618)
```

Every identifier a context or an outline emits is asserted to resolve against
the synastry result. Versions: engine 1.10.0 -> 1.11.0. Additive.

## Roadmap position

V1, V1.5 and V2 are now materially complete, except the overall 0-100 score,
which stays deferred for the reason recorded in S2.

Remaining: S9-S12, the timing layer -- relationship transits, composite
transits, progressed synastry, progressed composite.

# S6b — cross-chart point contacts

The roadmap asks at V1.5 section 6 for contacts to the derived points, each with
an explicit orb policy, an unknown-time policy, and either a scoring
contribution or an explicit no-scoring status. All three are stated below.

## Only two of the four points take part

The chart publishes four derived points and two of them carry no geometry of
their own:

```
south_node - true_node = 180.000000
antivertex - vertex    = 180.000000
```

Because they are exact reflections, every contact they could form is one the
other end already forms with the aspect reflected. Measured on a real pair:

```
              sep to A.south_node   sep to A.true_node    sum
B.sun               117.53                62.47          180.00
B.venus              76.71               103.29          180.00
B.mars              177.83                 2.17          180.00
```

Admitting both ends would report one piece of geometry twice under two names —
the same double-count the lunar node fix removed in S1 and the ruler
interactions avoided in S5. This is the third time this shape has appeared, and
it is the same collapse the scoring already applies to the Ascendant/Descendant
and Midheaven/IC axes.

So the vertex and the Lot of Fortune form contacts; the antivertex and the south
node do not.

## Orb, and a section that is often empty

A computed point is not a body. It has no disc and no traditional orb of
influence, and a contact to it is a weaker claim than a planet-to-planet aspect
at the same separation. Measured over thirty pairs, both directions, twelve
bodies:

```
conjunction + opposition, orb 2.0    mean 1.2 contacts    12 of 30 pairs have none
all five aspects,         orb 2.0    mean 4.1 contacts     1 of 30 pairs has none
```

Widening to all five aspects would fill the section for almost everyone. **It was
not done.** A trine to a calculated point at two degrees is a weak claim, and
padding a section so it is never empty is how a product ends up asserting things
it does not mean.

Forty percent of pairs having no notable point contact is the honest answer, and
the empty list says so. Tested directly with a pair that has none.

## Not scored, explicitly

Reported and not fed into the compatibility score — the same status house
overlays have carried since v0.2. Scoring them would need weights for the vertex
and the Lot relative to the planets, which is another table of editorial numbers
with nothing to validate it against.

`scored: false` travels on every contact rather than being left to inference,
and a test asserts no contribution in the score cites a `.point.` id. The
contribution count is unchanged at 50.

## Unknown time

The vertex and the Lot both need an Ascendant, so a chart without a birth time
sends no points. The other direction is unaffected: 0 contacts from the sparse
chart, 2 from the known one. Nothing is substituted.

## Verification

```
ruff   clean
mypy   clean, 105 source files
pytest 592 passed, 1777 subtests, 0 skipped   (584 -> 592)
```

Versions: engine 1.8.0 -> 1.9.0, synastry schema 1.2.0 -> 1.3.0. Additive.

## Roadmap position

V1 and V1.5 are now materially complete apart from the overall 0-100 score,
which stays deferred for the reason recorded in S2: summing dimensions rewards
the pair with more available data, and dividing by availability rewards the
sparse pair with one strong contact.

Remaining: S7 advanced patterns, S8 evidence context and report outline, then
S9-S12 the timing layer.

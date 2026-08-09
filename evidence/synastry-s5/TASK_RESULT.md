# Synastry S5 — ruler interactions and directional themes

Both are **views** over facts the result already contains. Neither produces
geometry, neither mints an evidence id, and neither is scored.

## The bug this design avoids

"A's seventh-house ruler conjunct B's Venus" is not a new contact. If Mercury
rules A's seventh house, it is the cross aspect
`synastry.cross.a.mercury.conjunction.b.venus` — already in the result, already
scored.

Emitting it again as a ruler interaction with its own evidence id would put the
same geometry into the scoring twice. That is the same double-count the lunar
node fix removed in S1, arriving in a new place, and it is the kind of thing
that would have been invisible: the score would simply have been higher for
anyone whose rulers happen to be busy.

So every ruler interaction carries `evidenceId` pointing at the fact it
reframes, and the scoring layer never sees these at all. Verified: 86 ruler
interactions on the reference pair, every citation resolves, and the
contribution count is unchanged at 50.

A body ruling two houses reframes one contact twice, deliberately — and the
fact behind it is still scored once. Tested.

## What is directional, and what is not

House overlays and angle contacts are directional. A's Sun in B's seventh house
is a statement about A acting on B's territory, and the reverse is a different
statement about different territory.

A cross aspect is **not**. `a.sun.trine.b.moon` and `b.moon.trine.a.sun` are one
geometric relation described twice; the A and B say whose planet is whose, not
which way influence runs. Grouping cross aspects into directional themes would
assert a direction the geometry does not have — the same claim the engine
already refuses when it reports cross-aspect phase as `indeterminate` rather
than borrowing natal speeds.

Directional themes are built from overlays and angle contacts only. Asserted
directly: no `.cross.` id appears in any theme.

## Asymmetry under unknown time

A chart with no birth time has no houses, so it has no house rulers to send.
The other direction is unaffected: 0 interactions `B_TO_A`, and a full set
`A_TO_B`. That asymmetry is the correct answer, not a degraded one, and nothing
is substituted for the rulerships the sparse chart does not have.

## Coverage

Every dimension is emitted for both directions even when empty, for the same
reason dimension scores are: an absent theme and a neutral one are different
statements.

```
A_TO_B  emotional      n=11        B_TO_A  ...
A_TO_B  communication  n=3
A_TO_B  attraction     n=7
A_TO_B  stability      n=5
A_TO_B  growth         n=8
A_TO_B  conflict       n=3
```

Swapping the two charts swaps the directions exactly — tested by comparing
`A_TO_B` of one against `B_TO_A` of the other.

## Verification

```
ruff   clean
mypy   clean, 102 source files
pytest 564 passed, 1689 subtests, 0 skipped   (552 -> 564)
```

Versions: engine 1.6.0 -> 1.7.0, synastry schema 1.1.0 -> 1.2.0. Additive: two
new arrays on the synastry result, nothing existing changed.

## Next

S6 needs a decision rather than code: the roadmap asks for contacts to Vertex
and Part of Fortune, and the engine has neither. Either they are added to the
natal layer first or they leave scope explicitly.

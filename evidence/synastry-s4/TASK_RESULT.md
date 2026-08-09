# Synastry S4 — top strengths and challenges

Up to five of each, every one citing a canonical evidence id, ranked for
strength and penalised for repeating a theme an earlier pick already covered.

## The reordering paid off

The roadmap puts strengths and challenges in V1, before dimensions. This plan
inverted that, and S4 is where the inversion pays: the rank basis is the sum of
a contact's dimension values, which already carry the dimension mapping and the
relationship-type weight. So the ranking needs no relevance weights of its own,
and a working relationship's top contacts differ from a romantic one's without
the ranking profile knowing that relationship types exist.

Built in the roadmap's order, this would have needed an ad-hoc weight table
that V1.5 section 9 would then have replaced one phase later.

## My justification for the diversity penalty was wrong

The roadmap asks for a ranking that avoids returning five near-duplicate
contacts. I assumed that meant a naive top five covers few dimensions, wrote
that into the profile, and then measured it over thirty random pairs:

```
penalty        distinct dimensions in top 5   commonest dimension's share
1.00 (off)             5.10 of 6                        31%
0.55                   5.97 of 6                        25%
```

A plain sort already reaches five of six dimensions, because one contact touches
several — a Sun-Moon contact is emotional, growth and stability at once — so
five contacts sprawl across nearly everything whatever the order. The gain I
claimed was almost entirely already there.

The duplication a reader actually notices is the same planet over and over, and
that is where the penalty earns its place:

```
penalty        distinct bodies in top 5   commonest body's share of 5 picks
1.00 (off)           6.57                            2.57
0.55                 7.53                            2.10
```

Penalising a repeated dimension demotes a repeated planet as a consequence,
since contacts that repeat a planet repeat its dimensions. The design is
unchanged; the stated reason for it is now the measured one.

Below 0.55 the numbers stop moving — 0.30 and 0.10 measure the same — so a
harsher penalty buys nothing and only makes the order harder to explain.

## Explainable ordering

Two numbers travel with every ranked contact: `value`, its raw contribution,
and `selectionScore`, the diversity-adjusted basis it was actually ranked on.
A strong contact placed low was demoted for repeating a dimension, and the pair
of numbers shows exactly that.

Asserted: `selectionScore` falls monotonically down each list (greedy selection
cannot pick a higher-scoring candidate later), and at least one lower-ranked
contact is stronger by raw value than one above it — because if that never
happened the penalty would be doing nothing.

```
TOP CHALLENGES (romantic)
1. a.mars.square.b.jupiter        val=-1.52  sel=3.25   attraction,conflict,emotional,growth
2. a.saturn.square.b.pluto        val=-1.13  sel=0.70   attraction,conflict,stability
3. b.mars.square.a.ascendant      val=-1.30  sel=0.16   attraction,conflict,emotional
```

Rank 3 is stronger than rank 2 in raw terms and sits below it, because by then
attraction, conflict and emotional had all been taken twice.

## Nothing is excluded

The penalty reorders; it never removes a contact from consideration. A pair
whose whole story is one dimension still receives a full list, and a sparse
unknown-time pair still receives both lists.

Round robin — one pick per dimension — was rejected: it promotes a weak contact
over a much stronger one purely for being unrepresented, and caps the list at
the number of dimensions.

## Challenging is not bad

The lists split on the sign of the contribution and the hard one is named for
what it is. Nothing scores a pair worse for having friction, and a relationship
with no hard contacts at all is usually one with nothing much happening.

## Verification

```
ruff   clean
mypy   clean, 101 source files
pytest 552 passed, 1280 subtests, 0 skipped   (541 -> 552)
```

Versions: engine 1.5.0 -> 1.6.0, score schema 1.2.0 -> 1.3.0. Additive.

## Next

S5: directional themes and ruler interactions. Both are unblocked — direction is
already carried on every overlay and angle contact, and the natal rulership
layer landed in 1.1.0.

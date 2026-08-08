# v1.1 — rulership, dignity, dispositors and dominance

Chart ruler, house rulers, essential dignity, dispositor chains, mutual
receptions and a dominant-planet ordering. All of it arrives in the `derived`
block of an ordinary natal chart, so a client needs no extra round trip and no
extra endpoint.

## Why it is here and not in the client

None of this touches an ephemeris. It is a table lookup plus a graph walk over
signs the chart already reports, and a frontend could compute all of it. That is
not the argument.

The tables encode decisions that are genuinely contested, and a decision that is
not published is a decision two clients can disagree about without either
knowing:

- Traditional or modern rulership changes the chart ruler, every dispositor
  chain, and which planets are in detriment.
- A sidereal chart cast in the Vedic tradition does **not** give Scorpio to
  Pluto. Answering it from the modern table names the wrong ruler for three
  signs in twelve, and corrupts every chain that passes through one of them.
- The frontend has no way to know which calculation profile produced a chart, so
  it has no standing to choose.

So the table is a property of the calculation profile, resolved per chart, and
published in `meta.rulershipProfile` alongside everything else that shaped the
answer. Same discipline as the ayanamsa, the aspect profile and the transit
ranking.

## The two tables

`traditional-septenary-v1` — the classical seven. The luminaries rule one sign
each, the other five rule two apiece. `modern-western-v1` — the same with
Scorpio, Aquarius and Pisces reassigned to Pluto, Uranus and Neptune, keeping
Mars, Saturn and Jupiter as co-rulers.

Bound to profiles: `western-modern-v1` uses modern, `vedic-sidereal-v1` uses
traditional. Verified on one chart:

```
MODERN    asc=pisces    ruler=neptune  final=(pluto,)   pluto=domicile
SIDEREAL  asc=aquarius  ruler=saturn   final=(saturn,)  pluto=unrated
```

Detriment and fall are **derived** from the domicile and exaltation tables
rather than listed separately, so a typo cannot put a planet in detriment
somewhere that does not face the sign it rules. Asserted for both tables.

## Distinctions the implementation refuses to blur

**`unrated` is not `peregrine`.** Peregrine means "in none of its dignities" and
presupposes the body has dignities. Pluto under a septenary scheme has no
rulership at all. Collapsing the two would claim a judgement the scheme does not
make, so an outer planet in a traditional chart reports `unrated` and starts no
dispositor chain.

**A loop is not a failure to find a final dispositor.** Follow a planet to the
ruler of its sign and repeat, and the walk ends in one of two ways: a planet in
its own sign, which is a final dispositor, or a closed loop of planets ruling
each other's signs, which has none. A chart can be nothing but loops and
legitimately have no final dispositor. A walk that assumes a self-ruler exists
never returns on that input, so the loop is detected explicitly and reported as
what it is. A two-planet loop is also named as a mutual reception, since it is
read as a relationship rather than as a gap in the chain.

**No rising sign is invented.** A chart with an unknown birth time has no
Ascendant, so it has no chart ruler and no house rulers. Dignity needs only a
sign and survives.

## Dominance

A product relevance ordering, in the same sense as the transit ranking: every
weight is published, every component of every score is returned beside the
total, and no model of any kind is involved. It is not a claim about
astrological truth — two schools weighting differently would both be entitled to
their answer, which is exactly why the weights travel with the score.

Angularity carries the largest multiplier because it is the one factor every
school that scores this at all agrees raises a planet's prominence. Dignity
contributes but cannot by itself make a cadent, unaspected planet dominant.
Ties break by body name, so two runs of the same chart always agree.

## Deliberately absent

The minor Ptolemaic dignities — triplicity, terms and faces — are not included.
There are at least three competing term tables, and adding them under one
arbitrary choice would be worse than not offering them. The output declares
`minorDignitiesIncluded: false` rather than leaving a caller to assume
completeness.

Vedic-specific refinements — varga dignity, combustion rules, the disputed
rulership claims for Rahu and Ketu — are not modelled. The profile id names a
septenary scheme, not a school.

## Structural note

The result dataclasses live in `models/rulership.py`, not beside the
computation. `models` is imported by `derived`, so defining them in `derived`
closes an import cycle through `moon_phase`. Same placement `MoonPhase` already
uses.

## Verification

```
ruff   clean
mypy   clean, 96 source files
pytest 490 passed, 743 subtests, 0 skipped   (466 -> 490)
```

24 new tests. The two that matter most are structural rather than numerical:
that the table follows the calculation profile rather than a hardcoded default,
and that a dispositor walk terminates on a chart made entirely of loops.

Versions: engine 1.0.0 → 1.1.0, natal schema 1.0.0 → 1.1.0. Both additive; no
existing field changed meaning or shape.

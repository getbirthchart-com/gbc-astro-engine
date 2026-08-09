# Synastry S7 — relationship patterns

Five families of named configuration: cross configurations, body emphasis, pair
clusters, mutual activation, angular activation.

## Why patterns exist alongside dimension scores

A pattern is discrete — present or absent — where a dimension score is a
magnitude. "This pair has a Saturn emphasis" and "stability scores 7.51" are
different statements, and a report needs both.

To stop them being the same thing twice, patterns are defined on **counts of
contacts and which bodies take part**, never on the dimension scores. A second
view of the same geometry, not a relabelling of the same number.

## The natal detector was reused rather than reimplemented

A grand trine is a grand trine whether its legs belong to one person or two. So
both charts' bodies are merged into one dictionary with each id prefixed by its
owner, and the validated natal detector runs over that. Results are then
filtered to figures that actually span both people — one lying entirely inside a
chart is that person's natal pattern, already reported there, and repeating it
as a relationship fact would say something about the pair that is only true of
one of them.

## First attempt produced 29.4 patterns per pair

A list of thirty notable patterns is not a list of notable patterns. Three
separate causes, all measured before being fixed:

**Cross configurations were far too loose.** Merging two charts doubles the
bodies and roughly octuples the triples to test, so the natal leg orbs produce
far more figures than they do natally:

```
leg orbs        cross configurations per pair
6/6/3 (natal)          13.8   (3-27)
4/4/2                   8.7   (3-18)
3/3/1.5                 5.8   (2-10)   <- chosen
2/2/1                   4.3   (2-8)
```

**Body emphasis fired on almost every body.** A body averages 6.3 cross-chart
contacts, so a threshold of four named 7.8 of the ten eligible bodies:

```
threshold    emphasised bodies per pair
>= 4              7.8   (3-10)
>= 6              4.6   (2-8)
>= 8              1.7   (0-8)   <- chosen
>= 10             0.4   (0-3)
```

Eight leaves some pairs with none, which is what "emphasis" should mean.

**Cross stelliums counted three bodies in a sign**, as natally — unremarkable
when twenty-four bodies are in play. Raised to four.

Result: 29.4 → 12.7 per pair.

## Two evidence problems, and what each turned out to mean

**Cross configurations cited nothing at first.** They are built from the merged
body set, not from the synastry contacts. Fixed by mapping each A-to-B leg back
to its cross aspect. Legs *inside* one chart are that person's natal aspects and
belong to their chart, which is why a configuration's evidence list is shorter
than its leg count.

**Cross yods could never cite anything.** A yod is defined by two quincunxes,
and the synastry aspect profile deliberately does not treat a quincunx as a
cross-chart contact. So a cross yod is a figure whose defining legs the engine
does not consider contacts between these two people. Excluded, rather than
published with a permanently empty evidence list.

**Cross stelliums sometimes cite nothing, and that is correct.** A stellium is
defined by sign sharing, not by an aspect: four bodies can span twenty degrees
of one sign with no conjunction between the charts inside the orb. Its evidence
is the sign membership, which travels in `members` and `detail.sign`. A test
pins that only a cross stellium may carry an empty evidence list.

## Not scored

Every contact behind a pattern is already scored once as itself. Scoring the
pattern too would count the same geometry a second time for having been noticed
— the shape removed three times already in this project. `scored: false` travels
on every pattern and the contribution count is unchanged at 50.

## Verification

```
ruff   clean
mypy   clean, 107 source files
pytest 602 passed, 1926 subtests, 0 skipped   (592 -> 602)
```

Versions: engine 1.9.0 -> 1.10.0, synastry schema 1.3.0 -> 1.4.0. Additive.

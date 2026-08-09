# Synastry S2 — dimensions, and the evidence rule made real

Six dimensions -- emotional, communication, attraction, stability, growth,
conflict -- each with its two signals kept apart, its coverage, and the
canonical evidence ids it rests on.

## A defect I introduced in S1

Splitting the synastry orb profile off from the natal one in S1 left the scorer
still dividing by the natal limits. Orb tightness is a fraction of the orb a
contact was *allowed*, so the denominator has to be the profile that produced
the contact:

```
sextile at 2.86 deg   scored 0.599   should have been 0.332
```

That sextile sits at 95% of the synastry limit and was being read as 57% of the
natal one. Every cross-aspect and angle contribution was too generous. Fixed,
and the comment now ties the denominator to the producing profile so the same
slip cannot be made silently again.

The class is familiar: a split that left a consumer pointing at the old thing.

## The evidence rule

The roadmap requires that no derived score exist without decomposable
contributing signals citing canonical evidence. Contributions previously
identified their subjects with free-form strings (`"A.moon"`, `"B.sun"`), which
describe a contact but cannot be looked up.

Every contribution now carries `evidenceId` -- the S1 fact id -- and every
dimension lists the ids behind its signals. Three tests hold this up:

- every contribution cites a fact the synastry result actually contains
- every dimension evidence id likewise
- no id is cited twice within one dimension

A citation that does not resolve is worse than no citation, so these assert
resolution rather than mere presence.

## What decides a dimension

The bodies, never the aspect. A Mercury square is still about communication;
what the aspect decides is whether the contribution helps or strains. The one
exception is deliberate and stated: hard aspects add friction to `conflict`,
because friction is a property of the angle rather than of the bodies.

A contact may land in several dimensions. Venus with Mercury is attraction and
communication both, and forcing a single home would discard half of what it
says. Weights are averaged across the two ends rather than summed, so a contact
between two bodies mapped to the same dimension does not outweigh itself.

### A decision the code was making and the profile was not stating

The lunar node and Chiron are mapped to no dimension. A test asserted that
contacts involving them therefore score nothing at all -- and failed, because
the averaging gives them the partner's dimensions at half weight.

The code was right and the test encoded a decision never actually made. Unmapped
does not mean silencing: Mars trine the node is still about drive, just less
squarely than Mars trine Venus, and from the emotional dimension's point of view
an unmapped body and a body mapped elsewhere are the same thing -- not
emotional. What an unmapped body must never do is *introduce* a dimension of its
own, and that is now what the test asserts and what the profile says.

## Coverage, not patched absence

`contactCount` accompanies every dimension. A dimension with no contacts is not
a zero: zero means the geometry is neutral, absent means it is silent, and a
pair with an unknown birth time is silent about everything the angles would have
said.

Verified: an unknown-time pair keeps all six dimensions with lower coverage, no
angle contact is invented for the chart that has no angles, and no zero-valued
contribution is injected to stand in for what is missing.

```
emotional      sup= 9.21  chal= -3.50  n=34
communication  sup= 4.03  chal= -0.54  n= 8
attraction     sup= 7.31  chal= -3.96  n=22
stability      sup= 5.33  chal= -2.17  n=23
growth         sup= 6.84  chal= -5.09  n=26
conflict       sup= 2.26  chal=-10.32  n=29
```

The spread in coverage -- 8 contacts for communication against 34 for emotional
-- is why the dimensions are not comparable as raw magnitudes, and why no
overall figure is derived from them here.

## Still deferred: the overall score

Summing dimensions rewards the pair that happens to have more available data;
dividing by what is available rewards the sparse pair with one strong contact.
Neither is defensible, so neither ships. This matches the roadmap's own escape
hatch at V1.5 section 4, and the calibration fixtures it asks for at V2 section
10 -- including sparse unknown-time geometry -- are the right gate for it.

## Verification

```
ruff   clean
mypy   clean, 99 source files
pytest 533 passed, 1214 subtests, 0 skipped   (516 -> 533)
```

Versions: engine 1.3.0 -> 1.4.0, score schema 1.0.0 -> 1.1.0. Additive: no
existing field changed shape, though every contribution's `orbFactor` and
`value` moved because of the orb fix above.

## Next

S3: relationship-type profiles (romantic, friendship, family, work). Same
geometry, different weighting, and the result must declare which profile
produced it.

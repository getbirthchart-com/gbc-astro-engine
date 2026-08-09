# Synastry S9–S12 — the relationship timing layer

Four capabilities, four routes: relationship transits with synastry activation,
composite transits, progressed synastry, progressed composite. Twenty-one paths
to twenty-five.

## The failure this layer is exposed to is conflation

A transit to A's chart, a transit to B's, a transit to the composite, and a
progressed contact are four different claims about time. Pooling any of them
produces a result nobody can read, and the pooling is easy because the geometry
looks alike. Nothing here is merged:

- the two natal transit charts are returned whole and separate, because which
  person a transit lands on is the only thing that makes it a *relationship*
  transit rather than an ordinary one
- composite transits are a statement about the relationship rather than about
  either person, and are kept in their own result
- progressed contacts carry a mandatory `direction` and are grouped by it

## Activation joins two facts, it does not mint a third

"Transiting Jupiter is conjunct A's Venus" and "A's Venus trines B's Moon" are
two existing facts sharing a body. The activation cites both and adds nothing of
its own — the same discipline as ruler interactions in S5 and point contacts in
S6b. Minting a third id would put the same geometry into the result twice.

Verified on the reference pair: 58 activations, every transit citation resolving
against the transit result and every synastry citation against the synastry
result.

### A defect caught in the smoke test

The first activation id named only the transit, so one transit activating three
different synastry contacts produced three rows with **the same id**:

```
relationship.activation.a.uranus.by.saturn.square   x3
```

Both halves of the join belong in the identifier. Fixed, and a test now asserts
that a transit activating several contacts yields several distinct ids —
including that this case actually occurs, since otherwise the test would pass
vacuously.

## Progressed comparisons: three, never pooled

```
natal_a_to_progressed_b         34 contacts
progressed_a_to_natal_b         27
progressed_a_to_progressed_b    27
```

Asserted that all three sets genuinely differ. If two matched, one would be
computed from the wrong chart — the kind of thing that produces plausible
numbers and no error.

An unknown birth time is refused, inherited from the progression layer: one
day of error in the progressed instant is a year of symbolic time.

## Progressed composite: progress, then compose

The roadmap names two methodologies and warns against mixing them silently. The
profile declares `progress_then_compose`, and the reason is that the alternative
is not available: **a composite chart has no birth instant of its own to
progress from**, so progressing it directly would mean inventing one.

Progressing each natal chart first uses two steps that are each already
validated — the progression numerics against external references, and the
composite midpoint geometry against its own fixtures.

## Zodiac

Composite transits reach the provider directly, and providers always answer
tropically. The rotation is applied, per the lesson from the seven frame bugs
the earlier audit found. Verified: a sidereal engine produces a different
contact set from a tropical one on the same pair.

## Verification

```
ruff   clean
mypy   clean, 111 source files
pytest 640 passed, 2215 subtests, 0 skipped   (618 -> 640)
```

`target_instant` is mandatory on every timing route — the engine never assumes
the current moment. Versions: engine 1.11.0 -> 1.12.0. Additive.

## Roadmap position

**V1, V1.5, V2 and V2.5 are complete**, with one deliberate exception: the
overall 0–100 compatibility score, deferred since S2 because summing dimensions
rewards the pair with more available data and dividing by availability rewards
the sparse pair with one strong contact. The roadmap's own escape hatch at V1.5
section 4 permits this, and its calibration fixtures at V2 section 10 —
including sparse unknown-time geometry — are the right gate for lifting it.

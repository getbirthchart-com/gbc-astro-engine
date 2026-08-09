# Synastry S3 — relationship-type profiles

Four named types plus a neutral one: `romantic-v1`, `friendship-v1`,
`family-v1`, `work-v1`, `general-v1`.

## The absolute rule, and how it is enforced

The roadmap's rule for V1.5 is that relationship type changes relevance and
weighting, **not astronomy facts**. That is asserted directly rather than
assumed: under every type the contributions are the same list, in the same
order, citing the same evidence ids, with the same orbs, and the same `activity`
total. Only the dimension split moves.

```
type          emotional  communic.  attraction  stability     growth   conflict
general-v1        12.71       4.58       11.27       7.51      11.94      12.58
romantic-v1       17.80       4.58       18.03       8.26      10.74      15.10
friendship-v1     15.25       6.86        4.51       7.51      16.71      10.06
family-v1         19.07       4.58        2.25      10.51      11.94      16.35
work-v1            8.90       7.32        1.69      11.26      13.13      15.10
```

Tested in the documented direction, not merely "different": romantic raises
attraction, work raises communication and stability, family raises emotional,
friendship raises growth, and attraction is demoted furthest in the two least
romantic readings.

## Where the weight is applied, and why it matters

Inside each contribution, as it is split across dimensions — not afterwards on
the dimension totals.

Applied afterwards it would scale the totals away from the contributions cited
under them, and a dimension score that is no longer the sum of its own evidence
is precisely what the evidence rule forbids. The S2 decomposition test is
re-run under all five types to prove it still holds.

The weight actually used is published per dimension as `profileWeight`, so a
caller can see it without dividing it back out.

## Demoted, never deleted

Attraction under `work-v1` weighs 0.15 and under `family-v1` weighs 0.2 — small,
but never zero. Zeroing a dimension would delete evidence rather than reweight
it, and the contacts are still there and still cited. Asserted: every demoted
dimension keeps a non-zero contact count and a non-zero activity.

## No default relationship type

Omitting the type resolves to `general-v1`, which weights every dimension at
1.0. That is not a fifth opinion about relationships — it is the absence of one.

Defaulting to `romantic-v1` would answer a question the caller never asked, and
a compatibility score is exactly where that assumption would be least welcome
and least visible. Asserted: an unspecified score is byte-identical to
`general-v1` and differs from `romantic-v1`.

An unrecognised type is refused rather than silently defaulted.

## One axis, deliberately

These profiles reweight dimensions and nothing else. They could also reweight
body pairs, aspect families, angles and overlays — and each of those would be
another table of editorial numbers with no reference to validate against. One
axis makes a work reading differ from a romantic one in the way that matters,
and keeps what changed between two readings legible.

## Verification

```
ruff   clean
mypy   clean, 100 source files
pytest 541 passed, 1258 subtests, 0 skipped   (533 -> 541)
```

API: `relationship_type` is an optional enum on `POST /v1/charts/compatibility`;
an unknown value is a 422 rather than a fallback. CLI:
`gbc compatibility --relationship-type work`.

Versions: engine 1.4.0 → 1.5.0, score schema 1.1.0 → 1.2.0. Additive — an
omitted type reproduces the previous behaviour exactly.

## Next

S4: strengths and challenges, ranked. It reads off the dimension scores rather
than carrying its own relevance weights, which is why the roadmap's order was
inverted for it.

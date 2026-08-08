# Unknown Birth Time Audit

Section 18 and 29. A chart without a birth time has no angles and no houses, so
nothing derived from them may be produced or approximated.

## Behaviour

| | Known time | Unknown time |
|---|---|---|
| Planet-to-planet transits | yes | **yes** |
| Ascendant / Midheaven targets | yes | **no** |
| Descendant / IC targets | no (by design) | no |
| House placements | yes | **no** |
| Ranking and `topAspects` | yes | **yes** |
| `meta.natalAngleTargetsIncluded` | `true` | `false` |
| Warning | none | `TRANSIT_HOUSE_PLACEMENT_UNAVAILABLE` |

Angle targets are omitted structurally, not filtered: `_natal_targets` reads
`natal_chart.angles`, which is empty for an unknown-time chart, so there is
nothing to exclude and nothing that could be substituted.

## Verification

`tests/integration/test_transit_profile.py::UnknownTimeTransitTests`

- no aspect has `natalTargetKind == "angle"`
- no aspect targets `ascendant`, `mc`, `descendant` or `ic`
- `transitHousePlacements` is empty and the warning is present
- planet-to-planet aspects are non-empty and ranked 1, 2, 3
- the same chart with a known time **does** include angle targets, so the
  test cannot pass vacuously

Measured: 14 aspects unknown-time versus 12 known-time on the reference chart at
the reference instant. Unknown-time is not smaller — it loses two angle targets
but the ten planets are unaffected.

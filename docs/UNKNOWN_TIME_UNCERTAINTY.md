# Unknown-birth-time uncertainty

Unknown time still publishes a natal chart anchored at local `00:00:00`. That
snapshot is a **calculation anchor**, not a known birth time. Houses, angles,
Vertex, Part of Fortune, and other angle-derived facts stay omitted. This
document describes the additive `unknownTimeAssessment` block (schema 1.9.0).

## Interval

For the supplied local civil date and IANA timezone:

```text
start = 00:00:00 local
end   = 23:59:59.999999 local
```

Each endpoint is converted independently with `normalize_local_datetime`. A
civil day may last 23 or 25 hours around DST. Interior sampling is uniform in
Julian Day between those UTC instants, not a walk of local clock hours.

Ambiguous or nonexistent endpoints raise the same errors as a known-time natal
at that civil instant. The interval object is not a `ChartInput` and is not two
known birth times.

## Sampling

Algorithm version: `uniform-jd-v1.1`.

1. Reuse the midnight natal positions as the start sample (labeled
   `anchorLongitude` on each body; not a resolved birth longitude).
2. Take 12 additional uniform JD samples (13 including endpoints).
3. Apply the conservative enclosure below. If a feature cannot be ruled out,
   probe the segment midpoint and/or refine with `find_roots` (bisection,
   tolerance `1e-5` days).
4. Stop if `provider.position` calls for the assessment exceed 768.

Known-time charts never run this path.

## Conservative enclosure

Sampled endpoint speed is **not** a proof. Between adjacent samples `dt` days
apart:

| Bound | Formula | Role |
|---|---|---|
| Travel | `\|Δλ\| ≤ vmax · dt` | Sign, orb, exact |
| Speed change | `\|Δv\| ≤ amax · dt` | Station |

`vmax = max(table_speed, 1.25·|v_start|, 1.25·|v_end|)`. `amax` is a tabulated
empirical acceleration ceiling (deg/day²). These are safety bounds for natal
bodies over ~2-hour segments, **not** a Keplerian enclosure of the solar
system. If a provider exceeds them, or the bound cannot rule out a crossing
that was not sampled, the property is `uncertain` with reason `bound_unproven`.

The Moon table speed is 16.5°/day. Twelve JD intervals on a 24-hour day are
~2 hours; travel bound ~1.4°, so a 30° sign cannot be entered and left between
samples without the bound noticing.

An aspect observed in-orb at every sample is labeled `presence: all_day`, but
`classification: stable` only when the travel bound also cannot reach the orb
edge and applying/separating does not reverse.

## Property-level body stability

Exact longitude is **always** time-dependent when birth time is unknown. Body
`classification: stable` is a roll-up of **sign** and **motionDirection** only.
It does not mean the ecliptic degree is known.

Each body reports:

- `anchorLongitude`: midnight calculation anchor
- `startLongitude` / `endLongitude` / `longitudeRange`: interval range
- `longitudeStatus`: always `uncertain`
- `signStatus` / `motionStatus`
- `stableProperties` / `uncertainProperties` (`longitude` is never stable)

## Evaluation cap (fail-closed)

Hitting 768 assessment evaluations sets `assessmentComplete: false` (also in
`provenance`). Every body and aspect is demoted to `uncertain` with reason
`evaluation_limit_reached`. Incomplete refinement never returns `stable`.

## Classification

- `stable` (body): sign and motion direction are proven for the interval.
  Longitude remains in `uncertainProperties`.
- `stable` (aspect): in orb the whole interval, bound cannot leave, phase does
  not reverse.
- `uncertain`: the property changes, the bound cannot prove it does not, or
  the evaluation cap was hit.
- `unavailable`: cannot be inferred without a known birth time (always includes
  angles, houses, house assignments, Vertex, antivertex, Part of Fortune,
  Ascendant-based chart ruler, house rulers, synastry house overlays,
  angularity).

Bodies are assessed for every chart body (default set plus opt-in Lilith).
Aspects follow the selected Standard / Extended / Custom profile and True/Mean
Node. Lilith is not added to Standard aspects.

Sidereal unknown-time uses the same Lahiri (or engine-profile) ayanamsa at every
sample. `provenance.frame` records `zodiac` and, when sidereal, `ayanamsa`,
`ayanamsaVersion`, and `ayanamsaDegrees`. Possible signs and ranges are in that
frame. Houses, angles, Vertex, and Part of Fortune stay unavailable.

359.8° → 0.2° is unwrapped along the short arc (range 0.4°, not 359.6°).

## Hash

v2 identity includes the normalized assessment (classifications, property
lists, interval, algorithm version, `assessmentComplete`). It omits evaluation
counts, raw samples, and warning prose. Known-time hashes do not gain an
assessment field.

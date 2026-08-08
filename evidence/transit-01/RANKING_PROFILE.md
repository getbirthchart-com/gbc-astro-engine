# Transit Ranking Profile

`transit-ranking-v1`, version `1.0.0`.

**A product relevance ordering, not a claim about astrological truth.** It
exists so a caller can show three things instead of twenty. No model of any kind
is involved.

```
score = aspect weight × transiting body weight × natal target weight
        × exactness × phase multiplier
```

## Weights

| Aspect | | Transiting body | | Natal target | |
|---|---:|---|---:|---|---:|
| conjunction | 1.0 | pluto | 1.00 | sun | 1.00 |
| opposition | 0.9 | neptune | 0.95 | moon | 1.00 |
| square | 0.9 | uranus | 0.90 | ascendant | 1.00 |
| trine | 0.7 | saturn | 0.85 | mc | 0.85 |
| sextile | 0.5 | jupiter | 0.70 | venus | 0.70 |
| | | mars | 0.55 | mars | 0.70 |
| | | sun | 0.50 | mercury | 0.60 |
| | | venus | 0.40 | saturn | 0.60 |
| | | mercury | 0.35 | jupiter | 0.55 |
| | | moon | 0.25 | uranus/neptune/pluto | 0.40 |

Exactness: 1.0 at exact, falling linearly to **0.35** at the orb limit.
Phase: exact 1.25, applying 1.15, separating 1.0, indeterminate 1.0.

## Reasoning

Slower transiting bodies outrank faster ones because their contacts last months
rather than hours. Hard aspects outrank soft ones because they are what people
notice. Contacts to the Sun, Moon and Ascendant outrank contacts to the outer
planets because they touch the chart's personal centre. Exactness separates
otherwise-equal contacts, with a floor so a wide contact between heavy bodies
does not vanish.

## Tie-breaking

`(-score, transiting body, natal target, aspect)` — by name, never by chance.
Nothing depends on dictionary or set iteration order. Tested by ranking the same
input in both orders and asserting identical output.

## Honest limits

Unlike the positions it ranks, this ordering has no independent reference to
validate against. It is an editorial opinion, published in full in
`meta.rankingProfileDetail` so it can be shown rather than asserted, and
versioned so changing it does not silently change stored results.

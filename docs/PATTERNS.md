# Chart patterns

Six named configurations, detected geometrically. A grand trine is three bodies
mutually trine within the profile's orb, or it is not reported — nothing here is
heuristic.

| Pattern | Definition |
|---|---|
| `stellium` | three or more bodies sharing a sign |
| `grand_trine` | three bodies mutually trine |
| `t_square` | two bodies in opposition, both square a third |
| `grand_cross` | two oppositions, square to each other |
| `yod` | two bodies sextile, both quincunx a third |
| `kite` | a grand trine with a fourth body opposite one corner and sextile the other two |

```python
for pattern in engine.patterns(natal):
    print(pattern.id, round(pattern.max_leg_orb, 2))
```

```
pattern.t_square.jupiter.mars.neptune   3.58
pattern.yod.mars.mercury.pluto          1.15
```

## Profile: `pattern-v1`

| Leg | Orb |
|---|---:|
| conjunction | 6° |
| sextile | 4° |
| square | 6° |
| trine | 6° |
| **quincunx** | **3°** |
| opposition | 6° |

### Why tighter than the aspect orbs

The natal profile allows 8° on a conjunction, which is right for reading a single
aspect and far too loose for a multi-body figure. A three-body pattern
accumulates its legs' error: at 8° a leg, a "grand trine" can be 24° out of true
and still be reported. These values keep a detected figure recognisable on the
wheel.

The quincunx is tighter still, at 3°, because a yod built on two loose quincunxes
is not a yod anyone would draw.

### Why the quincunx is here at all

Yods need it, and it is not part of the major-aspect profile. Pattern detection
therefore carries its own angle table rather than borrowing one.

### Which bodies take part

The ten planets. A grand trine that needs the mean node to close is not a grand
trine anyone draws, so nodes and Chiron are excluded — declared in the profile,
not hidden in the code.

## Containment

Every grand cross contains two T-squares. Every kite contains a grand trine.
Reporting all of them says the same thing three times, so the contained figure is
suppressed.

```
grand cross detected  →  its two T-squares are not also reported
kite detected         →  its grand trine is not also reported
```

Set `suppress_contained_patterns=False` on the profile to see everything.

## Max leg orb

Every pattern reports the widest orb among its legs. That number is what tells a
reader whether the figure is tight enough to matter: a grand cross with a 5° leg
and one with a half-degree leg are not the same object, and only this field
distinguishes them.

For a stellium, which has no legs, the field carries the span in degrees between
the first and last body instead.

## Validation

There is no external reference for "is this a grand trine", so every figure is
built by hand at exact longitudes and the detector is asked to find it. Every
positive test has a matching negative one just outside the orb, because a
detector that finds everything is worth as little as one that finds nothing.

| Check | Covered |
|---|---|
| Exact figure detected | all six |
| Just inside orb detected | grand trine |
| Just outside orb rejected | grand trine, yod |
| Partial figure rejected | grand trine, t-square, yod, stellium |
| Containment suppressed | grand cross, kite |
| Non-participating body ignored | grand trine via the node |
| Identifiers deterministic and sorted | all |

## Limitations

- Mystic rectangle, grand sextile and the harder-to-agree-on figures are not
  implemented.
- Angles do not participate. An Ascendant in a T-square is a real thing
  astrologically; admitting it here would need a declared orb policy for angle
  legs, which this profile does not define.
- A stellium is grouped by sign, so three bodies spanning 28°–31° are two groups
  rather than one. That is the declared convention, not an accident.

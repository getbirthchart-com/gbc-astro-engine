# Secondary progressions and solar arc

Both map life onto ephemeris motion at one day per year. The astronomy is
ordinary; the mapping is what is symbolic.

## Secondary progressions

The chart for the tenth day after birth is the chart of the tenth year. The
progressed chart is cast for that instant **at the birthplace**, so it is an
ordinary chart with real positions, real speeds and real houses.

```python
progressed = engine.progressions(natal, datetime(2026, 8, 8, tzinfo=timezone.utc))
progressed.meta["elapsedYears"]        # 33.76
progressed.meta["progressedInstant"]   # birth + 33.76 days
```

Exact by construction: age 0 returns the birth instant itself, age 1 returns
birth plus exactly one day.

A known birth time is required. One day of error in the progressed instant is a
whole year of symbolic time, so an unknown-time chart is refused rather than
progressed from an assumed hour.

## Solar arc

Takes the distance the progressed Sun has travelled and applies that **one arc
to every natal point**, angles included.

```python
directed = engine.solar_arc(natal, target)
directed.meta["solarArcDegrees"]   # ~1 degree per year of life
```

Because a single arc moves everything, solar arc is a **rotation**. The directed
points hold exactly their natal aspects to one another — a directed square is
the same square it always was. Only contacts between a directed point and the
**natal** chart carry information. The chart says so in
`SOLAR_ARC_IS_A_ROTATION` rather than leaving it to be discovered.

The arc is unwrapped, not folded: past 180 years of symbolic time it keeps
growing rather than reversing sign.

Directed points carry no speed and no retrograde state. A directed point is a
symbolic construction, not a moving body.

## Profiles

| | `secondary-progression-v1` | `solar-arc-v1` |
|---|---|---|
| Year length | tropical, 365.2422 d | tropical, 365.2422 d |
| Angles | cast at the progressed instant | advanced by the solar arc |

### On the year length

Tropical versus Julian is declared for reproducibility, not because it changes a
reading. Measured: over 100 years of life the two progressed instants differ by
**3.1 minutes**, about **7.7 arcseconds** of progressed Sun. Accumulating a full
day of divergence would take roughly 47,000 years of life.

This documentation originally claimed the divergence was a day per 128 years.
That was wrong by four orders of magnitude, and the test written to demonstrate
it failed and caught the error.

### On the angle method

Genuinely contested. Solar arc, Naibod, daily motion of the Midheaven and the
quotidian methods all produce different progressed Midheavens, and no
calculation arbitrates between them.

Secondary progressions here use the angles of the chart actually cast for the
progressed instant — the daily-motion convention, which falls out of casting
rather than being applied on top. Solar arc advances the natal angles by the
arc. Both are named in `meta.progressionProfile.angleMethod`; the other methods
are not implemented.

## No houses on a directed chart

`solar_arc` produces no cusps. The houses of the moment belong to the natal
chart, and directing them by the same arc would be a separate convention this
profile does not define.

Secondary progressions *do* have houses, because the progressed chart is a real
chart of a real instant at a real place.

## CLI

```bash
gbc progressions --date 1992-11-03 --time 14:35 --timezone Asia/Ho_Chi_Minh \
  --lat 21.0285 --lng 105.8542 --at 2026-08-08T00:00:00Z --json

gbc solar-arc --date 1992-11-03 --time 14:35 --timezone Asia/Ho_Chi_Minh \
  --lat 21.0285 --lng 105.8542 --at 2026-08-08T00:00:00Z --json
```

## Validation

Exact properties, asserted rather than approximated:

| Property | Holds |
|---|---|
| Age 0 progresses to the birth instant | exactly |
| Age 1 progresses to birth + 1 day | exactly |
| The mapping is linear in age | exactly |
| Age 0 gives a zero solar arc | exactly |
| The arc grows at 0.95–1.05°/year | measured |
| Every point advances by the same arc | exactly |
| Directed aspects equal natal aspects | exactly |

## Limitations

- Only one angle method each; Naibod and the quotidian family are not
  implemented.
- Tertiary and minor progressions are not implemented.
- Converse directions are not implemented, though a target before birth does
  progress backwards correctly.

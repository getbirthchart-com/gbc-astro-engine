# Ephemeris generator and optional bodies

## Optional bodies

| id | What it is | Needs |
|---|---|---|
| `ceres` `pallas` `juno` `vesta` | the four main-belt asteroids | `seas_18.se1` |
| `mean_lilith` | mean lunar apogee | `seas_18.se1` |
| `true_lilith` | osculating lunar apogee | `seas_18.se1` |
| `asteroid_<number>` | any numbered asteroid | `se<number>.se1` |

The first six ride along in the same file that carries Chiron, so any
installation with Chiron already has them. A numbered asteroid needs its own
data file, and whether `asteroid_433` works depends entirely on what was
provisioned.

### Ask, do not discover

`01_MASTER_REQUIREMENTS.md` section 4 requires the provider layer to "expose
capability metadata rather than making unsupported bodies fail unpredictably".

```python
for capability in engine.optional_bodies(extra=("asteroid_433",)):
    print(capability.body_id, capability.available, capability.reason)
```

```
ceres          True   None
vesta          True   None
asteroid_433   False  Swiss Ephemeris data for this body is not provisioned.
                      Numbered asteroids each need their own se<number>.se1 file.
```

Availability is **probed**, not guessed. The only reliable way to know whether a
data file is present is to ask for a position and see.

Optional bodies are not part of the v0.1 chart contract and are not added to
natal charts automatically. They are available to the provider, to the ephemeris
generator, and to anything that asks for them by name.

## Ephemeris generator

A table of positions over a range at a fixed step.

```python
table = engine.ephemeris(
    ("sun", "moon"),
    datetime(2026, 1, 1, tzinfo=timezone.utc),
    datetime(2026, 12, 31, tzinfo=timezone.utc),
    timedelta(days=1),
)
```

Both ends of the range are inclusive. Sub-daily steps work. Asteroids can be
tabulated alongside planets.

### One row equals one call

The generator is a convenience, not a second calculation path. Every row is
exactly what a single-instant provider call returns, and a test asserts that
field by field rather than trusting it.

### Bounded memory

`01_MASTER_REQUIREMENTS.md` section 16 asks for batch calculation with bounded
memory. `iter_ephemeris` yields rows lazily, so a ten-thousand-day range costs
one row of memory:

```python
for row in iter_ephemeris(provider, ("sun",), start, end, timedelta(days=1)):
    ...
```

`generate_ephemeris` materialises the same rows when a whole table is wanted.

### Refusals

- More than `max_rows` (200,000 by default) is refused rather than attempted. A
  step of seconds over a range of centuries is almost always a mistake, and a
  caller who means it can raise the limit deliberately.
- Naive datetimes, inverted ranges and non-positive steps are all refused.
- Unsupported bodies are refused **before** any calculation starts, not
  discovered on row nine thousand.

## Limitations

- Asteroid positions are not independently validated. Chiron is, against JPL
  Horizons; extending that method to Ceres and the rest is open work, and the
  same `tools/fetch_chiron_horizons.py` approach would generalise.
- The generator emits positions only. Houses need a place as well as a time, and
  a table of them would be a different object.

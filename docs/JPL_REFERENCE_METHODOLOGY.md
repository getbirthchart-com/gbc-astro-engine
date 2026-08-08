# JPL Reference Methodology

This document defines the independent astronomy reference path used by
`gbc validate astronomy-parity --reference jpl-de440`.

## Scope

The JPL path validates astronomy only:

- Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto
- apparent geocentric tropical ecliptic longitude
- apparent geocentric ecliptic latitude
- longitude speed
- retrograde state derived from longitude speed

It does not validate Ascendant, MC, house cusps, Placidus, or planet house
assignment. Those require a separate astrology-geometry reference.

## Data And Library Path

The reference provider is `JplReferenceSource`, identified as `jpl-de440`.
It reads a local JPL binary SPK kernel through Skyfield and does not call Swiss
Ephemeris or the Swiss binary.

Configuration is explicit:

```bash
export GBC_JPL_EPHEMERIS_PATH=/opt/gbc/jpl/de440s.bsp
```

or:

```bash
gbc validate astronomy-parity \
  --reference jpl-de440 \
  --jpl-ephemeris-path /opt/gbc/jpl/de440s.bsp
```

If a directory is supplied, the provider expects `de440s.bsp` inside it.

## Transformation Pipeline

For each validation case:

1. Resolve the supplied naive local datetime through IANA `zoneinfo`.
2. Preserve PEP 495 `fold` for ambiguous DST local times.
3. Convert to timezone-aware UTC.
4. Build a Skyfield UTC time from that instant.
5. Use the Earth geocenter as the observer center.
6. Observe the target body from Earth using the JPL SPK kernel.
7. Apply Skyfield apparent-position correction, including light-time and
   aberration handling.
8. Convert to true ecliptic and equinox of date using
   `apparent.ecliptic_latlon(epoch="date")`.
9. Compare longitude on the normalized circular range `[0, 360)`.
10. Compare latitude directly in degrees.

This matches the GBC/Swiss comparison convention: apparent geocentric tropical
ecliptic coordinates.

## Body Targets

The compact DE440S kernel supplies direct centers for the Sun, Moon, Mercury,
Venus, and Earth. For Mars and the outer planets it supplies barycenters, so the
reference target map is:

| Body | JPL target |
|---|---|
| Sun | `sun` |
| Moon | `moon` |
| Mercury | `mercury` |
| Venus | `venus` |
| Mars | `mars barycenter` |
| Jupiter | `jupiter barycenter` |
| Saturn | `saturn barycenter` |
| Uranus | `uranus barycenter` |
| Neptune | `neptune barycenter` |
| Pluto | `pluto barycenter` |

This is documented as a residual model difference. The resulting longitude and
latitude deltas are measured directly in the parity report rather than hidden.

## Longitude Speed

Longitude speed is calculated independently from JPL by finite-differencing the
same apparent ecliptic-of-date longitude used for position comparison.

The default step is 60 seconds:

- central difference when both sample points remain on the same UTC date;
- forward one-sided difference near the beginning of a UTC date;
- backward one-sided difference near the end of a UTC date.

The same-day guard avoids introducing a false speed jump from the moving
true-of-date frame at UTC date boundaries. Retrograde state is `speed < 0`.
Near station boundaries, mismatches are classified separately instead of being
treated as numerical longitude failures.

## Tolerance Profile

The versioned profile is `astronomy-jpl-parity-v1`.

The profile is intentionally separate from the older all-in-one natal parity
tolerance because this track validates astronomy only. Moon tolerances are
looser than other bodies because lunar model and frame residuals are larger.
Speed tolerances cover residual JPL-vs-Swiss model and target-center
differences, especially for compact-kernel barycenter targets.

Large unexplained deltas are not resolved by loosening the profile; they must be
classified before the report can pass.

## Bodies Not Present in DE440S

DE440S contains the Sun, the Moon, Earth and the planetary barycenters, and
nothing else. Two parts of the v0.1 body contract therefore cannot be looked up
in the kernel and are derived or captured instead.

### Lunar nodes

Neither node is a body. Both are derived independently of Swiss Ephemeris:

- **True node** — the ascending node of the Moon's instantaneous geocentric
  orbit, from Skyfield osculating elements in the ecliptic frame of date.
- **Mean node** — the mean-element polynomial for the Moon's ascending node
  (Meeus, *Astronomical Algorithms*, ch. 47), **plus nutation in longitude**.

That nutation term is not cosmetic. Without it the mean node disagrees with
Swiss Ephemeris by up to 17 arcseconds, and the residual tracks the nutation
cycle exactly: the Meeus series is referred to the mean equinox of date, while
Swiss Ephemeris reports the node against the true equinox. Adding the term
brings agreement to roughly 0.1 arcsecond. The discrepancy was diagnosed rather
than absorbed into a wider tolerance.

Node latitude is required to be exactly zero on both sides, not merely small,
because both nodes are ecliptic points by definition.

The true node passes through stationary points where it briefly turns direct.
The sign of a speed of order 1e-04 deg/day carries no meaning, so such cases are
classified `STATION_BOUNDARY_CONVENTION` rather than counted as mismatches.

### Chiron

Chiron is a minor planet and is absent from DE440S. It is validated against a
frozen capture from **JPL Horizons** (`COMMAND='2060;'`, `QUANTITIES=31`,
geocentric, ecliptic of date), which rests on JPL's own small-body orbit
solution and is independent of the Swiss `seas_18.se1` integration under
validation.

The capture is committed at `tests/fixtures/chiron_horizons_reference.json` and
read offline, so the gate is deterministic and needs no network access in CI.
Regenerate it with `python tools/fetch_chiron_horizons.py`; the fixture records
`capturedAt` so staleness is visible.

Run it with `gbc validate chiron-parity`. Report:
`evidence/v0.1-validation/CHIRON_PARITY.md`.

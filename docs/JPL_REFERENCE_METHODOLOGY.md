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

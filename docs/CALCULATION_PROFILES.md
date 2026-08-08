# Calculation Profiles

## `western-modern-v1`

Current default profile:

- zodiac: `tropical`
- house system: `placidus`
- node type: `true`
- aspect profile: `modern-major-v1`
- unknown-time policy: `local_date_start_with_uncertainty_warning`
- cusp policy: `exact_cusp_belongs_to_following_house`

## Aspect Defaults

`modern-major-v1` includes:

- conjunction: 0 degrees, 8 degree orb
- sextile: 60 degrees, 5 degree orb
- square: 90 degrees, 7 degree orb
- trine: 120 degrees, 7 degree orb
- opposition: 180 degrees, 8 degree orb

Applying/separating is determined from relative angular motion by comparing the
orb after a short deterministic timestep. If either body is missing longitude
speed, the phase is `indeterminate`.

## House Behavior

Supported v0.1 house systems:

- `whole_sign`
- `equal`
- `placidus`

Whole Sign and Equal cusps are derived from a validated Ascendant supplied by the
house calculator. Placidus is delegated to Swiss Ephemeris. The engine does not
silently fall back from Placidus to another house system when Swiss Ephemeris
cannot calculate a result, including high-latitude cases.

Cusp assignment policy: a body exactly on cusp N belongs to house N.

## Unknown Birth Time

Unknown-time mode must be requested explicitly. The engine:

- accepts a local date only;
- resolves the start of that local date through the supplied IANA timezone;
- emits an `UNKNOWN_BIRTH_TIME` warning;
- omits angles, houses and body house assignments;
- keeps `derived.bigThree.rising` as `null`.

This is intentionally not a hidden noon substitution and should not be displayed
as an exact birth-time chart.


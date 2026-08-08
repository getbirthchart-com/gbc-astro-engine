# Current Engine Audit

Read before writing any transit code, per section 1.

## Reusable primitives found

| Need | Existing code | Reused? |
|---|---|---|
| Planetary positions | `providers.swiss.SwissEphemerisProvider.position` | yes, unchanged |
| Position normalisation | `providers.normalization.normalize_body_position` | yes, unchanged |
| Aspect rule matching | `aspects.engine.match_aspect_rule` | yes, unchanged |
| Circular separation | `astronomy.circular.shortest_angular_distance` | yes, unchanged |
| House assignment | `houses.base.assign_house` | yes, unchanged |
| Zodiac mapping | `zodiac.tropical.longitude_to_tropical` | yes, via normalisation |
| Time normalisation | `astronomy.time` | yes, unchanged |
| Error envelope | `errors` + `api.errors` | yes, no new codes |

No validated core math was modified. Rule 1 was not engaged: nothing in the
transit path required changing natal calculation, and no defect in it surfaced.

## Canonical identifiers

Bodies: `sun moon mercury venus mars jupiter saturn uranus neptune pluto
true_node mean_node chiron` (`constants.BODY_IDS`).
Angles: `ascendant mc descendant ic` (`NatalChart.angles`).
Aspects: `conjunction sextile square trine opposition`
(`profiles.model.AspectRule`).

## Existing aspect orbs

`modern-major-v1`: conjunction 8, opposition 8, square 7, trine 7, sextile 5.
Suitable for natal, not for transits — see `ASPECT_PROFILE.md`.

## Provider capabilities

Swiss Ephemeris 2.10.03 with `sepl_18/semo_18/seas_18`. Positions carry
longitude, latitude, distance and longitude speed, so retrograde and
applying/separating are available without approximation.

## Time-scale behaviour

Natal input is local civil time plus an IANA zone; the engine owns DST and
historical offsets. Providers are called with timezone-aware UTC datetimes.
Transits therefore take a UTC instant directly and reject naive datetimes,
rather than reusing natal local-time semantics.

## Prior state

A transit snapshot already existed from v0.3 (Phases 10-12) with positions,
aspects, house placements and real applying/separating. Missing against this
brief: a dedicated orb profile, deterministic IDs, ranking, a top-N subset,
angle targets, full provenance, and the documentation and evidence set.

## Blockers

None.

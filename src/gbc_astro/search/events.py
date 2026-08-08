"""Astronomical event search built on the generic solver.

Every search here is a root find, never a scan for the closest sample. The
quantity that crosses zero differs per event type:

* exact longitude -- signed circular distance from the target longitude
* sign ingress     -- the same, against each 30 degree boundary
* station          -- longitude speed
* aspect to a fixed point -- signed distance to each of the two longitudes at
  which the aspect is exact

Retrograde motion means several of these can happen more than once in a window,
and that is not an edge case to be smoothed over: a Mercury station-retrograde
loop crosses the same degree three times, and a Saturn return commonly has three
exact hits. The solver returns all of them, in order.

Coarse step
-----------
`find_roots` can only find what its coarse step brackets: two roots inside one
step cancel and both are lost. The step therefore has to come from how fast the
body actually moves, which is what `COARSE_STEP_DAYS` records. The Moon covers
thirteen degrees a day and needs a step measured in hours; Pluto does not.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from gbc_astro.astronomy.circular import directed_circular_delta, normalize_longitude
from gbc_astro.astronomy.time import isoformat_z, julian_day_to_datetime
from gbc_astro.constants import SIGN_IDS
from gbc_astro.providers.base import EphemerisProvider
from gbc_astro.search.solver import Root, find_roots

# Per-body coarse step, in days. Chosen so that no two roots of any supported
# search can fall inside a single step for that body.
COARSE_STEP_DAYS: dict[str, float] = {
    "moon": 0.2,
    "mercury": 0.5,
    "venus": 0.5,
    "sun": 1.0,
    "mars": 1.0,
    "true_node": 1.0,
    "mean_node": 1.0,
    "jupiter": 2.0,
    "saturn": 2.0,
    "chiron": 3.0,
    "uranus": 5.0,
    "neptune": 5.0,
    "pluto": 5.0,
}
DEFAULT_COARSE_STEP_DAYS = 1.0

# A longitude residual wraps by 360; anything above this is a wrap, not a root.
ANGULAR_DISCONTINUITY = 180.0

# A speed residual has no wrap, but a provider glitch would show as a huge jump.
SPEED_DISCONTINUITY = 10.0


@dataclass(frozen=True)
class AstroEvent:
    """One located event, in the shape of the canonical event contract."""

    event_type: str
    body: str
    instant_utc: str
    julian_day: float
    longitude: float
    direction: str
    precision_seconds: float
    detail: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.event_type,
            "body": self.body,
            "instantUtc": self.instant_utc,
            "julianDay": self.julian_day,
            "longitude": self.longitude,
            "direction": self.direction,
            "precisionSeconds": self.precision_seconds,
            "detail": self.detail,
        }


def coarse_step_for(body: str) -> float:
    return COARSE_STEP_DAYS.get(body, DEFAULT_COARSE_STEP_DAYS)


class EphemerisFunction:
    """Adapter turning a provider into functions of Julian Day.

    The solver needs a continuous real function; the provider speaks datetimes.
    Results are memoised because bisection asks for the same instant repeatedly
    and every call is an ephemeris lookup.

    `zodiac_offset` moves the longitudes into the chart's zodiac. Providers
    always answer tropically, so without it a sidereal chart would be searched
    against tropical positions: a solar return would be looked for at a
    longitude the Sun does not reach for another 24 days, and a sign ingress
    would report the tropical boundary. Speed is unaffected -- the ayanamsa
    drifts 50 arcseconds a year, which is below anything a station search can
    see -- so only longitude is shifted.
    """

    def __init__(
        self,
        provider: EphemerisProvider,
        body: str,
        zodiac_offset: Callable[[float], float] | None = None,
    ) -> None:
        self.provider = provider
        self.body = body
        self.zodiac_offset = zodiac_offset
        self._cache: dict[float, tuple[float, float | None]] = {}

    def _at(self, julian_day: float) -> tuple[float, float | None]:
        cached = self._cache.get(julian_day)
        if cached is None:
            raw = self.provider.position(self.body, julian_day_to_datetime(julian_day))
            longitude = raw.longitude_deg
            if self.zodiac_offset is not None:
                longitude -= self.zodiac_offset(julian_day)
            cached = (
                normalize_longitude(longitude),
                raw.longitude_speed_deg_per_day,
            )
            self._cache[julian_day] = cached
        return cached

    def longitude(self, julian_day: float) -> float:
        return self._at(julian_day)[0]

    def speed(self, julian_day: float) -> float:
        speed = self._at(julian_day)[1]
        return 0.0 if speed is None else speed

    def signed_distance_to(self, julian_day: float, target_longitude: float) -> float:
        """Signed shortest arc from the target to the body, in (-180, 180]."""
        return directed_circular_delta(target_longitude, self.longitude(julian_day))


def _direction_at(function: EphemerisFunction, julian_day: float) -> str:
    speed = function.speed(julian_day)
    if speed > 0.0:
        return "direct"
    if speed < 0.0:
        return "retrograde"
    return "stationary"


def _event_from_root(
    function: EphemerisFunction,
    root: Root,
    event_type: str,
    detail: dict[str, object],
) -> AstroEvent:
    longitude = function.longitude(root.julian_day)
    return AstroEvent(
        event_type=event_type,
        body=function.body,
        instant_utc=isoformat_z(julian_day_to_datetime(root.julian_day)),
        julian_day=root.julian_day,
        longitude=longitude,
        direction=_direction_at(function, root.julian_day),
        precision_seconds=root.precision_seconds,
        detail={**detail, "solver": root.to_dict()},
    )


def find_longitude_crossings(
    provider: EphemerisProvider,
    body: str,
    target_longitude: float,
    start: datetime,
    end: datetime,
    coarse_step_days: float | None = None,
    zodiac_offset: Callable[[float], float] | None = None,
) -> tuple[AstroEvent, ...]:
    """Every instant the body's longitude equals `target_longitude`.

    Returns all crossings, not the first: a retrograde loop crosses the same
    degree three times and all three are real.
    """
    from gbc_astro.astronomy.time import datetime_to_julian_day

    function = EphemerisFunction(provider, body, zodiac_offset)
    target = normalize_longitude(target_longitude)
    roots = find_roots(
        lambda jd: function.signed_distance_to(jd, target),
        datetime_to_julian_day(start),
        datetime_to_julian_day(end),
        coarse_step_days or coarse_step_for(body),
        discontinuity_threshold=ANGULAR_DISCONTINUITY,
    )
    return tuple(
        _event_from_root(
            function, root, "exact_longitude", {"targetLongitude": target}
        )
        for root in roots
    )


def find_sign_ingresses(
    provider: EphemerisProvider,
    body: str,
    start: datetime,
    end: datetime,
    coarse_step_days: float | None = None,
    zodiac_offset: Callable[[float], float] | None = None,
) -> tuple[AstroEvent, ...]:
    """Every crossing of a 30 degree sign boundary, in either direction.

    A retrograde body re-enters the sign it just left, so the same boundary can
    be crossed three times in a few weeks. Each crossing is its own event, and
    `direction` says which way it went.
    """
    events: list[AstroEvent] = []
    for index in range(12):
        boundary = index * 30.0
        for event in find_longitude_crossings(
            provider, body, boundary, start, end, coarse_step_days, zodiac_offset
        ):
            entering = SIGN_IDS[index] if event.direction != "retrograde" else SIGN_IDS[index - 1]
            leaving = SIGN_IDS[index - 1] if event.direction != "retrograde" else SIGN_IDS[index]
            events.append(
                AstroEvent(
                    event_type="sign_ingress",
                    body=event.body,
                    instant_utc=event.instant_utc,
                    julian_day=event.julian_day,
                    longitude=event.longitude,
                    direction=event.direction,
                    precision_seconds=event.precision_seconds,
                    detail={
                        "boundaryLongitude": boundary,
                        "enteringSign": entering,
                        "leavingSign": leaving,
                        "solver": event.detail["solver"],
                    },
                )
            )
    return tuple(sorted(events, key=lambda item: item.julian_day))


def find_stations(
    provider: EphemerisProvider,
    body: str,
    start: datetime,
    end: datetime,
    coarse_step_days: float | None = None,
    zodiac_offset: Callable[[float], float] | None = None,
) -> tuple[AstroEvent, ...]:
    """Instants where longitude speed changes sign.

    A station is where the speed is zero, so the residual is the speed itself
    rather than an angle. The Sun and Moon never station; the outer planets do
    so twice a year.
    """
    from gbc_astro.astronomy.time import datetime_to_julian_day

    function = EphemerisFunction(provider, body, zodiac_offset)
    roots = find_roots(
        function.speed,
        datetime_to_julian_day(start),
        datetime_to_julian_day(end),
        coarse_step_days or coarse_step_for(body),
        discontinuity_threshold=SPEED_DISCONTINUITY,
    )

    events: list[AstroEvent] = []
    for root in roots:
        before = function.speed(root.julian_day - 0.5)
        after = function.speed(root.julian_day + 0.5)
        station_type = "station_retrograde" if before > 0.0 > after else "station_direct"
        events.append(
            AstroEvent(
                event_type=station_type,
                body=body,
                instant_utc=isoformat_z(julian_day_to_datetime(root.julian_day)),
                julian_day=root.julian_day,
                longitude=function.longitude(root.julian_day),
                direction="stationary",
                precision_seconds=root.precision_seconds,
                detail={
                    "speedBefore": before,
                    "speedAfter": after,
                    "solver": root.to_dict(),
                },
            )
        )
    return tuple(events)


def find_aspect_events(
    provider: EphemerisProvider,
    body: str,
    reference_longitude: float,
    aspect_angle: float,
    start: datetime,
    end: datetime,
    coarse_step_days: float | None = None,
    zodiac_offset: Callable[[float], float] | None = None,
) -> tuple[AstroEvent, ...]:
    """Every instant the body is exactly `aspect_angle` from a fixed longitude.

    An aspect is exact at two longitudes, one either side of the reference, so
    this is two crossing searches rather than a search on the separation itself.
    Searching the separation directly would fail: it touches zero without
    changing sign, which no bracketing scheme can see.

    Conjunction and opposition collapse to a single target and are deduplicated.
    """
    reference = normalize_longitude(reference_longitude)
    targets = {
        normalize_longitude(reference + aspect_angle),
        normalize_longitude(reference - aspect_angle),
    }

    events: list[AstroEvent] = []
    for target in sorted(targets):
        for event in find_longitude_crossings(
            provider, body, target, start, end, coarse_step_days, zodiac_offset
        ):
            events.append(
                AstroEvent(
                    event_type="exact_aspect",
                    body=event.body,
                    instant_utc=event.instant_utc,
                    julian_day=event.julian_day,
                    longitude=event.longitude,
                    direction=event.direction,
                    precision_seconds=event.precision_seconds,
                    detail={
                        "referenceLongitude": reference,
                        "aspectAngle": aspect_angle,
                        "targetLongitude": target,
                        "solver": event.detail["solver"],
                    },
                )
            )
    return tuple(sorted(events, key=lambda item: item.julian_day))

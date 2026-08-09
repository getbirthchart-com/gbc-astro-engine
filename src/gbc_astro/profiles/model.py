"""Immutable profile models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AspectRule:
    aspect_type: str
    exact_angle: float
    orb: float


@dataclass(frozen=True)
class AspectProfile:
    id: str
    version: str
    rules: tuple[AspectRule, ...]
    exact_epsilon_deg: float = 1e-8


@dataclass(frozen=True)
class RelationshipProfile:
    """Versioned methodology for synastry and composite charts.

    The spec requires composite house and angle methodology to be stated by
    profile rather than assumed, because schools disagree. Anything this profile
    leaves as `None` is not produced at all, instead of being approximated.
    """

    id: str
    version: str
    # Composite aspects. A composite chart is a chart -- midpoint positions read
    # the way a natal chart is read -- so it keeps the natal orb policy.
    aspect_profile: AspectProfile
    # Cross-chart aspects, versioned separately so a future change to natal orbs
    # cannot silently move every synastry contact and invalidate the evidence IDs
    # already referenced by stored scores.
    synastry_aspect_profile: AspectProfile
    synastry_bodies: tuple[str, ...]
    synastry_angles: tuple[str, ...]
    composite_position_method: str
    composite_angle_method: str | None
    composite_house_method: str | None
    composite_house_system: str
    composite_reference_latitude_method: str
    composite_obliquity_epoch: str
    davison_location_method: str
    cross_aspect_phase_policy: str


@dataclass(frozen=True)
class CalculationProfile:
    id: str
    version: str
    zodiac: str
    house_system: str
    node_type: str
    aspect_profile: AspectProfile
    unknown_time_policy: str
    balance_bodies: tuple[str, ...]
    cusp_policy: str = "exact_cusp_belongs_to_following_house"
    # Which bodies may form an aspect. Narrower than the bodies the chart
    # reports, and deliberately so: a chart publishes both the true and the mean
    # lunar node because a caller may want either, but they are one point
    # computed two ways. Aspecting both doubles every node contact and produces
    # a permanent "node conjunct node" in every chart ever cast. The engine
    # refuses a profile that lists both -- see `AstrologyEngine._validate_profile`.
    aspect_bodies: tuple[str, ...] = ()
    # Which rulership table names the chart ruler, the house rulers and every
    # dispositor chain. It belongs to the profile rather than to the request
    # because it is not independent of the rest of it: a sidereal chart cast in
    # the Vedic tradition uses the classical seven, and offering it Pluto as the
    # ruler of Scorpio would be answering in the wrong system entirely.
    rulership: str = "modern"
    # Which derived points are produced, and which convention the Lot of
    # Fortune follows below the horizon. Profile-scoped for the same reason the
    # ayanamsa is: the two conventions disagree on about half of all charts.
    points: str = "western"
    # Required when `zodiac` is "sidereal", ignored otherwise. No default is
    # applied for a sidereal profile: the schools disagree by whole degrees, so
    # picking one silently would be picking an answer.
    ayanamsa: str | None = None


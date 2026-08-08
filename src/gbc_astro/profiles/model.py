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
    aspect_profile: AspectProfile
    synastry_bodies: tuple[str, ...]
    synastry_angles: tuple[str, ...]
    composite_position_method: str
    composite_angle_method: str | None
    composite_house_method: str | None
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


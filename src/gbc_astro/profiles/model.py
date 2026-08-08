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


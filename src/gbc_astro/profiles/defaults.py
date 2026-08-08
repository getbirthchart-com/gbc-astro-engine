"""Default western-modern v0.1 profile."""

from __future__ import annotations

from gbc_astro.constants import CLASSICAL_BALANCE_BODIES
from gbc_astro.profiles.model import AspectProfile, AspectRule, CalculationProfile

MODERN_MAJOR_V1 = AspectProfile(
    id="modern-major-v1",
    version="1.0.0",
    rules=(
        AspectRule("conjunction", 0.0, 8.0),
        AspectRule("sextile", 60.0, 5.0),
        AspectRule("square", 90.0, 7.0),
        AspectRule("trine", 120.0, 7.0),
        AspectRule("opposition", 180.0, 8.0),
    ),
)

WESTERN_MODERN_V1 = CalculationProfile(
    id="western-modern-v1",
    version="1.0.0",
    zodiac="tropical",
    house_system="placidus",
    node_type="true",
    aspect_profile=MODERN_MAJOR_V1,
    unknown_time_policy="local_date_start_with_uncertainty_warning",
    balance_bodies=CLASSICAL_BALANCE_BODIES,
)


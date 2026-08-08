"""Default western-modern v0.1 profile."""

from __future__ import annotations

from gbc_astro.constants import BODY_IDS, CLASSICAL_BALANCE_BODIES
from gbc_astro.profiles.model import (
    AspectProfile,
    AspectRule,
    CalculationProfile,
    RelationshipProfile,
)

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


VEDIC_SIDEREAL_V1 = CalculationProfile(
    id="vedic-sidereal-v1",
    version="1.0.0",
    zodiac="sidereal",
    # Whole Sign is the near-universal choice in Vedic practice, and unlike
    # Placidus it is defined at every latitude.
    house_system="whole_sign",
    node_type="true",
    aspect_profile=MODERN_MAJOR_V1,
    unknown_time_policy="local_date_start_with_uncertainty_warning",
    balance_bodies=CLASSICAL_BALANCE_BODIES,
    ayanamsa="lahiri",
)


RELATIONSHIP_WESTERN_V1 = RelationshipProfile(
    id="relationship-western-v1",
    version="1.0.0",
    aspect_profile=MODERN_MAJOR_V1,
    synastry_bodies=BODY_IDS,
    synastry_angles=("ascendant", "mc", "descendant", "ic"),
    # Shortest-arc midpoint of each corresponding pair of body longitudes.
    composite_position_method="shortest_arc_midpoint",
    # Composite Midheaven is the shortest-arc midpoint of the two Midheavens;
    # the Ascendant and every cusp are then DERIVED from it rather than averaged
    # separately. Averaging each angle independently is the more common shortcut
    # and it produces an Ascendant and Midheaven that do not hold the geometric
    # relationship a real chart's angles do. Deriving removes that defect
    # instead of documenting it.
    composite_angle_method="midpoint_mc_derived_angles",
    # Composite houses come from the derived ARMC at a reference latitude. This
    # needs no time or place that the composite chart lacks: ARMC follows from
    # the composite Midheaven, and the latitude is declared below.
    composite_house_method="armc_from_midpoint_mc",
    composite_house_system="placidus",
    # Latitudes are not circular, so the plain mean is correct here.
    composite_reference_latitude_method="mean_of_birth_latitudes",
    # A composite chart has no instant, but obliquity needs one. The midpoint of
    # the two Julian Days is the same instant the Davison chart uses, which
    # keeps the two constructions consistent.
    composite_obliquity_epoch="midpoint_julian_day",
    # Davison uses the mean of the two latitudes and the CIRCULAR mean of the
    # two longitudes. Geographic longitude wraps at the antimeridian, so 179E
    # and 179W average to 180, not to 0. This is the astrological convention,
    # not the great-circle midpoint of the two points.
    davison_location_method="mean_latitude_circular_mean_longitude",
    # Applying and separating need a shared timeline, which two natal charts do
    # not have. Set to "natal_speed_convention" to opt into the traditional
    # convention that treats the faster body as moving toward the slower one;
    # that is a convention, not physics, and the chart says so when it is on.
    # For a physically real answer use a Davison chart, which is an actual
    # instant with actual motion.
    cross_aspect_phase_policy="indeterminate_no_shared_timeline",
)

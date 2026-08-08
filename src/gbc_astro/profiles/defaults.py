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


RELATIONSHIP_WESTERN_V1 = RelationshipProfile(
    id="relationship-western-v1",
    version="1.0.0",
    aspect_profile=MODERN_MAJOR_V1,
    synastry_bodies=BODY_IDS,
    synastry_angles=("ascendant", "mc", "descendant", "ic"),
    # Shortest-arc midpoint of each corresponding pair of body longitudes.
    composite_position_method="shortest_arc_midpoint",
    # Composite angles are the shortest-arc midpoints of the two charts' angles.
    # This is the common "midpoint composite" convention and it has a known
    # defect: the resulting Ascendant and Midheaven are not generally consistent
    # with each other the way a real chart's are, because each is averaged
    # independently. The defect is recorded in the chart's warnings rather than
    # hidden.
    composite_angle_method="shortest_arc_midpoint_of_angles",
    # No composite house system in v0.2. Deriving houses would require choosing
    # a reference time and place the composite chart does not have, and the spec
    # forbids inventing methodology. Left None so nothing is emitted.
    composite_house_method=None,
    # Applying and separating need a shared timeline. Two natal charts do not
    # have one, so cross aspects report `indeterminate` rather than a number
    # that looks physical and is not.
    cross_aspect_phase_policy="indeterminate_no_shared_timeline",
)

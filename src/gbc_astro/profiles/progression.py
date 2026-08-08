"""Versioned progression and direction profiles.

Secondary progressions run the chart forward one day for each year of life. That
sentence hides two decisions that change every result, so both are declared here
rather than assumed:

**How long is a year.** The tropical year of 365.2422 days is the usual choice;
the Julian year of 365.25 is also used. The difference is small and worth being
precise about rather than dramatic: over a hundred years of life the two
progressed instants differ by about three minutes, which is roughly eight
arcseconds of progressed Sun. Accumulating a full day of divergence would take
some 47,000 years of life. The value is declared for reproducibility, not
because it changes a reading.

**How do the angles progress.** This is genuinely contested. Solar arc, Naibod,
daily motion of the Midheaven and the quotidian methods all give different
Midheavens, and no calculation arbitrates between them. Only solar arc is
implemented; the profile names it so a chart can never be mistaken for one built
another way.
"""

from __future__ import annotations

from dataclasses import dataclass

# Mean tropical year, the interval between successive vernal equinoxes.
TROPICAL_YEAR_DAYS = 365.2422

# The Julian year, exactly 365.25 days by definition.
JULIAN_YEAR_DAYS = 365.25


@dataclass(frozen=True)
class ProgressionProfile:
    id: str
    version: str
    year_length_days: float
    year_length_name: str
    angle_method: str
    rationale: str

    def to_dict(self) -> dict[str, float | str]:
        return {
            "id": self.id,
            "version": self.version,
            "yearLengthDays": self.year_length_days,
            "yearLength": self.year_length_name,
            "angleMethod": self.angle_method,
            "rationale": self.rationale,
        }


SECONDARY_PROGRESSION_V1 = ProgressionProfile(
    id="secondary-progression-v1",
    version="1.0.0",
    year_length_days=TROPICAL_YEAR_DAYS,
    year_length_name="tropical",
    # The progressed chart is cast for the progressed instant at the birthplace,
    # so its angles come from the ordinary house calculation for that moment.
    # This is the "progressed Midheaven by daily motion" convention, which falls
    # out of casting the chart rather than being applied on top of it.
    angle_method="cast_at_progressed_instant",
    rationale=(
        "One day of ephemeris time for each tropical year of life. The tropical "
        "year is used because progressions are a symbolic mapping onto the "
        "seasonal year, not onto the calendar; the choice between it and the "
        "Julian year is worth declaring for reproducibility but is not material, "
        "amounting to about eight arcseconds of progressed Sun over a century. "
        "The progressed chart is cast for the progressed instant at the "
        "birthplace, so its angles are whatever the sky actually held then, "
        "rather than a separately directed Midheaven."
    ),
)


SOLAR_ARC_V1 = ProgressionProfile(
    id="solar-arc-v1",
    version="1.0.0",
    year_length_days=TROPICAL_YEAR_DAYS,
    year_length_name="tropical",
    angle_method="solar_arc_applied_to_all_points",
    rationale=(
        "Every natal point, including the angles, advances by the arc the "
        "secondary-progressed Sun has travelled. Because one arc is applied to "
        "everything, a solar arc chart is a rotation: the aspects between directed "
        "points are identical to the natal ones, and only contacts to the natal "
        "chart carry information."
    ),
)

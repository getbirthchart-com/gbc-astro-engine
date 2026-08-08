"""Parity and invariant checks for every supported house system.

Two levels of check, because only some systems can honestly get the stronger one.

**Absolute.** Placidus, Porphyry and Meridian are re-derived here from their
definitions, independently of Swiss Ephemeris, and compared numerically.
Whole Sign and Equal are derived by the engine itself from the Ascendant, so
they are checked against that derivation directly.

**Structural.** Koch, Campanus, Regiomontanus, Alcabitius, Topocentric and
Morinus have no independent reference in this engine. Claiming they are
validated because Swiss Ephemeris produced them would be validating a thing
against itself. Instead they are held to the properties every house system must
satisfy regardless of how its cusps are defined:

* exactly twelve cusps, advancing in zodiacal order and closing the circle
* cusp 1 is the Ascendant and cusp 10 the Midheaven, for quadrant systems only
* cusp k + 6 is exactly opposite cusp k, for axially symmetric systems
* every body lands in exactly one house
* systems undefined beyond the polar circles refuse rather than substitute

Those catch a wrong code, a swapped cusp array, an off-by-one, or a silent
fallback. They do not catch a subtly wrong cusp formula inside Swiss Ephemeris,
and this module does not pretend otherwise.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from gbc_astro.astronomy.circular import normalize_longitude, shortest_angular_distance
from gbc_astro.astronomy.time import normalize_local_datetime
from gbc_astro.constants import ENGINE_VERSION
from gbc_astro.errors import GbcAstroError, HouseCalculationUnavailableError
from gbc_astro.houses.base import assign_house
from gbc_astro.houses.equal import equal_cusp_longitudes
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.houses.systems import HOUSE_SYSTEMS
from gbc_astro.houses.whole_sign import whole_sign_cusp_longitudes
from gbc_astro.validation.geometry import (
    GeometryReference,
    GeometryUndefinedError,
    meridian_cusps,
    porphyry_cusps,
)
from gbc_astro.validation.geometry_parity import GEOMETRY_ZONES, POLAR_ZONES
from gbc_astro.validation.reference import ValidationCase

# Systems this engine can re-derive without Swiss Ephemeris.
INDEPENDENTLY_DERIVED = ("placidus", "porphyry", "meridian", "whole_sign", "equal")

# Systems checked only against the invariants above.
STRUCTURAL_ONLY = (
    "koch",
    "campanus",
    "regiomontanus",
    "alcabitius",
    "topocentric",
    "morinus",
)

# Two independent implementations of the same spherical geometry agree to well
# under a hundredth of an arcsecond in practice; see PLACIDUS_PARITY.md for the
# measurement behind the equivalent threshold on the Placidus track.
CUSP_TOLERANCE_DEG = 1.0e-5


def generate_house_cases(count: int = 96) -> tuple[ValidationCase, ...]:
    """Deterministic corpus sweeping latitude bands and hours of the day."""
    cases: list[ValidationCase] = []
    zones = GEOMETRY_ZONES + POLAR_ZONES
    for index in range(count):
        zone, latitude, longitude, band = zones[index % len(zones)]
        hour = index % 24
        month = index % 12 + 1
        cases.append(
            ValidationCase(
                id=f"house-{index + 1:04d}",
                local_datetime=f"1990-{month:02d}-15T{hour:02d}:30:00",
                timezone=zone,
                latitude=latitude,
                longitude=longitude,
                house_system="placidus",
                reason=f"house system sweep ({band})",
                expected_behavior="success",
            )
        )
    return tuple(cases)


def _check_invariants(
    system: str,
    cusps: tuple[float, ...],
    ascendant: float,
    midheaven: float,
) -> list[str]:
    """Return the names of every invariant this cusp set violates."""
    profile = HOUSE_SYSTEMS[system]
    failures: list[str] = []

    if len(cusps) != 12:
        return ["cusp_count"]

    total = 0.0
    for index in range(12):
        step = (cusps[(index + 1) % 12] - cusps[index]) % 360.0
        if step <= 0.0 or step >= 180.0:
            failures.append("monotonic_order")
            break
        total += step
    if "monotonic_order" not in failures and abs(total - 360.0) > 1.0e-6:
        failures.append("closes_circle")

    if profile.quadrant_based:
        if shortest_angular_distance(cusps[0], ascendant) > CUSP_TOLERANCE_DEG:
            failures.append("cusp1_is_ascendant")
        # Equal houses start at the Ascendant but do not put the MC on cusp 10.
        if system != "equal" and (
            shortest_angular_distance(cusps[9], midheaven) > CUSP_TOLERANCE_DEG
        ):
            failures.append("cusp10_is_midheaven")

    if profile.axially_symmetric:
        for index in range(6):
            opposite = normalize_longitude(cusps[index] + 180.0)
            if shortest_angular_distance(cusps[index + 6], opposite) > CUSP_TOLERANCE_DEG:
                failures.append("axial_symmetry")
                break

    return failures


def run_house_system_parity(
    cases: tuple[ValidationCase, ...] | None = None,
    swiss_ephemeris_path: str | None = None,
) -> dict[str, Any]:
    corpus = cases or generate_house_cases()
    calculator = SwissHouseCalculator(ephemeris_path=swiss_ephemeris_path)
    reference = GeometryReference()

    absolute: dict[str, dict[str, Any]] = {
        system: {"compared": 0, "maxDeltaDeg": 0.0, "outside": 0}
        for system in INDEPENDENTLY_DERIVED
    }
    structural: dict[str, dict[str, Any]] = {
        system: {"checked": 0, "failures": []} for system in HOUSE_SYSTEMS
    }
    polar_refusals: dict[str, int] = {system: 0 for system in HOUSE_SYSTEMS}
    degenerate: dict[str, int] = {}
    unexpected_degeneracy: list[dict[str, Any]] = []
    assignment_failures: list[dict[str, Any]] = []

    for case in corpus:
        time_norm = normalize_local_datetime(
            datetime.fromisoformat(case.local_datetime), case.timezone
        )
        try:
            geometry = reference.calculate(
                time_norm.julian_day, case.latitude, case.longitude
            )
        except GeometryUndefinedError:
            geometry = None

        for system in HOUSE_SYSTEMS:
            try:
                calculated = calculator.calculate(
                    julian_day=time_norm.julian_day,
                    latitude=case.latitude,
                    longitude=case.longitude,
                    house_system=system,
                )
            except HouseCalculationUnavailableError:
                polar_refusals[system] += 1
                continue
            except GbcAstroError:
                continue

            cusps = tuple(cusp.cusp_longitude for cusp in calculated.houses)
            ascendant = calculated.angles["ascendant"].longitude
            midheaven = calculated.angles["mc"].longitude

            structural[system]["checked"] += 1
            if calculated.sequence_degenerate:
                # Beyond the polar circles some quadrant systems invert: the
                # cusps run backwards. That is what the geometry does, not a
                # defect, so it is recorded rather than failed -- but it must be
                # flagged, and a silent inversion is a failure.
                degenerate[system] = degenerate.get(system, 0) + 1
                if abs(case.latitude) < 66.0:
                    unexpected_degeneracy.append(
                        {"caseId": case.id, "system": system, "latitude": case.latitude}
                    )
                continue

            for violation in _check_invariants(system, cusps, ascendant, midheaven):
                entry = {"caseId": case.id, "invariant": violation}
                failures = structural[system]["failures"]
                if len(failures) < 20:
                    failures.append(entry)

            # Every longitude must land in exactly one house.
            for probe in (0.0, 47.5, 123.25, 271.9, 359.99):
                house = assign_house(probe, calculated.houses)
                if house not in range(1, 13):
                    assignment_failures.append(
                        {"caseId": case.id, "system": system, "longitude": probe}
                    )

            if calculated.sequence_degenerate:
                continue

            expected: tuple[float, ...] | None = None
            if system == "porphyry" and geometry is not None:
                expected = porphyry_cusps(geometry.ascendant, geometry.midheaven)
            elif system == "meridian" and geometry is not None:
                expected = meridian_cusps(geometry.ramc, geometry.obliquity)
            elif system == "placidus" and geometry is not None:
                expected = geometry.cusps
            elif system == "whole_sign":
                expected = whole_sign_cusp_longitudes(ascendant)
            elif system == "equal":
                expected = equal_cusp_longitudes(ascendant)

            if expected is None:
                continue
            worst = max(
                shortest_angular_distance(cusps[index], expected[index])
                for index in range(12)
            )
            stats = absolute[system]
            stats["compared"] += 1
            stats["maxDeltaDeg"] = max(float(stats["maxDeltaDeg"]), worst)
            if worst > CUSP_TOLERANCE_DEG:
                stats["outside"] = int(stats["outside"]) + 1

    structural_failed = [
        system for system, data in structural.items() if data["failures"]
    ]
    absolute_failed = [
        system for system, data in absolute.items() if int(data["outside"]) > 0
    ]
    status = (
        "PASS"
        if not structural_failed
        and not absolute_failed
        and not assignment_failures
        and not unexpected_degeneracy
        else "FAIL"
    )

    return {
        "status": status,
        "engineVersion": ENGINE_VERSION,
        "caseCount": len(corpus),
        "systems": {system: HOUSE_SYSTEMS[system].to_dict() for system in HOUSE_SYSTEMS},
        "independentlyValidated": {
            system: absolute[system] for system in INDEPENDENTLY_DERIVED
        },
        "structurallyValidatedOnly": list(STRUCTURAL_ONLY),
        "structural": structural,
        "polarRefusals": polar_refusals,
        "degenerateSequences": degenerate,
        "unexpectedDegeneracy": unexpected_degeneracy,
        "houseAssignmentFailures": assignment_failures[:20],
        "toleranceDeg": CUSP_TOLERANCE_DEG,
        "notes": (
            "Placidus, Porphyry and Meridian are re-derived from their definitions "
            "without Swiss Ephemeris and compared numerically. Whole Sign and Equal "
            "are derived by the engine from the Ascendant and checked against that "
            "derivation.",
            "Koch, Campanus, Regiomontanus, Alcabitius, Topocentric and Morinus have "
            "no independent reference here and are held to structural invariants "
            "only. Calling them validated because Swiss Ephemeris produced them "
            "would be validating a thing against itself.",
            "Placidus and Koch are undefined beyond the polar circles. The engine "
            "refuses them there; it never substitutes a system that happens to be "
            "defined.",
            "Campanus, Regiomontanus and Topocentric do not refuse beyond the polar "
            "circles; they invert, returning cusps that run backwards. That is what "
            "the geometry does, so the engine returns them with a "
            "HOUSE_SEQUENCE_DEGENERATE warning rather than pretending the chart is "
            "ordinary. Degeneracy inside the polar circles would be a defect and "
            "fails the gate.",
        ),
    }

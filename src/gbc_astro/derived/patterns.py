"""Chart pattern detection.

Each pattern is a named geometric claim, tested by checking that every leg of
the figure holds within the profile's orb. Nothing here is heuristic: a grand
trine is three bodies mutually trine, or it is not reported.

Detected figures carry the widest leg orb they contain, because that number is
what tells a reader whether the figure is tight enough to matter. A grand cross
with a five-degree leg and one with a half-degree leg are not the same object.

Containment is resolved rather than ignored. Every grand cross contains two
T-squares and every kite contains a grand trine; the contained figure is
suppressed so the same configuration is not announced three times.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from gbc_astro.astronomy.circular import shortest_angular_distance
from gbc_astro.constants import SIGN_IDS
from gbc_astro.models.position import BodyPosition
from gbc_astro.profiles.pattern import PATTERN_ANGLES, PatternProfile


@dataclass(frozen=True)
class ChartPattern:
    """One detected configuration."""

    pattern_type: str
    bodies: tuple[str, ...]
    max_leg_orb: float
    detail: dict[str, object]

    @property
    def id(self) -> str:
        """Deterministic, derived only from what the figure is."""
        return f"pattern.{self.pattern_type}." + ".".join(self.bodies)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "type": self.pattern_type,
            "bodies": list(self.bodies),
            "maxLegOrb": self.max_leg_orb,
            "detail": self.detail,
        }


def _leg(
    first: BodyPosition,
    second: BodyPosition,
    aspect: str,
    profile: PatternProfile,
) -> float | None:
    """Orb of the named aspect between two bodies, or None if it does not hold."""
    separation = shortest_angular_distance(first.longitude, second.longitude)
    orb = abs(separation - PATTERN_ANGLES[aspect])
    return orb if orb <= profile.leg_orbs[aspect] else None


def _participants(
    bodies: dict[str, BodyPosition], profile: PatternProfile
) -> list[tuple[str, BodyPosition]]:
    return [
        (body_id, bodies[body_id])
        for body_id in profile.participating_bodies
        if body_id in bodies
    ]


def find_stelliums(
    bodies: dict[str, BodyPosition], profile: PatternProfile
) -> list[ChartPattern]:
    """Three or more participating bodies sharing a sign."""
    by_sign: dict[str, list[str]] = {}
    for body_id, body in _participants(bodies, profile):
        by_sign.setdefault(body.sign, []).append(body_id)

    patterns: list[ChartPattern] = []
    for sign in SIGN_IDS:
        members = sorted(by_sign.get(sign, []))
        if len(members) < profile.stellium_minimum_bodies:
            continue
        longitudes = [bodies[body_id].longitude for body_id in members]
        span = max(longitudes) - min(longitudes)
        patterns.append(
            ChartPattern(
                pattern_type="stellium",
                bodies=tuple(members),
                # A stellium has no legs; the span is the comparable measure.
                max_leg_orb=span,
                detail={"sign": sign, "spanDegrees": span, "bodyCount": len(members)},
            )
        )
    return patterns


def find_grand_trines(
    bodies: dict[str, BodyPosition], profile: PatternProfile
) -> list[ChartPattern]:
    """Three bodies mutually trine."""
    patterns: list[ChartPattern] = []
    for triple in combinations(_participants(bodies, profile), 3):
        orbs = [
            _leg(first[1], second[1], "trine", profile)
            for first, second in combinations(triple, 2)
        ]
        if any(orb is None for orb in orbs):
            continue
        patterns.append(
            ChartPattern(
                pattern_type="grand_trine",
                bodies=tuple(sorted(body_id for body_id, _ in triple)),
                max_leg_orb=max(orb for orb in orbs if orb is not None),
                detail={"legs": "three mutual trines"},
            )
        )
    return patterns


def find_t_squares(
    bodies: dict[str, BodyPosition], profile: PatternProfile
) -> list[ChartPattern]:
    """Two bodies in opposition, both square a third."""
    patterns: list[ChartPattern] = []
    participants = _participants(bodies, profile)
    for first, second in combinations(participants, 2):
        opposition = _leg(first[1], second[1], "opposition", profile)
        if opposition is None:
            continue
        for apex_id, apex in participants:
            if apex_id in (first[0], second[0]):
                continue
            legs = [
                opposition,
                _leg(first[1], apex, "square", profile),
                _leg(second[1], apex, "square", profile),
            ]
            if any(orb is None for orb in legs):
                continue
            patterns.append(
                ChartPattern(
                    pattern_type="t_square",
                    bodies=tuple(sorted((first[0], second[0], apex_id))),
                    max_leg_orb=max(orb for orb in legs if orb is not None),
                    detail={"apex": apex_id, "opposition": sorted((first[0], second[0]))},
                )
            )
    return patterns


def find_grand_crosses(
    bodies: dict[str, BodyPosition], profile: PatternProfile
) -> list[ChartPattern]:
    """Two oppositions square to each other."""
    patterns: list[ChartPattern] = []
    participants = _participants(bodies, profile)
    for quad in combinations(participants, 4):
        for pairing in (((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2))):
            (a, b), (c, d) = pairing
            legs = [
                _leg(quad[a][1], quad[b][1], "opposition", profile),
                _leg(quad[c][1], quad[d][1], "opposition", profile),
                _leg(quad[a][1], quad[c][1], "square", profile),
                _leg(quad[a][1], quad[d][1], "square", profile),
                _leg(quad[b][1], quad[c][1], "square", profile),
                _leg(quad[b][1], quad[d][1], "square", profile),
            ]
            if any(orb is None for orb in legs):
                continue
            patterns.append(
                ChartPattern(
                    pattern_type="grand_cross",
                    bodies=tuple(sorted(body_id for body_id, _ in quad)),
                    max_leg_orb=max(orb for orb in legs if orb is not None),
                    detail={"oppositions": 2, "squares": 4},
                )
            )
            break
    return patterns


def find_yods(
    bodies: dict[str, BodyPosition], profile: PatternProfile
) -> list[ChartPattern]:
    """Two bodies sextile, both quincunx a third."""
    patterns: list[ChartPattern] = []
    participants = _participants(bodies, profile)
    for first, second in combinations(participants, 2):
        sextile = _leg(first[1], second[1], "sextile", profile)
        if sextile is None:
            continue
        for apex_id, apex in participants:
            if apex_id in (first[0], second[0]):
                continue
            legs = [
                sextile,
                _leg(first[1], apex, "quincunx", profile),
                _leg(second[1], apex, "quincunx", profile),
            ]
            if any(orb is None for orb in legs):
                continue
            patterns.append(
                ChartPattern(
                    pattern_type="yod",
                    bodies=tuple(sorted((first[0], second[0], apex_id))),
                    max_leg_orb=max(orb for orb in legs if orb is not None),
                    detail={"apex": apex_id, "base": sorted((first[0], second[0]))},
                )
            )
    return patterns


def find_kites(
    bodies: dict[str, BodyPosition],
    profile: PatternProfile,
    grand_trines: list[ChartPattern],
) -> list[ChartPattern]:
    """A grand trine with a fourth body opposite one corner and sextile the others."""
    patterns: list[ChartPattern] = []
    participants = dict(_participants(bodies, profile))
    for trine in grand_trines:
        for tail_id, tail in participants.items():
            if tail_id in trine.bodies:
                continue
            for apex in trine.bodies:
                others = [body for body in trine.bodies if body != apex]
                legs = [
                    trine.max_leg_orb,
                    _leg(participants[apex], tail, "opposition", profile),
                    _leg(participants[others[0]], tail, "sextile", profile),
                    _leg(participants[others[1]], tail, "sextile", profile),
                ]
                if any(orb is None for orb in legs):
                    continue
                patterns.append(
                    ChartPattern(
                        pattern_type="kite",
                        bodies=tuple(sorted((*trine.bodies, tail_id))),
                        max_leg_orb=max(orb for orb in legs if orb is not None),
                        detail={
                            "grandTrine": list(trine.bodies),
                            "tail": tail_id,
                            "opposedCorner": apex,
                        },
                    )
                )
                break
    return patterns


def _suppress_contained(patterns: list[ChartPattern]) -> list[ChartPattern]:
    """Drop figures wholly contained in a larger detected one.

    Every grand cross contains two T-squares and every kite contains a grand
    trine. Reporting all three says the same thing three times.
    """
    containers = {
        "grand_cross": "t_square",
        "kite": "grand_trine",
    }
    kept: list[ChartPattern] = []
    for pattern in patterns:
        contained = False
        for container_type, contained_type in containers.items():
            if pattern.pattern_type != contained_type:
                continue
            if any(
                other.pattern_type == container_type
                and set(pattern.bodies).issubset(set(other.bodies))
                for other in patterns
            ):
                contained = True
                break
        if not contained:
            kept.append(pattern)
    return kept


def find_patterns(
    bodies: dict[str, BodyPosition], profile: PatternProfile
) -> tuple[ChartPattern, ...]:
    """Every configuration the profile defines, in a stable order."""
    grand_trines = find_grand_trines(bodies, profile)
    found = [
        *find_stelliums(bodies, profile),
        *grand_trines,
        *find_t_squares(bodies, profile),
        *find_grand_crosses(bodies, profile),
        *find_yods(bodies, profile),
        *find_kites(bodies, profile, grand_trines),
    ]
    if profile.suppress_contained_patterns:
        found = _suppress_contained(found)
    # Sorted by name so the order never depends on iteration or chance.
    return tuple(sorted(found, key=lambda pattern: (pattern.pattern_type, pattern.id)))

"""Lunar-node selection for a calculation profile.

`node_type` is the single source of truth for which lunar node the chart treats
as the North Node. Natal aspects, the South Node, draconic calculations and
metadata must all resolve through this module rather than hard-coding
`true_node`.
"""

from __future__ import annotations

from dataclasses import replace

from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.models.chart import NatalChart
from gbc_astro.profiles.model import CalculationProfile, RelationshipProfile

NODE_BODY_BY_TYPE: dict[str, str] = {
    "true": "true_node",
    "mean": "mean_node",
}

LUNAR_NODE_BODIES: frozenset[str] = frozenset(NODE_BODY_BY_TYPE.values())


def normalize_node_type(node_type: str) -> str:
    """Return the canonical node convention: `true` or `mean`."""

    if not isinstance(node_type, str) or not node_type.strip():
        raise InvalidCalculationProfileError(
            "Unsupported node type.",
            {
                "nodeType": node_type,
                "supported": sorted(NODE_BODY_BY_TYPE),
                "field": "node_type",
            },
        )
    normalized = node_type.strip().lower()
    if normalized not in NODE_BODY_BY_TYPE:
        raise InvalidCalculationProfileError(
            "Unsupported node type.",
            {
                "nodeType": normalized,
                "supported": sorted(NODE_BODY_BY_TYPE),
                "field": "node_type",
            },
        )
    return normalized


def selected_node_body_id(node_type: str) -> str:
    """Return the natal body id that `node_type` selects as the North Node."""

    return NODE_BODY_BY_TYPE[normalize_node_type(node_type)]


def aspect_bodies_for_node_type(
    aspect_bodies: tuple[str, ...],
    node_type: str,
) -> tuple[str, ...]:
    """Copy `aspect_bodies`, substituting the lunar node that `node_type` selects.

    This is for constructing a valid profile. Engine validation does not apply
    this substitution to an invalid profile: a mismatch is an error.
    """

    selected = selected_node_body_id(node_type)
    return tuple(
        selected if body in LUNAR_NODE_BODIES else body for body in aspect_bodies
    )


def profile_with_node_type(
    profile: CalculationProfile,
    node_type: str,
    profile_id: str | None = None,
) -> CalculationProfile:
    """Return a copy of `profile` whose node type and aspect bodies agree.

    Callers that switch node convention must use this helper (or the settings
    resolver that calls it). Raw `replace(..., node_type=...)` is not a
    supported way to change convention: aspect bodies would be left pointing
    at the other node.
    """

    normalized = normalize_node_type(node_type)
    bodies = aspect_bodies_for_node_type(profile.aspect_bodies, normalized)
    if (
        profile_id is None
        and normalized == profile.node_type
        and bodies == profile.aspect_bodies
    ):
        return profile
    return replace(
        profile,
        id=profile.id if profile_id is None else profile_id,
        node_type=normalized,
        aspect_bodies=bodies,
    )


def relationship_profile_with_node_type(
    profile: RelationshipProfile,
    node_type: str,
) -> RelationshipProfile:
    """Return a copy whose synastry bodies agree with `node_type`.

    Callers that switch relationship node convention must use this helper.
    Raw `replace(..., node_type=...)` is not a supported switching path:
    synastry_bodies would be left pointing at the other node.
    """

    normalized = normalize_node_type(node_type)
    bodies = aspect_bodies_for_node_type(profile.synastry_bodies, normalized)
    if normalized == profile.node_type and bodies == profile.synastry_bodies:
        return profile
    return replace(
        profile,
        node_type=normalized,
        synastry_bodies=bodies,
    )


def resolve_relationship_node_type(
    chart_a: NatalChart,
    chart_b: NatalChart,
    node_type: str | None,
    *,
    default: str = "true",
) -> str:
    """Resolve the single node convention for one relationship calculation.

    An explicit value always wins. Omitted uses `default` (the relationship
    profile's node_type, True on the western-modern default) when both natal
    charts share a convention. Differing natal conventions without an explicit
    relationship setting are refused rather than guessed.
    """

    if node_type is not None:
        return normalize_node_type(node_type)
    natal_a = chart_a.meta.node_type
    natal_b = chart_b.meta.node_type
    if natal_a != natal_b:
        raise InvalidCalculationProfileError(
            "Synastry requires an explicit relationship node_type when the two "
            "natal charts use different node conventions. The engine will not "
            "choose True or Mean silently.",
            {
                "chartANodeType": natal_a,
                "chartBNodeType": natal_b,
                "field": "node_type",
                "supported": sorted(NODE_BODY_BY_TYPE),
            },
        )
    return normalize_node_type(default)


def validate_node_settings(node_type: str, aspect_bodies: tuple[str, ...]) -> None:
    """Refuse node settings that would mix True and Mean Node conventions."""

    selected = selected_node_body_id(node_type)
    nodes = LUNAR_NODE_BODIES & set(aspect_bodies)
    if len(nodes) > 1:
        raise InvalidCalculationProfileError(
            "A profile may make at most one lunar node eligible to aspect. "
            "The true and mean nodes are the same point computed two ways, "
            "so admitting both counts every node contact twice and makes "
            "the two of them permanently conjunct.",
            {"aspectBodies": list(aspect_bodies), "nodes": sorted(nodes)},
        )
    if nodes and nodes != {selected}:
        raise InvalidCalculationProfileError(
            "Aspect bodies include a lunar node that does not match "
            "node_type. The selected node type is the source of truth; a "
            "profile cannot request one convention while aspecting the other.",
            {
                "nodeType": node_type,
                "selectedNode": selected,
                "aspectNodes": sorted(nodes),
            },
        )

"""Result models for the rulership-derived block of a natal chart.

These live here rather than beside the computation for the same reason
`MoonPhase` does: `models` is imported by `derived`, so a result type defined in
`derived` and referenced from `models.chart` closes an import cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RulerPlacement:
    """A ruling planet and where it actually is.

    The ruler on its own is half an answer: "your chart ruler is Mars" matters
    much less than which house and sign that Mars occupies.
    """

    body_id: str
    sign: str | None
    house: int | None
    longitude: float | None
    retrograde: bool | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "body": self.body_id,
            "sign": self.sign,
            "house": self.house,
            "longitude": self.longitude,
            "retrograde": self.retrograde,
        }


@dataclass(frozen=True)
class HouseRuler:
    house: int
    cusp_sign: str
    ruler: RulerPlacement
    co_rulers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "house": self.house,
            "cuspSign": self.cusp_sign,
            "ruler": self.ruler.to_dict(),
            "coRulers": list(self.co_rulers),
        }


@dataclass(frozen=True)
class Dignity:
    body_id: str
    sign: str
    state: str
    # True only when the body sits in the degree tradition names for its
    # exaltation, within a degree. Reported, never scored here.
    exact_exaltation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "body": self.body_id,
            "sign": self.sign,
            "state": self.state,
            "exactExaltation": self.exact_exaltation,
        }


@dataclass(frozen=True)
class DispositorChain:
    body_id: str
    # The walk from this body to where it ends, excluding the body itself.
    chain: tuple[str, ...]
    final_dispositor: str | None
    # The planets in the loop this chain runs into, if it runs into one.
    loop: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "body": self.body_id,
            "chain": list(self.chain),
            "finalDispositor": self.final_dispositor,
            "loop": list(self.loop),
        }


@dataclass(frozen=True)
class DominantPlanet:
    body_id: str
    score: float
    rank: int
    components: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "body": self.body_id,
            "score": self.score,
            "rank": self.rank,
            "components": dict(self.components),
        }

"""Aspect model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Aspect:
    body_a: str
    body_b: str
    aspect_type: str
    exact_angle: float
    actual_angle: float
    orb: float
    phase: str

    def to_dict(self) -> dict[str, float | str]:
        return {
            "a": self.body_a,
            "b": self.body_b,
            "type": self.aspect_type,
            "exactAngle": self.exact_angle,
            "actualAngle": self.actual_angle,
            "orb": self.orb,
            "phase": self.phase,
        }


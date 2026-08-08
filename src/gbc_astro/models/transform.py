"""Canonical model for a transformed chart."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from gbc_astro.models.aspect import Aspect
from gbc_astro.models.chart import ChartSubject, WarningMessage
from gbc_astro.models.position import AnglePosition, BodyPosition


@dataclass(frozen=True)
class TransformedChart:
    """A natal chart mapped through a documented longitude transform.

    The source chart is kept so the two can always be read side by side, which
    is how draconic and harmonic charts are used in practice.
    """

    schema_version: str
    transform: str
    transform_version: str
    meta: dict[str, Any]
    subject: ChartSubject
    bodies: dict[str, BodyPosition]
    angles: dict[str, AnglePosition] = field(default_factory=dict)
    aspects: tuple[Aspect, ...] = ()
    warnings: tuple[WarningMessage, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "transform": self.transform,
            "transformVersion": self.transform_version,
            "meta": self.meta,
            "subject": self.subject.to_dict(),
            "bodies": {name: body.to_dict() for name, body in self.bodies.items()},
            "angles": {name: angle.to_dict() for name, angle in self.angles.items()},
            "aspects": [aspect.to_dict() for aspect in self.aspects],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

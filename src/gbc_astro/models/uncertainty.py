"""Unknown-birth-time uncertainty assessment models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BodyUncertainty:
    body_id: str
    anchor_longitude: float
    start_longitude: float
    end_longitude: float
    longitude_range: float
    possible_signs: tuple[str, ...]
    sign_changed: bool
    motion_start: str
    motion_end: str
    motion_states: tuple[str, ...]
    station_in_interval: bool
    sign_status: str
    motion_status: str
    longitude_status: str
    stable_properties: tuple[str, ...]
    uncertain_properties: tuple[str, ...]
    classification: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchorLongitude": self.anchor_longitude,
            "startLongitude": self.start_longitude,
            "endLongitude": self.end_longitude,
            "longitudeRange": self.longitude_range,
            "longitudeStatus": self.longitude_status,
            "possibleSigns": list(self.possible_signs),
            "signChanged": self.sign_changed,
            "signStatus": self.sign_status,
            "motionStatus": self.motion_status,
            "motion": {
                "start": self.motion_start,
                "end": self.motion_end,
                "states": list(self.motion_states),
                "stationInInterval": self.station_in_interval,
            },
            "stableProperties": list(self.stable_properties),
            "uncertainProperties": list(self.uncertain_properties),
            "classification": self.classification,
            "reasons": list(self.reasons),
        }

    def identity_dict(self) -> dict[str, Any]:
        return {
            "anchorLongitude": self.anchor_longitude,
            "startLongitude": self.start_longitude,
            "endLongitude": self.end_longitude,
            "longitudeRange": self.longitude_range,
            "longitudeStatus": self.longitude_status,
            "possibleSigns": list(self.possible_signs),
            "signChanged": self.sign_changed,
            "signStatus": self.sign_status,
            "motionStatus": self.motion_status,
            "motionStart": self.motion_start,
            "motionEnd": self.motion_end,
            "motionStates": list(self.motion_states),
            "stationInInterval": self.station_in_interval,
            "stableProperties": list(self.stable_properties),
            "uncertainProperties": list(self.uncertain_properties),
            "classification": self.classification,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class AspectUncertainty:
    body_a: str
    body_b: str
    aspect_type: str
    exact_angle: float
    presence: str
    min_orb: float
    max_orb: float
    exact_hit: bool
    phase_stable: bool
    phases: tuple[str, ...]
    enter_at: str | None
    exact_at: str | None
    leave_at: str | None
    classification: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "a": self.body_a,
            "b": self.body_b,
            "type": self.aspect_type,
            "exactAngle": self.exact_angle,
            "presence": self.presence,
            "minOrb": self.min_orb,
            "maxOrb": self.max_orb,
            "exactHit": self.exact_hit,
            "phaseStable": self.phase_stable,
            "phases": list(self.phases),
            "classification": self.classification,
            "reasons": list(self.reasons),
        }
        if self.enter_at is not None:
            payload["enterAt"] = self.enter_at
        if self.exact_at is not None:
            payload["exactAt"] = self.exact_at
        if self.leave_at is not None:
            payload["leaveAt"] = self.leave_at
        return payload

    def identity_dict(self) -> dict[str, Any]:
        return {
            "a": self.body_a,
            "b": self.body_b,
            "type": self.aspect_type,
            "exactAngle": self.exact_angle,
            "presence": self.presence,
            "minOrb": self.min_orb,
            "maxOrb": self.max_orb,
            "exactHit": self.exact_hit,
            "phaseStable": self.phase_stable,
            "phases": list(self.phases),
            "enterAt": self.enter_at,
            "exactAt": self.exact_at,
            "leaveAt": self.leave_at,
            "classification": self.classification,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class UnknownTimeAssessment:
    version: str
    algorithm_version: str
    anchor: str
    interval: dict[str, str]
    bodies: dict[str, BodyUncertainty]
    aspects: dict[str, AspectUncertainty]
    unavailable: tuple[str, ...]
    ephemeris_evaluations: int
    coarse_samples: int
    max_evaluations: int
    evaluation_budget_exhausted: bool = False
    assessment_complete: bool = True
    zodiac: str = "tropical"
    ayanamsa: str | None = None
    ayanamsa_version: str | None = None
    ayanamsa_degrees: float | None = None

    def _frame_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"zodiac": self.zodiac}
        if self.ayanamsa is not None:
            payload["ayanamsa"] = self.ayanamsa
            payload["ayanamsaVersion"] = self.ayanamsa_version
            payload["ayanamsaDegrees"] = self.ayanamsa_degrees
        return payload

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "algorithmVersion": self.algorithm_version,
            "anchor": self.anchor,
            "assessmentComplete": self.assessment_complete,
            "interval": dict(self.interval),
            "bodies": {body_id: body.to_dict() for body_id, body in self.bodies.items()},
            "aspects": {key: aspect.to_dict() for key, aspect in self.aspects.items()},
            "unavailable": list(self.unavailable),
            "provenance": {
                "ephemerisEvaluations": self.ephemeris_evaluations,
                "coarseSamples": self.coarse_samples,
                "maxEvaluations": self.max_evaluations,
                "evaluationBudgetExhausted": self.evaluation_budget_exhausted,
                "assessmentComplete": self.assessment_complete,
                "frame": self._frame_dict(),
            },
        }

    def identity_dict(self) -> dict[str, Any]:
        """Canonical identity: classification and astronomy, not eval counts."""

        return {
            "version": self.version,
            "algorithmVersion": self.algorithm_version,
            "anchor": self.anchor,
            "assessmentComplete": self.assessment_complete,
            "interval": dict(self.interval),
            "frame": self._frame_dict(),
            "bodies": {
                body_id: body.identity_dict()
                for body_id, body in sorted(self.bodies.items())
            },
            "aspects": {
                key: aspect.identity_dict()
                for key, aspect in sorted(self.aspects.items())
            },
            "unavailable": list(self.unavailable),
        }

"""Optional asteroid and lunar-apogee bodies.

`01_MASTER_REQUIREMENTS.md` section 4 lists these as provider-dependent and adds
a requirement about how that dependency must behave:

> The provider layer must expose capability metadata rather than making
> unsupported bodies fail unpredictably.

That is the whole design here. The four main-belt asteroids and both lunar
apogees ride along in `seas_18.se1`, which any installation carrying Chiron
already has. Arbitrary numbered asteroids each need their own data file, so
whether `433 Eros` is available depends entirely on what was provisioned.

`available_optional_bodies()` answers that by probing rather than guessing, so a
caller can ask what it can have instead of finding out through an exception.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import import_module
from types import ModuleType

from gbc_astro.errors import ProviderDependencyError, UnsupportedBodyError

# Bodies carried by the standard asteroid file. `mean_lilith` and `true_lilith`
# are the mean and osculating lunar apogee: not asteroids at all, but grouped
# here because they share the same optional-data story.
OPTIONAL_BODIES: dict[str, str] = {
    "ceres": "CERES",
    "pallas": "PALLAS",
    "juno": "JUNO",
    "vesta": "VESTA",
    "mean_lilith": "MEAN_APOG",
    "true_lilith": "OSCU_APOG",
}

# Swiss Ephemeris addresses numbered asteroids at this offset.
NUMBERED_ASTEROID_PREFIX = "asteroid_"

# Probe instant for capability checks: mid-range and unremarkable.
_PROBE = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)


@dataclass(frozen=True)
class BodyCapability:
    body_id: str
    available: bool
    kind: str
    reason: str | None = None

    def to_dict(self) -> dict[str, bool | str | None]:
        return {
            "bodyId": self.body_id,
            "available": self.available,
            "kind": self.kind,
            "reason": self.reason,
        }


def parse_numbered_asteroid(body_id: str) -> int | None:
    """`asteroid_433` -> 433. Anything else -> None."""
    if not body_id.startswith(NUMBERED_ASTEROID_PREFIX):
        return None
    suffix = body_id[len(NUMBERED_ASTEROID_PREFIX) :]
    if not suffix.isdigit():
        return None
    number = int(suffix)
    return number if number > 0 else None


def swisseph_code(body_id: str, swe: ModuleType) -> int:
    """Swiss Ephemeris planet number for an optional body."""
    named = OPTIONAL_BODIES.get(body_id)
    if named is not None:
        code = getattr(swe, named, None)
        if code is None:
            raise UnsupportedBodyError(
                "This Swiss Ephemeris build does not provide the requested body.",
                {"body": body_id, "constant": named},
            )
        return int(code)

    number = parse_numbered_asteroid(body_id)
    if number is None:
        raise UnsupportedBodyError(
            "Unknown optional body.",
            {
                "body": body_id,
                "supported": sorted(OPTIONAL_BODIES),
                "numberedFormat": f"{NUMBERED_ASTEROID_PREFIX}<number>",
            },
        )
    return int(swe.AST_OFFSET) + number


def available_optional_bodies(
    ephemeris_path: str | None = None,
    extra: tuple[str, ...] = (),
) -> tuple[BodyCapability, ...]:
    """Probe which optional bodies this installation can actually calculate.

    Probing rather than guessing: whether a numbered asteroid works depends on a
    data file being present, and the only reliable way to know is to ask.
    """
    swe = _load_swisseph()
    if ephemeris_path:
        swe.set_ephe_path(ephemeris_path)
    julian_day = _julian_day(_PROBE)

    capabilities: list[BodyCapability] = []
    for body_id in (*sorted(OPTIONAL_BODIES), *extra):
        kind = "asteroid" if parse_numbered_asteroid(body_id) else (
            "lunar_apogee" if "lilith" in body_id else "named_asteroid"
        )
        try:
            swe.calc_ut(julian_day, swisseph_code(body_id, swe))
        except UnsupportedBodyError as exc:
            capabilities.append(
                BodyCapability(body_id, False, kind, reason=exc.message)
            )
        except Exception:
            capabilities.append(
                BodyCapability(
                    body_id,
                    False,
                    kind,
                    reason=(
                        "Swiss Ephemeris data for this body is not provisioned. "
                        "Numbered asteroids each need their own se<number>.se1 file."
                    ),
                )
            )
        else:
            capabilities.append(BodyCapability(body_id, True, kind))
    return tuple(capabilities)


def _julian_day(instant: datetime) -> float:
    from gbc_astro.astronomy.provider_time import julian_day_ut

    return julian_day_ut(instant)


def _load_swisseph() -> ModuleType:
    try:
        return import_module("swisseph")
    except ImportError as exc:
        raise ProviderDependencyError(
            "Optional bodies require the 'pyswisseph' dependency.",
            {"install": "python -m pip install gbc-astro"},
        ) from exc

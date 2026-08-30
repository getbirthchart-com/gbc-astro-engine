"""Circular range, sign coverage, and motion labels for sampled longitudes."""

from __future__ import annotations

import math
from collections.abc import Sequence

from gbc_astro.astronomy.circular import directed_circular_delta, normalize_longitude
from gbc_astro.constants import SIGN_IDS
from gbc_astro.uncertainty.constants import STATION_SPEED_EPS


def unwrap_longitudes(longitudes: Sequence[float]) -> tuple[float, ...]:
    """Walk a longitude series along the short arc so 359.8° → 0.2° is 0.4°."""

    if not longitudes:
        return ()
    unwrapped = [normalize_longitude(longitudes[0])]
    for value in longitudes[1:]:
        current = normalize_longitude(value)
        previous_mod = normalize_longitude(unwrapped[-1])
        unwrapped.append(unwrapped[-1] + directed_circular_delta(previous_mod, current))
    return tuple(unwrapped)


def circular_range_deg(unwrapped: Sequence[float]) -> float:
    if not unwrapped:
        return 0.0
    return max(unwrapped) - min(unwrapped)


def signs_covering(unwrapped: Sequence[float]) -> tuple[str, ...]:
    """Every sign the unwrapped span occupies, including unsampled interiors."""

    if not unwrapped:
        return ()
    lo = min(unwrapped)
    hi = max(unwrapped)
    start_idx = int(math.floor(lo / 30.0))
    end_idx = int(math.floor((hi - 1e-12) / 30.0)) if hi > lo else start_idx
    if math.isclose(hi, lo, abs_tol=1e-12):
        end_idx = start_idx
    signs: list[str] = []
    for index in range(start_idx, end_idx + 1):
        sign = SIGN_IDS[index % 12]
        if sign not in signs:
            signs.append(sign)
    return tuple(signs)


def motion_label(speed: float | None) -> str:
    if speed is None:
        return "indeterminate"
    if speed > STATION_SPEED_EPS:
        return "direct"
    if speed < -STATION_SPEED_EPS:
        return "retrograde"
    return "stationary"

Status: PASS

Implemented:
- IANA timezone normalization through `zoneinfo`
- Ambiguous local time detection requiring explicit `fold`
- Nonexistent local time detection
- UTC serialization with trailing `Z`
- Julian Day conversion isolated from providers

Tests:
- Known Asia/Ho_Chi_Minh conversion
- Gregorian Julian Day J2000 reference
- America/New_York spring-forward nonexistent local time
- America/New_York fall-back ambiguous local time with fold resolution

Differential evidence:
- Not applicable yet; provider parity belongs to later phases.

Known limitations:
- Timezone data version is recorded as `system-zoneinfo`; Python stdlib does not expose a precise installed tzdb version across all platforms.

Files changed:
- `src/gbc_astro/astronomy/time.py`
- `tests/unit/test_time.py`


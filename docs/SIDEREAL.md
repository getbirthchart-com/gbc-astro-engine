# Sidereal zodiac

A sidereal chart is a tropical chart rotated backwards by the **ayanamsa** — the
angle between the vernal equinox and a zodiac fixed against the stars. The two
drift apart at the rate of precession, about 50.3 arcseconds a year.

## What changes and what does not

Only labels change. Every relationship between points survives the rotation
exactly, because every longitude shifts by the same amount:

| | Sidereal |
|---|---|
| Longitude, sign, degree in sign | **change** |
| House assignments | unchanged |
| Aspects and orbs | unchanged |
| Latitude, distance, speed, retrograde | unchanged |

This is why it is applied as a single rotation over a finished tropical chart
rather than threaded through the calculation. The validated tropical math runs
untouched.

## Supported ayanamsas

| id | Anchor | J2000 |
|---|---|---:|
| `lahiri` | Indian government standard; the Vedic default | 23.857092° |
| `true_citra` | Spica held at exactly 180° | 23.840018° |
| `fagan_bradley` | Western sidereal standard | 24.740300° |
| `krishnamurti` | Krishnamurti Paddhati | 23.760240° |
| `raman` | B. V. Raman | 22.410791° |

They disagree by up to **2.33°** at J2000 — more than enough to move a planet
into the neighbouring sign. There is no calculation that arbitrates between
them, so a sidereal profile that does not name one is **refused at engine
construction**, not silently defaulted.

## Usage

```python
from dataclasses import replace
from gbc_astro import AstrologyEngine
from gbc_astro.profiles.defaults import VEDIC_SIDEREAL_V1

engine = AstrologyEngine(profile=VEDIC_SIDEREAL_V1)          # lahiri, whole sign
chart = engine.natal("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)

raman = AstrologyEngine(profile=replace(VEDIC_SIDEREAL_V1, id="raman-v1", ayanamsa="raman"))
```

`VEDIC_SIDEREAL_V1` uses Whole Sign houses: the near-universal choice in Vedic
practice, and unlike Placidus it is defined at every latitude.

## Provenance

A sidereal chart's `meta` carries three extra fields, absent from tropical
charts:

```json
{
  "zodiac": "sidereal",
  "ayanamsa": "lahiri",
  "ayanamsaVersion": "1.0.0",
  "ayanamsaDegrees": 23.75707697798441
}
```

`ayanamsaDegrees` is the value actually used at that instant, so a stored chart
can be reproduced or audited without recomputing anything.

## Validation

Most ayanamsas are defined by a polynomial with no observable anchor. They are
conventions, and a convention cannot be checked against nature.

One is different. **True Chitrapaksha is defined** as the offset placing Spica
at exactly 180° sidereal. That is an observable, so it is validated against
Spica's apparent ecliptic longitude computed from the Hipparcos catalogue
position through Skyfield and a JPL kernel — a path sharing no code or data with
Swiss Ephemeris.

```bash
gbc validate ayanamsa-parity
```

| Check | Result |
|---|---|
| True Chitrapaksha vs Spica, 1900–2026 | max **17.4 arcsec** (tolerance 60) |
| Precession drift, all five profiles | 50.23–50.28 arcsec/yr vs IAU 50.2877 |

The remaining ayanamsas are checked **structurally**: each must advance at the
rate of general precession, because that is what an ayanamsa is. A profile
drifting at the wrong rate would be wrong no matter which school defined it.

Report: `evidence/v1.0-sidereal/AYANAMSA_PARITY.md`.

## Limitations

- Sidereal affects the zodiac only. Nakshatras, dashas, divisional charts and
  the rest of Vedic technique are not implemented.
- Ayanamsa values come from Swiss Ephemeris. Only true Chitrapaksha has an
  independent reference; the others are validated for drift rate, not value,
  because no observable defines them.
- The 17 arcsec residual on true Chitrapaksha comes from the two sides using
  different star positions and aberration handling, not from either being wrong.

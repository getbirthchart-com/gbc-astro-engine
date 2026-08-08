# JPL Data

JPL data is required for independent astronomy validation. It is not required
for normal natal-chart calculation.

## Required Kernel

For v0.1 validation the configured reference is:

- reference id: `jpl-de440`
- kernel: `de440s.bsp`
- data version reported by the provider: `DE440S`
- validation date range: 1900-01-01 through 2026-12-31
- kernel supported range reported by health check: 1849-12-25 through 2150-01-21

Do not commit large binary kernels to this repository. Provision them through a
deployment artifact store, mounted volume, or CI cache approved for ephemeris
data.

## Configuration

Use one of:

```bash
export GBC_JPL_EPHEMERIS_PATH=/opt/gbc/jpl/de440s.bsp
```

```bash
gbc validate astronomy-parity \
  --reference jpl-de440 \
  --jpl-ephemeris-path /opt/gbc/jpl/de440s.bsp
```

If the configured path is a directory, `JplReferenceSource` looks for:

```text
de440s.bsp
```

inside that directory.

## Optional Dependencies

Install validation dependencies with:

```bash
python -m pip install "gbc-astro[validation]"
```

The JPL validation path currently uses Skyfield, JPL/SPK reading through
Skyfield's dependency stack, and NumPy.

## Health Check Shape

`JplReferenceSource.health_check()` returns:

```json
{
  "status": "ok",
  "reference": "jpl-de440",
  "dataPath": "/opt/gbc/jpl/de440s.bsp",
  "dataVersion": "DE440S",
  "supportedBodies": [
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto"
  ],
  "supportedDateRange": [
    "1849-12-25",
    "2150-01-21"
  ]
}
```

Validation is blocked if the kernel is missing, unreadable, outside supported
range, or the optional validation dependency set is not installed.

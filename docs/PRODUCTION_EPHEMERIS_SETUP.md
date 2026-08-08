# Production Ephemeris Setup

Production must use explicit ephemeris paths. Do not rely on temporary
developer-machine paths such as `/private/tmp`.

## Directory Layout

Recommended layout:

```text
/opt/gbc/ephemeris/
  swiss/
    sepl_18.se1
    semo_18.se1
    seas_18.se1
  jpl/
    de440s.bsp
```

For the v0.1 production date range 1900-2026:

- `sepl_18.se1`: Swiss planetary ephemeris for recent-era core bodies;
- `semo_18.se1`: Swiss lunar ephemeris for the Moon;
- `seas_18.se1`: optional asteroid-style data used for Chiron.

If the production-supported date range changes, provision the matching Swiss
century files for that range and update the manifest checks before release.

Public Swiss Ephemeris download metadata is listed at:

- `https://www.astro.com/ftp/swisseph/ephe/`
- `https://github.com/aloistr/swisseph/tree/master/ephe`

## Environment Variables

Runtime natal calculation:

```bash
export GBC_SWISS_EPHE_PATH=/opt/gbc/ephemeris/swiss
```

Independent validation:

```bash
export GBC_JPL_EPHEMERIS_PATH=/opt/gbc/ephemeris/jpl/de440s.bsp
```

CLI options can override these values:

```bash
gbc natal ... --swiss-ephe-path /opt/gbc/ephemeris/swiss
```

```bash
gbc validate astronomy-parity \
  --reference jpl-de440 \
  --swiss-ephe-path /opt/gbc/ephemeris/swiss \
  --jpl-ephemeris-path /opt/gbc/ephemeris/jpl/de440s.bsp
```

## Container Example

```dockerfile
FROM python:3.12-slim

ENV GBC_SWISS_EPHE_PATH=/opt/gbc/ephemeris/swiss
ENV GBC_JPL_EPHEMERIS_PATH=/opt/gbc/ephemeris/jpl/de440s.bsp

COPY ephemeris/swiss/ /opt/gbc/ephemeris/swiss/
COPY ephemeris/jpl/de440s.bsp /opt/gbc/ephemeris/jpl/de440s.bsp
COPY . /app
WORKDIR /app
RUN python -m pip install .
```

Do not bake licensed or proprietary ephemeris data into an image unless the
deployment license permits redistribution.

## Health Checks

Swiss provider health:

```bash
python - <<'PY'
from gbc_astro.providers.swiss import SwissEphemerisProvider
print(SwissEphemerisProvider().health_check())
PY
```

JPL validation health:

```bash
python - <<'PY'
from gbc_astro.validation.reference import JplReferenceSource
print(JplReferenceSource().health_check())
PY
```

CI should also run:

```bash
gbc validate astronomy-parity \
  --reference jpl-de440 \
  --cases 10000 \
  --seed 42
```

## Failure Behavior

Missing Swiss data or unavailable provider dependencies must fail with
structured provider errors. The engine must not fabricate positions.

If optional Chiron data is missing, health can be `degraded` only when Chiron is
not part of the production chart contract. For charts that include Chiron, a
missing `seas_18.se1` blocks production readiness.

JPL data failures block validation, not normal chart rendering.

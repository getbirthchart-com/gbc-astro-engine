# Ephemeris Data Manifest

`gbc_astro` delegates astronomical positions to configured providers. The
default production provider is Swiss Ephemeris via `pyswisseph`.

## Configuration

Set the Swiss data path explicitly:

```bash
export GBC_SWISS_EPHE_PATH=/path/to/swisseph
```

or pass:

```bash
gbc natal ... --swiss-ephe-path /path/to/swisseph
```

Production must not rely on temporary development paths such as `/private/tmp`.

## Core Planetary Data

Production must provision Swiss Ephemeris data explicitly. For the v0.1
supported validation range, the manifest requires:

- `sepl_18.se1`: planetary ephemeris for Sun, Mercury, Venus, Mars, Jupiter,
  Saturn, Uranus, Neptune, Pluto, True Node and Mean Node.
- `semo_18.se1`: lunar ephemeris for the Moon.

Startup validation should still probe actual capability availability for:

- Sun
- Moon
- Mercury
- Venus
- Mars
- Jupiter
- Saturn
- Uranus
- Neptune
- Pluto
- True Node
- Mean Node

## Chiron

Chiron uses Swiss asteroid-style data. The current manifest knows about:

- `seas_18.se1`: Chiron and asteroid-style calculations around modern eras.

If this file is absent, provider startup health is `degraded`, and a chart that
requires Chiron returns a structured `PROVIDER_DEPENDENCY_MISSING` error instead
of silently omitting or fabricating Chiron.

## Health Check

`SwissEphemerisProvider.health_check()` returns:

```json
{
  "status": "ok|degraded|error",
  "provider": "swiss",
  "ephemerisPath": "...",
  "availableCapabilities": [],
  "unavailableCapabilities": [],
  "manifest": {
    "missingRequiredData": [],
    "missingOptionalData": []
  }
}
```

`error` means required planetary/lunar files are absent. `degraded` is
acceptable only when optional bodies are intentionally not used. It is not
acceptable for v0.1 production natal charts that require Chiron.

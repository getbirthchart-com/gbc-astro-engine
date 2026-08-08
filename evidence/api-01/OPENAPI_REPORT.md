# OpenAPI Report — API-01

## Schema source

Generated from the live FastAPI app (`create_app().openapi()`).

## Command

```bash
python -m gbc_astro.api.export_openapi
# default output: openapi/gbc-astro-v1.json
```

## Output path

```text
openapi/gbc-astro-v1.json
```

## Versions recorded in snapshot

- `info.version` = `v1` (HTTP API version)
- `info.x-gbc-api-version` = `v1`
- `info.x-gbc-engine-version` = `0.1.0`

## Drift check

`tests/api/test_natal_api.py::OpenApiExportTests::test_export_matches_committed_snapshot`
regenerates to a temp file and asserts equality with the committed snapshot.

## Frontend usage

`getbirthchart-web` should generate TypeScript types from the checked-in snapshot,
not from a live backend URL at build time.

# OpenAPI Report

Snapshot: `openapi/gbc-astro-v1.json`, regenerated with
`python -m gbc_astro.api.export_openapi`.

## Diff against v0.3.0

```
v0.3.0 paths : 9
current paths: 9
changed paths: NONE
removed paths: NONE
added paths  : NONE
changed schemas: ['TransitRequest']
removed schemas: NONE
added schemas  : NONE
```

The only contract change is `TransitRequest`, which gains an optional `top`
field with a default. Existing clients that omit it are unaffected.

## Backward compatibility

```
natal path identical to v0.1.0: True
```

`POST /v1/charts/natal` and `GET /health` have not changed since v0.1.0, across
three feature releases. Section 25 satisfied.

## Response shape

`TransitChart` gains `topAspects`, and each aspect gains `id`, `score`, `rank`,
`natalTarget` and `natalTargetKind`. `natalBody` was retained as an alias so no
field disappears from a schema frontends may already read. Response schemas are
not declared as OpenAPI components — routes return canonical documents directly,
as the natal route does — so generated request types are unchanged apart from
`top`.

## Frontend

The web app pins the contract by content hash in `.engine-version.json` and is
currently on `v0.2.0`, so it is unaffected until it re-pins deliberately with
`npm run contract:sync -- --tag <tag>`.

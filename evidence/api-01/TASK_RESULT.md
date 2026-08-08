Status: PASS

Implemented:
- Thin FastAPI adapter under `src/gbc_astro/api/`
- `GET /health`, `POST /v1/charts/natal`, `/docs`, `/openapi.json`
- Request model mapped explicitly to `AstrologyEngine.natal(...)`
- Structured error envelope preserving real `gbc_astro.errors` codes
- Optional `[api]` extra (FastAPI/Uvicorn); library/CLI remain independent
- Deterministic OpenAPI snapshot `openapi/gbc-astro-v1.json`
- Docs: `docs/API.md`, `docs/FRONTEND_API_HANDOFF.md`
- API tests: validation, DST errors, house failure, library/HTTP parity

Architecture:
```
AstrologyEngine ← CLI
               ← Python library
               ← FastAPI adapter (transport only)
```

Quality gates:
- ruff PASS
- mypy PASS
- pytest 62 passed, 2 skipped PASS
- OpenAPI export PASS
- CLI smoke PASS (Swiss)
- HTTP smoke PASS (health, known-time, unknown-time, openapi)

Known limitations:
- Production natal still requires `pyswisseph` + `GBC_SWISS_EPHE_PATH`
- No auth/rate-limit (deployment concern)
- Place search/geocoding remains out of scope
- Editable installs may need `pip install -e . --config-settings editable_mode=compat` on some pip/setuptools combos

Files:
- `src/gbc_astro/api/**`
- `tests/api/test_natal_api.py`
- `openapi/gbc-astro-v1.json`
- `docs/API.md`, `docs/FRONTEND_API_HANDOFF.md`
- `pyproject.toml` (`api` extra)
- `evidence/api-01/**`

Status: PASS

Implemented:
- Swiss Ephemeris provider integration through `pyswisseph`
- Configurable ephemeris path via `GBC_SWISS_EPHE_PATH` or `--swiss-ephe-path`
- Structured missing-data error for required files such as `seas_18.se1`
- Provider-backed golden sample for Sun/Moon/Chiron and metadata

Tests:
- `GBC_SWISS_EPHE_PATH=/private/tmp/gbc_swisseph PYTHONPATH=/private/tmp/gbc_deps:src python3 -m pytest -q tests/golden/test_swiss_natal.py` passed.
- CLI generated a complete Placidus natal chart using Swiss + local ephemeris data.

Differential evidence:
- Not yet complete. This is a provider-backed golden smoke test, not the required 10K differential corpus.

Known limitations:
- Swiss data files are not committed; production must provision them and set an ephemeris path.

Files changed:
- `src/gbc_astro/providers/swiss.py`
- `src/gbc_astro/cli.py`
- `tests/golden/test_swiss_natal.py`
- `README.md`


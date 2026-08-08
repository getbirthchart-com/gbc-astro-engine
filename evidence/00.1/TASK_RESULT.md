Status: PASS

Implemented:
- `src` package layout for `gbc_astro`
- `pyproject.toml` with Python 3.12+, Ruff, mypy and pytest configuration
- CLI entrypoint `gbc`
- README usage and current implementation boundary

Tests:
- `PYTHONPATH=/private/tmp/gbc_deps:src python3 -m pytest -q` passed.
- `/private/tmp/gbc_tools/bin/ruff check .` passed.
- `PYTHONPATH=/private/tmp/gbc_deps:src python3 -m mypy src` passed.
- `PYTHONPYCACHEPREFIX=/private/tmp/gbc_pycache PYTHONPATH=src python3 -m compileall -q src tests` passed.

Differential evidence:
- Not applicable for repository foundation.

Known limitations:
- Verification in this session used Python 3.9.6 plus dependencies installed under `/private/tmp`.
- CI is configured for Python 3.12, which remains the package requirement.

Files changed:
- `pyproject.toml`
- `README.md`
- `.gitignore`
- `src/gbc_astro/**`
- `tests/**`

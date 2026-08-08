Status: PASS

Implemented:
- `gbc benchmark` executes randomized natal calculations
- Seeded reproducible case generation
- Machine-readable runtime report
- Provider/data missing state remains explicit `blocked`

Tests:
- Benchmark ran 10,000 seeded Swiss-backed Equal-house cases successfully.
- Ruff, mypy and pytest passed after implementation.

Differential evidence:
- This is a runtime benchmark, not the required differential comparison.

Known limitations:
- The benchmark samples UTC datetimes and latitudes within +/-60 degrees by default to avoid intentionally undefined Placidus polar cases.
- 10K differential parity remains a separate pending gate.

Files changed:
- `src/gbc_astro/cli.py`
- `src/gbc_astro/engine.py`

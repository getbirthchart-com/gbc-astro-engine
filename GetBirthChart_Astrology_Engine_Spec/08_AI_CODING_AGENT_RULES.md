# 08 — AI Coding Agent Rules

## Mission

Implement `gbc_astro` as a production-grade deterministic astrology calculation engine.

## Absolute prohibitions

1. **DO NOT ask an LLM to calculate planetary positions.**
2. **DO NOT invent astronomical equations from memory.**
3. **DO NOT copy random astrology formulas from blogs.**
4. **DO NOT silently substitute noon when birth time is unknown.**
5. **DO NOT silently resolve ambiguous DST timestamps.**
6. **DO NOT silently fallback from Placidus to another house system.**
7. **DO NOT hard-code UTC offsets by city.**
8. **DO NOT couple domain calculations to FastAPI, database, UI or AI interpretation.**
9. **DO NOT mark a phase complete without tests and evidence.**
10. **DO NOT implement later releases before current release acceptance gate passes.**

## Required working method

For every task:

1. Read:
   - master requirements
   - architecture
   - relevant calculation spec
   - canonical contract
   - definition of done
2. Inspect current repository.
3. State assumptions in task report.
4. Implement the smallest correct vertical slice.
5. Add unit tests.
6. Add edge/regression tests where relevant.
7. Run tests.
8. Run differential comparison where relevant.
9. Record evidence.
10. Only then mark task PASS.

## Reference discipline

When implementing any nontrivial astronomical/house/progression algorithm:
- prefer a trusted library/provider or authoritative technical reference;
- cite/reference the algorithm source in code/docstrings where appropriate;
- record convention choices;
- add differential tests.

If the correct convention cannot be established, stop that feature as `BLOCKED` rather than guessing.

## Deterministic boundary

The engine may output:

- astronomical positions
- zodiac positions
- houses
- aspects
- derived deterministic classifications
- exact event timestamps
- versioned deterministic scoring only if a scoring profile is specified

The engine must not output statements such as:
- "you are loyal"
- "your ex will return"
- "this relationship is destined"
- prose interpretations

## Code quality

- Python 3.12+
- `pyproject.toml`
- type hints on public API
- Pydantic/dataclasses where appropriate
- Ruff
- mypy or pyright
- pytest
- Hypothesis for property tests
- clear modules, no god files
- no hidden mutable global calculation settings

## Precision

Do not round internal astronomical values for storage or downstream calculations.

Only formatting layer converts:
`224.721843°` → `14°43′... Scorpio`.

## Error policy

All unsupported/uncertain conditions must be explicit structured errors/warnings.

## Evidence artifacts

Each implementation task should update/create:

```text
evidence/<task-id>/TASK_RESULT.md
evidence/<task-id>/TEST_OUTPUT.txt
```

`TASK_RESULT.md`:

```text
Status: PASS | FAIL | BLOCKED
Implemented:
Tests:
Differential evidence:
Known limitations:
Files changed:
```

## Completion phrase

A task is complete only when:
- code exists;
- tests pass;
- required differential/edge tests pass;
- evidence is written;
- no unresolved correctness concern is hidden.

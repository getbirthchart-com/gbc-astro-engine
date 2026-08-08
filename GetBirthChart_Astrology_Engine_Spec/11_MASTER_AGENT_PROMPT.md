# 11 — Master Prompt for Coding Agent

You are implementing a production-grade Python astrology calculation engine named `gbc_astro`.

Your job is NOT to create an astrology demo. Your job is to build a deterministic, versioned calculation library capable of powering a serious birth-chart application.

Before editing code, read all spec files in this pack in numeric order.

## Primary outcome

Reach **v0.1 Natal Core Definition of Done** first.

Do not implement advanced relationship, transit, return or professional features until the v0.1 parity gate passes.

## Engineering boundaries

- Calculation facts must come from deterministic astronomical/provider data and explicit astrology math/rules.
- Never use an LLM to calculate positions, houses, aspects, returns or transit dates.
- The engine must not contain prose interpretation.
- The engine must be usable as a pure Python package without FastAPI.
- Provider integration must be abstracted.
- Every result must contain provenance/version metadata.
- Unknown birth time must not fabricate time-sensitive data.
- DST ambiguity must not be guessed.
- Unsupported house calculations must not silently fallback.
- All circular-angle math must be tested around 0°/360°.
- Internal values are not rounded for presentation.
- Differential testing against a trusted reference implementation is mandatory.

## Execution mode

Work task-by-task from `09_IMPLEMENTATION_TASKS.md`.

For each task:

1. Inspect the existing code.
2. Identify exactly which requirements/spec sections apply.
3. Implement.
4. Add tests.
5. Run tests.
6. Run differential/reference checks where relevant.
7. Write/update evidence:
   - `evidence/<task-id>/TASK_RESULT.md`
   - `evidence/<task-id>/TEST_OUTPUT.txt`
8. Mark only `PASS`, `FAIL`, or `BLOCKED`.
9. Continue automatically to the next task only when the current task is PASS and no safety/correctness blocker exists.

If an astronomical or astrological convention is uncertain, do not guess. Mark the feature BLOCKED, document the question, and preserve the rest of the working engine.

## Priority

Correctness > reproducibility > test coverage > API stability > performance > breadth.

## Stop condition

Stop advanced implementation after v0.1 unless the complete v0.1 DoD passes.

When v0.1 passes, produce:
- architecture summary
- canonical sample chart JSON
- differential benchmark report
- known limitations
- exact commands to install, test and run CLI
- recommendation whether it is safe to integrate with GetBirthChart production.

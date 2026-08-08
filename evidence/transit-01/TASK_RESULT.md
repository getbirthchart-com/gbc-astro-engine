Status: PASS

Phase 08B-1 — Minimal Personalized Transit Engine + HTTP API.

## What existed before this task

A transit snapshot shipped in v0.3 (Phases 10-12) with positions, aspects,
house placements and real applying/separating. Against this brief it was missing
the entire product layer: a dedicated orb profile, deterministic IDs, ranking, a
top-N subset, angle targets, full provenance, and the documentation and evidence
set. Roughly 13 of the 20 PASS criteria in section 38 were already met; this
task closed the other seven.

## Rules

- **Rule 1** — no validated natal math was modified. Every primitive was reused
  unchanged: provider, normalisation, aspect matching, circular math, house
  assignment, timezone handling. No defect in core math surfaced, so Rule 1's
  BLOCKED path was never engaged. See `CURRENT_ENGINE_AUDIT.md`.
- **Rule 2** — no LLM, no prompt logic, no prose. Ranking is arithmetic over
  published weights.
- **Rule 3** — deterministic. Repeated calls are byte-identical and ordering is
  stable across runs, both asserted.

## The change that mattered most

Natal orbs were being reused for transits. Measured across twelve monthly
snapshots that left 27 to 44 aspects active at every moment — no basis for
surfacing a meaningful three.

`transit-major-v1` (3°/3°/3°/3°/2°) was chosen from measurement rather than
copied from the brief's example, and yields a mean of 14.6 active aspects.
Full comparison table in `ASPECT_PROFILE.md`.

Without ranking in the engine, the frontend would have had to pick the top three
itself — which would have moved an astrological decision out of the engine and
broken the brief's own first rule.

## Deliverables

| Section | Item | Where |
|---|---|---|
| 5 | `transit-major-v1` orb profile | `profiles/transit.py` |
| 13 | Deterministic IDs `transit.mars.square.natal.moon` | `models/forecast.py` |
| 14-17 | `transit-ranking-v1`, `topAspects`, default 3 | `profiles/transit.py`, `forecast/transits.py` |
| 3 | Ascendant and Midheaven targets, known-time only | `forecast/transits.py` |
| 19 | Both profile versions plus full weights in `meta` | `forecast/transits.py` |
| 34-35 | `docs/TRANSITS.md`, `docs/FRONTEND_TRANSIT_HANDOFF.md` | `docs/` |
| 36 | This evidence set | `evidence/transit-01/` |

Descendant and IC were deliberately excluded as targets: each is the exact
opposite of an included angle, so counting both would report one geometric fact
twice — the same defect already found and fixed in relationship scoring.

## Quality gates

| Gate | Result |
|---|---|
| ruff | PASS |
| mypy (strict, 75 files) | PASS |
| pytest | PASS — 267 passed, 0 skipped |
| OpenAPI export | PASS |
| Library transit smoke | PASS |
| HTTP transit smoke | PASS |
| Unknown-time smoke | PASS |
| Natal regression | PASS — natal path byte-identical to v0.1.0 |
| Library/API parity | PASS — 3 of 3 scenarios identical |
| Determinism | PASS |

## Deviation from the brief

The endpoint is `POST /v1/forecast/transits`, not `/v1/charts/transits`. Section
21 allows "a similarly clean endpoint"; transits sit with the event and return
searches because they are the same domain, and chart routes stay chart routes.

## Known limitations

- Snapshot only. "When does this become exact" is `POST /v1/forecast/events`.
- The ranking is an editorial ordering with no independent reference, unlike the
  positions it ranks. Stated in the profile and in the docs.
- Transiting nodes and Chiron are excluded by design, not by omission.

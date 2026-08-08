# v1.2 — response schemas for every route

## The defect

All seventeen v1 routes published `{}` as their 200 response schema. Only
`/health` and `/ready` were typed.

Every route returns a bare `JSONResponse`, so FastAPI had nothing to
introspect and emitted an empty schema. The consequence was invisible from the
engine side and severe from the client side: a frontend vendoring the contract
got request types and **no response types at all**, leaving it to hand-write the
shape of every chart from a documentation example.

That defeats both mechanisms the project relies on to keep two repositories in
step. The vendored contract exists so the wire format is a derived artifact of a
named engine tag rather than something maintained by hand; the frontend's
contract test exists so drift fails a build. With an empty response schema the
first carries no response information and the second can only check that paths
exist.

It also meant the v1.1 rulership block was **absent from the contract**. A
client syncing to v1.1.0 would have found no mention of `chartRuler`,
`dignities`, `dispositors` or `dominantPlanets` and reasonably concluded they
did not exist.

## Documentation, never filtering

The schemas are attached with `responses={200: {"model": ...}}`, not with
`response_model=`.

The distinction is the whole design. Under `response_model` FastAPI coerces the
payload through the model, so any field the model forgot would be **silently
dropped from the response** — a documentation defect promoted to a data defect,
in a codebase whose entire discipline is that nothing is silently omitted.
Declaring under `responses` publishes the schema and leaves `to_dict()` the sole
author of what is sent.

Asserted directly: `test_declaring_a_schema_does_not_filter_the_payload`
compares the HTTP payload's keys against the same chart taken straight from the
engine.

## What stops them drifting

Nothing structural, which is the cost of not filtering. So real engine output is
validated against every published model — one live call per route, table-driven,
including the awkward shapes:

- an unknown-time natal chart (no angles, no houses, no chart ruler, `house`
  null on every body) — where an over-tight schema would show up
- a sidereal natal chart, which carries three meta fields the tropical one never
  has
- a chart with actual patterns, so the pattern schema meets populated output
- a chart with none, since empty is the common case

A new route added without a response model shows up as a missing table entry
rather than as an empty schema discovered at integration time.

`extra="allow"` throughout: the schemas describe a floor, not a ceiling. A
caller may rely on every named field being present, and the engine may add
fields in a minor release without any client's parser rejecting the payload.

## Result

```
before: 17 of 19 routes published {}
after:  0 routes publish {}
contract: 1,977 -> 4,378 lines, 44 new component schemas
```

Purely additive, verified structurally: no path lost, no path added, no
pre-existing request schema changed by a single byte. The 150 deleted lines are
the empty `{}` stubs being replaced.

```
ruff   clean
mypy   clean, 97 source files
pytest 502 passed, 763 subtests, 0 skipped   (490 -> 502)
```

## For the client

`npm run contract:sync -- --tag v1.2.0` now yields real response types for all
seventeen routes. The capability resolver has something to resolve against, and
the rulership fields are finally in the contract.

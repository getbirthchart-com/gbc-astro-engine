# Security and memory audit

Scope: the Python core and its HTTP adapter. Findings are ordered by severity.

## Summary

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Race on Swiss Ephemeris global sidereal mode | **High** | fixed |
| 2 | Unbounded astrocartography response | **Medium** | fixed |
| 3 | Malformed timezone became a 500 | Low | fixed |
| — | Memory leak | none found | — |

No code execution, injection, SSRF, deserialisation or secret-exposure issue was
found. `src/` contains no `eval`, `exec`, `subprocess`, `pickle` or network call;
the only network access in the repository is in `tools/`, which are operator-run
maintenance scripts. `pip-audit` reports no known vulnerabilities in the
dependency tree.

---

## 1. Race on the global sidereal mode — High

Swiss Ephemeris keeps the sidereal mode in **process-global state**. Selecting a
mode and reading the ayanamsa were two separate calls against one shared
variable:

```python
self._swe.set_sid_mode(mode, 0, 0)
return float(self._swe.get_ayanamsa_ut(julian_day))
```

FastAPI runs synchronous route handlers in a threadpool, so two requests for
different ayanamsas genuinely interleave.

**Measured** with 12,000 concurrent calls across three ayanamsas under forced
GIL switching:

```
lahiri:         54/4000 returned another thread's value
raman:          54/4000
fagan_bradley:  57/4000
total:         165/12000  (1.4%)
```

A Lahiri request answered with Raman is **1.45 degrees out** — enough to move a
planet into the neighbouring sign. No exception, no log line: silently wrong
output, which is the worst failure mode this engine can have.

**Fixed** with a module-level lock around the select-then-read pair. The lock is
module-level rather than per-instance because the state it guards belongs to the
library, not to any one calculator. Re-measured: 0/12,000 wrong.

Regression test: `tests/api/test_security.py::AyanamsaConcurrencyTests`, which
also asserts the ayanamsas differ by more than a degree so the test cannot pass
vacuously.

---

## 2. Unbounded astrocartography response — Medium

`latitude_step` was validated as `> 0`, which permitted `0.001`. Over the
default latitude band that is 132,000 samples; with thirteen bodies on four
lines, 6.8 million points.

**Measured**: one unauthenticated request produced **9.2 seconds of CPU and a
351 MB response**. A handful in parallel would exhaust memory and saturate the
threadpool.

**Fixed** by budgeting what actually costs — points, not step size.
`MAX_LINE_POINTS = 200_000` is enforced in the domain module, so a caller
reaching the library directly hits the same wall as one arriving over HTTP. The
schema also floors the step at 0.05 and caps body lists at 32.

Worst permitted case now: 138 ms, 6.8 MB.

| Request | Before | After |
|---|---|---|
| `latitude_step: 0.001` | 9249 ms, 351 MB | 422 in 20 ms |
| `latitude_step: 0.05`, all bodies | — | 200 in 139 ms, 6.8 MB |
| `bodies: ["sun"] * 10000` | 200 | 422 |

---

## 3. Malformed timezone became a 500 — Low

`ZoneInfo("../../etc/passwd")` raises `ValueError`, not
`ZoneInfoNotFoundError`, and only the latter was caught. The `ValueError`
escaped and became a 500 with a full stack trace in the logs.

**No traversal was possible**: Python's `zoneinfo` validates the key against
`TZPATH` and refuses to leave it, which is what raised in the first place. The
response body never carried the trace either — the error handler already
returned a generic envelope.

The defect was that a bad request looked like a server fault. A 500 is
indistinguishable from a real outage in monitoring, triggers retries, and writes
a stack trace per occurrence, which is free log volume for anyone who wants it.

**Fixed**: `ValueError` and `TypeError` now map to `UNKNOWN_TIMEZONE` alongside
`ZoneInfoNotFoundError`. Verified across path traversal, absolute paths, null
bytes, 5,000-character strings and whitespace — all return 400 or 422, none leak
a trace or a filesystem path.

---

## Memory

**No leak found.**

Isolating the layers was necessary because a naive measurement through
`TestClient` suggested 5.2 KB per request:

| Path | Growth per call |
|---|---:|
| `engine.natal()` tropical | +2 B |
| `engine.natal()` sidereal | +13 B |
| `GET /health` via TestClient | +5,246 B |
| `POST /v1/charts/natal` via TestClient | +5,411 B |

`/health` performs no calculation and grew the same as a full chart, which
identified the growth as TestClient bookkeeping rather than engine behaviour.

Confirmed against a real uvicorn server measuring RSS:

```
after 200 warm-up requests : 54 MB
after 1500 more requests   : 55 MB
                             174 B/request
```

That is allocator arena behaviour, not accumulation. The 20-year station search
peaks at 2.99 MB and returns to baseline exactly on release.

---

## Not fixed, by design

**No authentication or rate limiting.** Deliberate and documented in
`docs/DEPLOYMENT.md`, which states plainly that the service must not be exposed
to the public internet unauthenticated. It is intended to sit behind the
frontend's server or a proxy. That remains a deployment responsibility, and the
absence of a limiter is why finding 2 mattered enough to fix in the engine.

**CORS is off unless configured.** The intended path is browser → Next.js server
action → engine, so the browser never talks to this service.

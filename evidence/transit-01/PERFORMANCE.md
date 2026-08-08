# Performance

Section 33. Measured over 200 consecutive daily instants against the reference
chart, Swiss Ephemeris provider, warm process.

| | Known time | Unknown time |
|---|---:|---:|
| Mean | 0.131 ms | 0.097 ms |
| p50 | 0.128 ms | 0.097 ms |
| p95 | 0.145 ms | 0.109 ms |
| Max | 0.457 ms | 0.119 ms |
| Aspects (mean / min / max) | 14.6 / 6 / 22 | 13.4 / 4 / 22 |

Ranking alone: **0.0121 ms** per call over 10,000 iterations on a 12-aspect
result.

## Reading

Ranking is roughly a tenth of the total, and the total is dominated by ten
ephemeris lookups. Nothing here needs optimising: a transit snapshot is two
orders of magnitude cheaper than the HTTP round trip that carries it.

The known-time maximum of 0.457 ms is a first-call artefact — Swiss Ephemeris
opens and caches its data files on the first lookup of a process. The p95 is the
honest figure.

No per-request inefficiency was found. The transit path performs exactly ten
provider calls and no repeated lookups.

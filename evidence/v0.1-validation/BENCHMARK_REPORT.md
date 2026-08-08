# Benchmark Report

Status: PASS

Provider: Swiss Ephemeris 2.10.03 with `sepl_18.se1`, `semo_18.se1`, and `seas_18.se1`

Seed: 42

Cases per house system: 10,000

Ephemeris path used for validation: `/private/tmp/gbc_swisseph`

The path above is a development-only path. Production must provision an explicit Swiss Ephemeris data directory and set `GBC_SWISS_EPHE_PATH`.

| House system | Status | Successes | Runtime ms | P50 ms | P95 ms | P99 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| Whole Sign | pass | 10000 | 2509.933542 | 0.24366600000003125 | 0.279417000000004 | 0.35087500000008376 | 0.9421249999999604 |
| Equal | pass | 10000 | 2505.2462499999997 | 0.24466599999994898 | 0.27549999999987307 | 0.3292080000001363 | 1.0175840000000158 |
| Placidus | pass | 10000 | 2500.641125 | 0.2415000000000056 | 0.27137500000007364 | 0.36470800000000525 | 2.7380830000000023 |

Correctness remains higher priority than performance. These benchmarks do not replace independent numerical parity validation.

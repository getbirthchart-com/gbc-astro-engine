# Public Golden Tests

This document describes the small public regression set for GetBirthChart
Core. It is intentionally curated from existing trusted fixtures and golden
tests; it does not invent new planetary values for marketing copy.

## What is frozen

- A known-time Hanoi natal chart pins Sun, Moon, Chiron, Ascendant, Midheaven,
  the first house cusp, Big Three labels, and the major-aspect count.
- The relationship regression pins composite positions, derived angles,
  overlays, and aspect counts.
- Time normalization pins explicit errors for nonexistent and ambiguous local
  times, and proves that PEP 495 folds resolve to different UTC instants.
- Unknown birth time pins omission of angles and houses plus the explicit
  `UNKNOWN_BIRTH_TIME` warning.
- The hostile corpus keeps coverage for DST, zodiac and circular boundaries,
  house cusps, high latitudes, retrograde stations, unknown time, date-line
  conversions, and leap days.

The exact values in `tests/fixtures/public_golden_cases.json` are copied from
the existing trusted tests named by each `source_test` field. A change to a
frozen value requires a deliberate engine or methodology change, not a silent
fixture refresh.

## Unknown-time Moon policy

The engine can calculate planetary positions at the start of a local date, but
that timestamp is not a confirmed birth time. The web product therefore checks
the Moon across the local-date interval. If it changes signs, the UI presents
the possible signs as ambiguous; it never turns the midnight approximation
into a definitive Moon sign. Angles and houses remain unavailable without a
reliable birth time.

## Run

With the Swiss Ephemeris files configured:

```bash
GBC_SWISS_EPHE_PATH=/path/to/ephemeris python -m unittest \
  tests.golden.test_swiss_natal \
  tests.golden.test_relationship_golden \
  tests.golden.test_public_golden_cases
```

The manifest and boundary-contract tests also run without Swiss Ephemeris data.

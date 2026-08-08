# Hostile Case Report

Status: PASS

Case count: 100

Categories:
- circular_boundary: 8
- date_line: 8
- dst: 10
- geography: 6
- high_latitude: 8
- house_cusp: 8
- leap_day: 8
- retrograde_station: 12
- unknown_time: 8
- zodiac_boundary: 24

Expected behavior:
- error: 17
- success: 75
- warning: 8

- Corpus is hostile input coverage, not an independent numerical reference.
- DST and unknown-time behavior are exercised by pytest edge-case tests.
- High-latitude Placidus behavior is exercised by Swiss golden tests when data exists.

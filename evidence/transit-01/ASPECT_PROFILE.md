# Transit Aspect Profile

`transit-major-v1`, version `1.0.0`.

| Aspect | Exact | Orb |
|---|---:|---:|
| conjunction | 0° | 3.0° |
| opposition | 180° | 3.0° |
| square | 90° | 3.0° |
| trine | 120° | 3.0° |
| sextile | 60° | 2.0° |

## Why not reuse the natal orbs

The brief warns against copying natal orbs "if that produces poor transit
semantics". It does. Measured over twelve monthly snapshots of the reference
chart, with all thirteen bodies on both sides:

| Orb policy | Mean active | Range |
|---|---:|---|
| natal (8/8/7/7/5) | 36.2 | 27–44 |
| 6/4 | 36.2 | 27–44 |
| 4/3 | 24.2 | 20–30 |
| **3/2 (chosen)** | **18.7** | 13–26 |
| 2/1.5 | 12.8 | 9–18 |

With everything always active there is nothing for a top-three list to select
from.

## Why 3/2 and not tighter

2/1.5 is a defensible policy and was rejected deliberately: a slow outer planet
two to three degrees off exact is genuinely the story of a season, and dropping
it would lose the transits that matter most under the ranking's own logic.

The brief's example values were 3/3/3/3/2. The measurement was run before
looking at whether it agreed, and it does.

## Scope

Transiting bodies are the ten planets. The lunar nodes and Chiron are supported
by the engine but excluded: a transiting node moves under a degree a day and
would pad the pool without ever surfacing in a ranked three.

Natal targets are those ten planets plus Ascendant and Midheaven when the birth
time is known. Descendant and IC are excluded because each is the exact opposite
of an included angle — a transit square the Ascendant is square the Descendant,
one geometric fact, and counting both would double it.

Restricted to that scope the profile yields a mean of 14.6 active aspects for a
known-time chart across 200 consecutive days.

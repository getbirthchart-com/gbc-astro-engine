#!/usr/bin/env python3
"""Freeze a Chiron reference corpus from JPL Horizons.

Maintenance tool, not part of the package. Run it to regenerate
`tests/fixtures/chiron_horizons_reference.json`; validation itself reads the
frozen file and never touches the network, so CI stays deterministic and
offline.

Why Horizons: DE440S carries only the major planets, so the JPL track that
validates Sun through Pluto cannot reach Chiron. Horizons publishes its own
small-body orbit solution for 2060 Chiron, which is independent of the Swiss
Ephemeris `seas_18.se1` integration the engine uses. `QUANTITIES=31` returns
observer-centred ecliptic-of-date longitude and latitude, matching the
apparent geocentric frame the engine reports.

Usage:
    python tools/fetch_chiron_horizons.py [--steps 500] [--start 1900-01-01]
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HORIZONS_API = "https://ssd.jpl.nasa.gov/api/horizons.api"
FIXTURE_PATH = Path("tests/fixtures/chiron_horizons_reference.json")

# "1992-Nov-03 00:00     142.5913907  -6.5102916"
# Horizons appends seconds and milliseconds when the step does not land on a
# whole minute, which it does whenever the range is divided into N intervals.
ROW = re.compile(
    r"^\s*(\d{4})-([A-Za-z]{3})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?\s+"
    r"(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$"
)
MONTH_NAMES = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)  # fmt: skip
MONTHS = {name: index for index, name in enumerate(MONTH_NAMES, start=1)}


def fetch(start: str, stop: str, steps: int) -> str:
    query = urllib.parse.urlencode(
        {
            "format": "text",
            "COMMAND": "'2060;'",
            "OBJ_DATA": "'NO'",
            "MAKE_EPHEM": "'YES'",
            "EPHEM_TYPE": "'OBSERVER'",
            "CENTER": "'500@399'",
            "START_TIME": f"'{start}'",
            "STOP_TIME": f"'{stop}'",
            "STEP_SIZE": f"'{steps}'",
            "QUANTITIES": "'31'",
            "CAL_TYPE": "'GREGORIAN'",
        }
    )
    with urllib.request.urlopen(f"{HORIZONS_API}?{query}", timeout=180) as response:
        return response.read().decode("utf-8")


def parse(payload: str) -> list[dict[str, float | str]]:
    body = payload.split("$$SOE", 1)
    if len(body) != 2:
        raise SystemExit("Horizons response has no $$SOE marker:\n" + payload[:800])
    rows: list[dict[str, float | str]] = []
    for line in body[1].split("$$EOE", 1)[0].splitlines():
        match = ROW.match(line)
        if not match:
            continue
        year, month, day, hour, minute, second, longitude, latitude = match.groups()
        instant = datetime(
            int(year),
            MONTHS[month],
            int(day),
            int(hour),
            int(minute),
            int(second or 0),
            tzinfo=timezone.utc,
        )
        rows.append(
            {
                "utc": instant.isoformat().replace("+00:00", "Z"),
                "longitudeDeg": float(longitude),
                "latitudeDeg": float(latitude),
            }
        )
    if not rows:
        raise SystemExit("Horizons returned no parsable rows.")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="1900-01-01")
    parser.add_argument("--stop", default="2026-12-31")
    parser.add_argument("--steps", type=int, default=500)
    args = parser.parse_args()

    rows = parse(fetch(args.start, args.stop, args.steps))
    fixture = {
        "source": "JPL Horizons",
        "sourceUrl": HORIZONS_API,
        "target": "2060 Chiron",
        "command": "2060;",
        "center": "500@399 (geocentric)",
        "quantities": "31 (observer ecliptic longitude/latitude, ecliptic of date)",
        "frame": "apparent geocentric ecliptic of date",
        "capturedAt": datetime.now(timezone.utc).date().isoformat(),
        "range": {"start": args.start, "stop": args.stop, "steps": args.steps},
        "independentOfSwissEphemeris": True,
        "note": (
            "Frozen because DE440S contains no minor planets, so the JPL track "
            "cannot reach Chiron. Horizons uses its own small-body orbit solution, "
            "independent of the Swiss seas_18.se1 integration under validation. "
            "Regenerate with tools/fetch_chiron_horizons.py."
        ),
        "samples": rows,
    }
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} samples to {FIXTURE_PATH}")
    print(f"  {rows[0]['utc']} .. {rows[-1]['utc']}")


if __name__ == "__main__":
    main()

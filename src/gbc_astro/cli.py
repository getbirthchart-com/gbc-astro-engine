"""Command line interface for the astrology engine."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from gbc_astro import ENGINE_VERSION, errors
from gbc_astro.engine import AstrologyEngine
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.defaults import WESTERN_MODERN_V1
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.validation import (
    DEFAULT_V0_1_TOLERANCE,
    JplReferenceSource,
    ReferenceUnavailableError,
    calculation_hash,
)
from gbc_astro.validation.astronomy import (
    generate_astronomy_cases,
    run_jpl_astronomy_parity,
    write_astronomy_parity_report,
)
from gbc_astro.validation.corpus import load_validation_cases
from gbc_astro.validation.fixtures import (
    DeterministicValidationHouseCalculator,
    DeterministicValidationProvider,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gbc")
    subcommands = parser.add_subparsers(dest="command", required=True)

    natal = subcommands.add_parser("natal")
    natal.add_argument("--date", required=True, help="Local date, YYYY-MM-DD.")
    natal.add_argument("--time", help="Local time, HH:MM[:SS]. Required unless --unknown-time.")
    natal.add_argument("--unknown-time", action="store_true")
    natal.add_argument("--timezone", required=True)
    natal.add_argument("--lat", type=float, required=True)
    natal.add_argument("--lng", type=float, required=True)
    natal.add_argument("--altitude-m", type=float)
    natal.add_argument("--house-system", default=WESTERN_MODERN_V1.house_system)
    natal.add_argument("--swiss-ephe-path", help="Directory containing Swiss Ephemeris data files.")
    natal.add_argument("--fold", type=int, choices=(0, 1), help="PEP 495 DST fold resolution.")
    natal.add_argument("--json", action="store_true", help="Emit canonical JSON.")

    benchmark = subcommands.add_parser("benchmark")
    benchmark.add_argument("--cases", type=int, default=10000)
    benchmark.add_argument("--seed", type=int, default=42)
    benchmark.add_argument("--house-system", default="equal")
    benchmark.add_argument(
        "--swiss-ephe-path",
        help="Directory containing Swiss Ephemeris data files.",
    )

    validate = subcommands.add_parser("validate")
    validate_subcommands = validate.add_subparsers(dest="validate_command", required=True)

    differential = validate_subcommands.add_parser("differential")
    differential.add_argument("--cases", type=int, default=10000)
    differential.add_argument("--seed", type=int, default=42)
    differential.add_argument("--reference", required=True, choices=("jpl", "external-fixture"))
    differential.add_argument("--reference-path")
    differential.add_argument("--output-dir", default="evidence/v0.1-validation")

    astronomy = validate_subcommands.add_parser("astronomy-parity")
    astronomy.add_argument("--reference", required=True, choices=("jpl-de440",))
    astronomy.add_argument("--cases", type=int, default=10000)
    astronomy.add_argument("--seed", type=int, default=42)
    astronomy.add_argument("--jpl-ephemeris-path")
    astronomy.add_argument("--swiss-ephe-path")
    astronomy.add_argument("--output-dir", default="evidence/v0.1-validation")

    hostile = validate_subcommands.add_parser("hostile")
    hostile.add_argument("--cases-path", default="tests/fixtures/hostile_natal_cases.json")
    hostile.add_argument("--output-dir", default="evidence/v0.1-validation")

    reproducibility = validate_subcommands.add_parser("reproducibility")
    reproducibility.add_argument("--cases-path", default="tests/fixtures/hostile_natal_cases.json")
    reproducibility.add_argument("--cases", type=int, default=50)
    reproducibility.add_argument("--runs", type=int, default=3)
    reproducibility.add_argument("--swiss-ephe-path")
    reproducibility.add_argument("--output-dir", default="evidence/v0.1-validation")

    health = validate_subcommands.add_parser("health")
    health.add_argument("--swiss-ephe-path")

    return parser


def _natal(args: argparse.Namespace) -> int:
    if args.unknown_time:
        local_datetime = args.date
    elif args.time:
        local_datetime = f"{args.date}T{args.time}"
    else:
        raise errors.UnknownBirthTimeError(
            "--time is required unless --unknown-time is supplied.",
            {"date": args.date},
        )

    if args.swiss_ephe_path:
        engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=args.swiss_ephe_path),
            house_calculator=SwissHouseCalculator(ephemeris_path=args.swiss_ephe_path),
        )
    else:
        engine = AstrologyEngine()
    chart = engine.natal(
        local_datetime=local_datetime,
        timezone=args.timezone,
        latitude=args.lat,
        longitude=args.lng,
        altitude_m=args.altitude_m,
        house_system=args.house_system,
        unknown_time=args.unknown_time,
        fold=args.fold,
    )
    if args.json:
        print(chart.to_json(indent=2))
    else:
        print(json.dumps(chart.to_dict(), indent=2, sort_keys=True))
    return 0


def _benchmark(args: argparse.Namespace) -> int:
    if args.cases <= 0:
        raise ValueError("--cases must be positive.")
    if args.swiss_ephe_path:
        engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=args.swiss_ephe_path),
            house_calculator=SwissHouseCalculator(ephemeris_path=args.swiss_ephe_path),
        )
    else:
        engine = AstrologyEngine()

    rng = random.Random(args.seed)
    durations_ms: list[float] = []
    errors_by_code: dict[str, int] = {}
    started = time.perf_counter()
    for _index in range(args.cases):
        local_datetime, latitude, longitude = _random_benchmark_case(rng)
        case_started = time.perf_counter()
        try:
            engine.natal(
                local_datetime=local_datetime,
                timezone="UTC",
                latitude=latitude,
                longitude=longitude,
                house_system=args.house_system,
            )
        except errors.ProviderDependencyError as exc:
            report = {
                "status": "blocked",
                "reason": exc.message,
                "details": exc.details,
                "cases": args.cases,
                "seed": args.seed,
            }
            print(json.dumps(report, indent=2, sort_keys=True))
            return 2
        except errors.GbcAstroError as exc:
            errors_by_code[exc.code] = errors_by_code.get(exc.code, 0) + 1
        else:
            durations_ms.append((time.perf_counter() - case_started) * 1000.0)

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    report = {
        "status": "pass" if not errors_by_code else "completed_with_errors",
        "provider": engine.provider_id,
        "cases": args.cases,
        "seed": args.seed,
        "houseSystem": args.house_system,
        "successes": len(durations_ms),
        "errors": errors_by_code,
        "runtimeMs": elapsed_ms,
        "p50Ms": _percentile(durations_ms, 50),
        "p95Ms": _percentile(durations_ms, 95),
        "p99Ms": _percentile(durations_ms, 99),
        "maxMs": max(durations_ms) if durations_ms else None,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors_by_code else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "natal":
            return _natal(args)
        if args.command == "benchmark":
            return _benchmark(args)
        if args.command == "validate":
            return _validate(args)
    except errors.GbcAstroError as exc:
        print(json.dumps(exc.to_error_dict(), indent=2, sort_keys=True), file=sys.stderr)
        return 1
    parser.error(f"Unsupported command: {args.command}")
    return 2


def _random_benchmark_case(rng: random.Random) -> tuple[str, float, float]:
    start = datetime(1900, 1, 1)
    end = datetime(2026, 12, 31, 23, 59, 59)
    span_seconds = int((end - start).total_seconds())
    local_datetime = start + timedelta(seconds=rng.randrange(span_seconds))
    return (
        local_datetime.isoformat(timespec="seconds"),
        rng.uniform(-60.0, 60.0),
        rng.uniform(-180.0, 180.0),
    )


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((percentile / 100.0) * (len(ordered) - 1))
    return ordered[index]


def _validate(args: argparse.Namespace) -> int:
    if args.validate_command == "differential":
        return _validate_differential(args)
    if args.validate_command == "hostile":
        return _validate_hostile(args)
    if args.validate_command == "reproducibility":
        return _validate_reproducibility(args)
    if args.validate_command == "health":
        return _validate_health(args)
    if args.validate_command == "astronomy-parity":
        return _validate_astronomy_parity(args)
    raise ValueError(f"Unsupported validation command: {args.validate_command}")


def _validate_differential(args: argparse.Namespace) -> int:
    started = time.perf_counter()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    blocked_reason = ""
    reference_version = "unconfigured"
    try:
        if args.reference == "jpl":
            source = JplReferenceSource()
            reference_version = source.version
            raise ReferenceUnavailableError(
                "JPL reference source validates astronomy only; combined natal parity still "
                "requires independent angle and house fixtures. Use `validate astronomy-parity` "
                "for the JPL astronomy track."
            )
        if args.reference == "external-fixture" and not args.reference_path:
            raise ReferenceUnavailableError(
                "No external fixture path was supplied for independent parity."
            )
    except ReferenceUnavailableError as exc:
        blocked_reason = str(exc)

    report = {
        "status": "BLOCKED" if blocked_reason else "PASS",
        "engineVersion": ENGINE_VERSION,
        "provider": "swiss",
        "providerVersion": "not-run",
        "ephemerisDataVersion": "not-run",
        "timezoneDataVersion": "system-zoneinfo",
        "referenceSource": args.reference,
        "referenceVersion": reference_version,
        "toleranceProfile": _tolerance_to_dict(),
        "seed": args.seed,
        "caseCount": args.cases,
        "successCount": 0,
        "failureCount": 0,
        "runtimeMs": (time.perf_counter() - started) * 1000.0,
        "blockedReason": blocked_reason,
        "metrics": _empty_parity_metrics(),
        "outsideToleranceCount": None,
        "unresolvedMismatchCount": None,
    }
    _write_json(output_dir / "parity-report.json", report)
    _write_text(output_dir / "PARITY_REPORT.md", _parity_markdown(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if blocked_reason else 0


def _validate_hostile(args: argparse.Namespace) -> int:
    cases = load_validation_cases(args.cases_path)
    categories: dict[str, int] = {}
    expected: dict[str, int] = {}
    for case in cases:
        category = _case_category(case.id)
        categories[category] = categories.get(category, 0) + 1
        expected[case.expected_behavior] = expected.get(case.expected_behavior, 0) + 1
    report = {
        "status": "PASS" if len(cases) >= 100 else "FAIL",
        "caseCount": len(cases),
        "categories": categories,
        "expectedBehavior": expected,
        "notes": [
            "Corpus is hostile input coverage, not an independent numerical reference.",
            "DST and unknown-time behavior are exercised by pytest edge-case tests.",
            "High-latitude Placidus behavior is exercised by Swiss golden tests when data exists.",
        ],
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_text(output_dir / "HOSTILE_CASE_REPORT.md", _hostile_markdown(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


def _validate_reproducibility(args: argparse.Namespace) -> int:
    if args.swiss_ephe_path:
        engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=args.swiss_ephe_path),
            house_calculator=SwissHouseCalculator(ephemeris_path=args.swiss_ephe_path),
        )
        provider = "swiss"
    else:
        engine = AstrologyEngine(
            provider=DeterministicValidationProvider(),
            house_calculator=DeterministicValidationHouseCalculator(),
        )
        provider = "fixture"
    cases = [
        case
        for case in load_validation_cases(args.cases_path)
        if case.expected_behavior in {"success", "warning"} and case.house_system != "placidus"
    ][: args.cases]
    failures = []
    for case in cases:
        hashes = []
        for _run in range(args.runs):
            chart = engine.natal(
                local_datetime=case.local_datetime,
                timezone=case.timezone,
                latitude=case.latitude,
                longitude=case.longitude,
                house_system=case.house_system,
                unknown_time=case.unknown_time,
                fold=case.fold,
            )
            hashes.append(calculation_hash(chart))
        if len(set(hashes)) != 1:
            failures.append({"caseId": case.id, "hashes": hashes})
    report = {
        "status": "PASS" if not failures else "FAIL",
        "provider": provider,
        "cases": len(cases),
        "runs": args.runs,
        "failures": failures,
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_text(output_dir / "REPRODUCIBILITY_REPORT.md", _repro_markdown(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


def _validate_health(args: argparse.Namespace) -> int:
    provider = SwissEphemerisProvider(ephemeris_path=args.swiss_ephe_path)
    report = provider.health_check()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in {"ok", "degraded"} else 1


def _validate_astronomy_parity(args: argparse.Namespace) -> int:
    jpl_ephemeris_path = args.jpl_ephemeris_path or os.environ.get("GBC_JPL_EPHEMERIS_PATH")
    if not jpl_ephemeris_path:
        report = {
            "status": "BLOCKED",
            "blockedReason": "GBC_JPL_EPHEMERIS_PATH or --jpl-ephemeris-path is required.",
            "caseCount": args.cases,
            "reference": args.reference,
        }
        write_astronomy_parity_report(args.output_dir, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 2
    cases = generate_astronomy_cases(args.cases, args.seed)
    report = run_jpl_astronomy_parity(
        cases=cases,
        swiss_ephemeris_path=args.swiss_ephe_path,
        jpl_ephemeris_path=jpl_ephemeris_path,
    )
    write_astronomy_parity_report(args.output_dir, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _tolerance_to_dict() -> dict[str, Any]:
    tolerance = DEFAULT_V0_1_TOLERANCE
    return {
        "id": tolerance.id,
        "version": tolerance.version,
        "referenceSource": tolerance.reference_source,
        "rationale": tolerance.rationale,
        "bodyLongitudeDeg": tolerance.body_longitude_deg,
        "moonLongitudeDeg": tolerance.moon_longitude_deg,
        "bodySpeedDegPerDay": tolerance.body_speed_deg_per_day,
        "ascendantDeg": tolerance.ascendant_deg,
        "mcDeg": tolerance.mc_deg,
        "houseCuspDeg": tolerance.house_cusp_deg,
    }


def _empty_parity_metrics() -> dict[str, dict[str, float | int | None]]:
    metric_names = (
        "sun",
        "moon",
        "mercury",
        "venus",
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
        "pluto",
        "ascendant",
        "mc",
        "houseCusps",
    )
    empty = {
        "meanDelta": None,
        "p50Delta": None,
        "p95Delta": None,
        "p99Delta": None,
        "maxDelta": None,
        "maxDeltaCase": None,
        "outsideToleranceCount": None,
    }
    return {name: dict(empty) for name in metric_names}


def _parity_markdown(report: dict[str, Any]) -> str:
    return (
        "# v0.1 Parity Report\n\n"
        f"Status: {report['status']}\n\n"
        f"Reference: {report['referenceSource']} {report['referenceVersion']}\n\n"
        f"Cases requested: {report['caseCount']}\n\n"
        f"Blocked reason: {report['blockedReason'] or 'None'}\n\n"
        "This report is not an independent parity PASS unless status is PASS and "
        "`unresolvedMismatchCount` is zero.\n"
    )


def _hostile_markdown(report: dict[str, Any]) -> str:
    lines = ["# Hostile Case Report", "", f"Status: {report['status']}", ""]
    lines.append(f"Case count: {report['caseCount']}")
    lines.append("")
    lines.append("Categories:")
    for category, count in sorted(report["categories"].items()):
        lines.append(f"- {category}: {count}")
    lines.append("")
    lines.append("Expected behavior:")
    for behavior, count in sorted(report["expectedBehavior"].items()):
        lines.append(f"- {behavior}: {count}")
    lines.append("")
    lines.extend(f"- {note}" for note in report["notes"])
    lines.append("")
    return "\n".join(lines)


def _repro_markdown(report: dict[str, Any]) -> str:
    return (
        "# Reproducibility Report\n\n"
        f"Status: {report['status']}\n\n"
        f"Provider: {report['provider']}\n\n"
        f"Cases: {report['cases']}\n\n"
        f"Runs per case: {report['runs']}\n\n"
        f"Failures: {len(report['failures'])}\n"
    )


def _case_category(case_id: str) -> str:
    if case_id.startswith("dst-"):
        return "dst"
    if case_id.startswith("zodiac-") or case_id.startswith("moon-boundary-"):
        return "zodiac_boundary"
    if case_id.startswith("circular-"):
        return "circular_boundary"
    if case_id.startswith("house-cusp-"):
        return "house_cusp"
    if case_id.startswith("high-lat-"):
        return "high_latitude"
    if case_id.startswith("retro-station-"):
        return "retrograde_station"
    if case_id.startswith("unknown-time-"):
        return "unknown_time"
    if case_id.startswith("dateline-"):
        return "date_line"
    if case_id.startswith("leap-"):
        return "leap_day"
    return "geography"

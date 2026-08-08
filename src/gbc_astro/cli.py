"""Command line interface for the astrology engine."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from gbc_astro import ENGINE_VERSION, errors
from gbc_astro.engine import AstrologyEngine
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.models.relationship import (
    CompositeChart,
    DavisonChart,
    RelationshipScore,
    SynastryChart,
)
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
from gbc_astro.validation.ayanamsa import run_ayanamsa_parity
from gbc_astro.validation.chiron import (
    DEFAULT_FIXTURE_PATH as CHIRON_FIXTURE_PATH,
)
from gbc_astro.validation.chiron import (
    load_chiron_fixture,
    run_chiron_parity,
)
from gbc_astro.validation.corpus import load_validation_cases
from gbc_astro.validation.fixtures import (
    DeterministicValidationHouseCalculator,
    DeterministicValidationProvider,
)
from gbc_astro.validation.geometry_parity import (
    generate_geometry_cases,
    run_geometry_parity,
)
from gbc_astro.validation.houses_parity import (
    generate_house_cases,
    run_house_system_parity,
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

    for name, help_text in (
        ("synastry", "Cross aspects, house overlays and angle interactions for two charts."),
        ("composite", "Shortest-arc midpoint composite of two charts."),
        ("davison", "Real chart for the midpoint moment and place of two births."),
        ("compatibility", "Profile-scoped relationship score with full breakdown."),
    ):
        pair = subcommands.add_parser(name, help=help_text)
        for side in ("a", "b"):
            pair.add_argument(f"--{side}-date", required=True, help="Local date, YYYY-MM-DD.")
            pair.add_argument(f"--{side}-time", help="Local time, HH:MM[:SS].")
            pair.add_argument(f"--{side}-unknown-time", action="store_true")
            pair.add_argument(f"--{side}-timezone", required=True)
            pair.add_argument(f"--{side}-lat", type=float, required=True)
            pair.add_argument(f"--{side}-lng", type=float, required=True)
            pair.add_argument(f"--{side}-fold", type=int, choices=(0, 1))
        pair.add_argument("--house-system", default=WESTERN_MODERN_V1.house_system)
        pair.add_argument("--swiss-ephe-path")
        pair.add_argument("--json", action="store_true", help="Emit canonical JSON.")

    transits = subcommands.add_parser("transits", help="Transit snapshot against a natal chart.")
    _add_natal_arguments(transits)
    transits.add_argument("--at", required=True, help="UTC instant, ISO 8601.")
    transits.add_argument("--json", action="store_true")

    returns = subcommands.add_parser("returns", help="Every exact return in a window.")
    _add_natal_arguments(returns)
    returns.add_argument("--body", required=True)
    returns.add_argument("--from", dest="window_start", required=True, help="UTC ISO 8601.")
    returns.add_argument("--to", dest="window_end", required=True, help="UTC ISO 8601.")
    returns.add_argument("--charts", action="store_true", help="Cast a chart per hit.")
    returns.add_argument("--json", action="store_true")

    events = subcommands.add_parser("events", help="Ingress, station or exact-contact search.")
    events.add_argument(
        "--type",
        dest="event_type",
        required=True,
        choices=("sign_ingress", "station", "exact_longitude", "exact_aspect"),
    )
    events.add_argument("--body", required=True)
    events.add_argument("--from", dest="window_start", required=True, help="UTC ISO 8601.")
    events.add_argument("--to", dest="window_end", required=True, help="UTC ISO 8601.")
    events.add_argument("--target-longitude", type=float)
    events.add_argument("--aspect-angle", type=float)
    events.add_argument("--swiss-ephe-path")
    events.add_argument("--json", action="store_true")

    for name, help_text in (
        ("draconic", "Re-zero the zodiac on the lunar node."),
        ("harmonic", "The harmonic-n chart: every longitude multiplied by n."),
        ("progressions", "Secondary progressions: one day of motion per year of life."),
        ("solar-arc", "Direct every natal point by the progressed Sun's travel."),
    ):
        transform = subcommands.add_parser(name, help=help_text)
        _add_natal_arguments(transform)
        if name == "harmonic":
            transform.add_argument("--n", type=int, required=True, help="Harmonic number.")
        if name in {"progressions", "solar-arc"}:
            transform.add_argument("--at", required=True, help="Target instant, UTC ISO 8601.")
        transform.add_argument("--json", action="store_true")

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

    geometry = validate_subcommands.add_parser("geometry-parity")
    geometry.add_argument("--cases", type=int, default=500)
    geometry.add_argument("--seed", type=int, default=42)
    geometry.add_argument("--swiss-ephe-path")
    geometry.add_argument("--output-dir", default="evidence/v0.1-validation")

    house_systems = validate_subcommands.add_parser("house-systems")
    house_systems.add_argument("--cases", type=int, default=96)
    house_systems.add_argument("--swiss-ephe-path")
    house_systems.add_argument("--output-dir", default="evidence/v1.0-house-systems")

    ayanamsa = validate_subcommands.add_parser("ayanamsa-parity")
    ayanamsa.add_argument("--jpl-ephemeris-path")
    ayanamsa.add_argument("--swiss-ephe-path")
    ayanamsa.add_argument("--output-dir", default="evidence/v1.0-sidereal")

    chiron = validate_subcommands.add_parser("chiron-parity")
    chiron.add_argument("--fixture-path", default=CHIRON_FIXTURE_PATH)
    chiron.add_argument("--swiss-ephe-path")
    chiron.add_argument("--output-dir", default="evidence/v0.1-validation")

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


def _add_natal_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--date", required=True, help="Local birth date, YYYY-MM-DD.")
    parser.add_argument("--time", help="Local birth time, HH:MM[:SS].")
    parser.add_argument("--unknown-time", action="store_true")
    parser.add_argument("--timezone", required=True)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lng", type=float, required=True)
    parser.add_argument("--fold", type=int, choices=(0, 1))
    parser.add_argument("--house-system", default=WESTERN_MODERN_V1.house_system)
    parser.add_argument("--swiss-ephe-path")


def _engine_for(args: argparse.Namespace) -> AstrologyEngine:
    if args.swiss_ephe_path:
        return AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=args.swiss_ephe_path),
            house_calculator=SwissHouseCalculator(ephemeris_path=args.swiss_ephe_path),
        )
    return AstrologyEngine()


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _forecast(args: argparse.Namespace) -> int:
    engine = _engine_for(args)

    if args.command == "events":
        result: Any = engine.search_events(
            event_type=args.event_type,
            body=args.body,
            start=_utc(args.window_start),
            end=_utc(args.window_end),
            target_longitude=args.target_longitude,
            aspect_angle=args.aspect_angle,
        )
    else:
        natal = engine.natal(
            local_datetime=(
                args.date if args.unknown_time else f"{args.date}T{args.time}"
            ),
            timezone=args.timezone,
            latitude=args.lat,
            longitude=args.lng,
            house_system=args.house_system,
            unknown_time=args.unknown_time,
            fold=args.fold,
        )
        if args.command == "transits":
            result = engine.transits(natal, _utc(args.at))
        else:
            result = engine.returns(
                natal,
                args.body,
                _utc(args.window_start),
                _utc(args.window_end),
                include_charts=args.charts,
            )

    if args.json:
        print(result.to_json(indent=2))
    else:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


def _transform(args: argparse.Namespace) -> int:
    engine = _engine_for(args)
    chart = engine.natal(
        local_datetime=(args.date if args.unknown_time else f"{args.date}T{args.time}"),
        timezone=args.timezone,
        latitude=args.lat,
        longitude=args.lng,
        house_system=args.house_system,
        unknown_time=args.unknown_time,
        fold=args.fold,
    )
    if args.command == "draconic":
        result = engine.draconic(chart)
    elif args.command == "harmonic":
        result = engine.harmonic(chart, args.n)
    elif args.command == "progressions":
        result = engine.progressions(chart, _utc(args.at))
    else:
        result = engine.solar_arc(chart, _utc(args.at))
    if args.json:
        print(result.to_json(indent=2))
    else:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


def _relationship(args: argparse.Namespace) -> int:
    if args.swiss_ephe_path:
        engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=args.swiss_ephe_path),
            house_calculator=SwissHouseCalculator(ephemeris_path=args.swiss_ephe_path),
        )
    else:
        engine = AstrologyEngine()

    charts = [
        engine.natal(
            local_datetime=_pair_local_datetime(args, side),
            timezone=getattr(args, f"{side}_timezone"),
            latitude=getattr(args, f"{side}_lat"),
            longitude=getattr(args, f"{side}_lng"),
            house_system=args.house_system,
            unknown_time=getattr(args, f"{side}_unknown_time"),
            fold=getattr(args, f"{side}_fold"),
        )
        for side in ("a", "b")
    ]

    result: SynastryChart | CompositeChart | DavisonChart | RelationshipScore
    if args.command == "synastry":
        result = engine.synastry(*charts)
    elif args.command == "composite":
        result = engine.composite(*charts)
    elif args.command == "davison":
        result = engine.davison(*charts)
    else:
        result = engine.compatibility(*charts)
    if args.json:
        print(result.to_json(indent=2))
    else:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


def _pair_local_datetime(args: argparse.Namespace, side: str) -> str:
    date_value = getattr(args, f"{side}_date")
    time_value = getattr(args, f"{side}_time")
    if getattr(args, f"{side}_unknown_time"):
        return str(date_value)
    if not time_value:
        raise errors.UnknownBirthTimeError(
            f"--{side}-time is required unless --{side}-unknown-time is supplied.",
            {"date": date_value, "chart": side.upper()},
        )
    return f"{date_value}T{time_value}"


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
        if args.command in {"synastry", "composite", "davison", "compatibility"}:
            return _relationship(args)
        if args.command in {"transits", "returns", "events"}:
            return _forecast(args)
        if args.command in {"draconic", "harmonic", "progressions", "solar-arc"}:
            return _transform(args)
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
    if args.validate_command == "geometry-parity":
        return _validate_geometry_parity(args)
    if args.validate_command == "chiron-parity":
        return _validate_chiron_parity(args)
    if args.validate_command == "ayanamsa-parity":
        return _validate_ayanamsa_parity(args)
    if args.validate_command == "house-systems":
        return _validate_house_systems(args)
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
                "JPL reference source validates astronomy only. Run `validate "
                "astronomy-parity` for the JPL astronomy track and `validate "
                "geometry-parity` for the independent angle/Placidus track; this "
                "combined-fixture path still needs an external fixture set."
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
    # Deliberately not PARITY_REPORT.md: that file is the curated v0.1 gate
    # summary covering every track, and this command only knows about its own.
    _write_text(output_dir / "DIFFERENTIAL_REPORT.md", _parity_markdown(report))
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


def _validate_geometry_parity(args: argparse.Namespace) -> int:
    if args.swiss_ephe_path:
        os.environ["GBC_SWISS_EPHE_PATH"] = args.swiss_ephe_path
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    cases = generate_geometry_cases(args.cases, args.seed)
    report = run_geometry_parity(cases)
    report["seed"] = args.seed
    report["runtimeMs"] = (time.perf_counter() - started) * 1000.0

    _write_json(output_dir / "geometry-parity.json", report)
    _write_text(output_dir / "ANGLE_PARITY.md", _angle_parity_markdown(report))
    _write_text(output_dir / "PLACIDUS_PARITY.md", _placidus_parity_markdown(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


def _validate_house_systems(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = run_house_system_parity(
        cases=generate_house_cases(args.cases),
        swiss_ephemeris_path=args.swiss_ephe_path,
    )
    _write_json(output_dir / "house-systems.json", report)
    _write_text(output_dir / "HOUSE_SYSTEMS.md", _house_systems_markdown(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


def _house_systems_markdown(report: dict[str, Any]) -> str:
    absolute = [
        f"| {system} | {data['compared']} | {data['maxDeltaDeg'] * 3600.0:.5f} | "
        f"{data['outside']} |"
        for system, data in report["independentlyValidated"].items()
    ]
    catalogue = [
        f"| {profile['id']} | {profile['name']} | {profile['swissephCode']} | "
        f"{'yes' if profile['quadrantBased'] else 'no'} | "
        f"{'yes' if profile['definedAtAllLatitudes'] else 'no'} |"
        for profile in report["systems"].values()
    ]
    return "\n".join(
        (
            "# House Systems",
            "",
            f"Status: {report['status']}",
            "",
            f"Cases: {report['caseCount']}",
            f"Tolerance: {report['toleranceDeg']:.1e} deg",
            "",
            "## Supported systems",
            "",
            "| id | Name | Swiss code | Quadrant | Defined at all latitudes |",
            "|---|---|---|---|---|",
            *catalogue,
            "",
            "## Independently validated",
            "",
            "Re-derived from their definitions without Swiss Ephemeris, then compared.",
            "",
            "| System | Compared | Max delta (arcsec) | Outside tolerance |",
            "|---|---:|---:|---:|",
            *absolute,
            "",
            "## Structurally validated only",
            "",
            f"{', '.join(report['structurallyValidatedOnly'])}",
            "",
            "No independent reference exists for these in this engine. Calling them",
            "validated because Swiss Ephemeris produced them would be validating a",
            "thing against itself, so they are held to invariants instead: twelve",
            "cusps in zodiacal order closing the circle, cusp 1 on the Ascendant and",
            "cusp 10 on the Midheaven for quadrant systems, axial symmetry, and every",
            "longitude landing in exactly one house.",
            "",
            f"Invariant violations: "
            f"{sum(len(d['failures']) for d in report['structural'].values())}",
            "",
            "## Polar behaviour",
            "",
            f"Refusals (undefined beyond the polar circles): {report['polarRefusals']}",
            "",
            f"Degenerate sequences, flagged: {report['degenerateSequences']}",
            "",
            f"Unexpected degeneracy inside the polar circles: "
            f"{len(report['unexpectedDegeneracy'])}",
            "",
            "Placidus and Koch have no solution beyond the polar circles and are",
            "refused there. Campanus, Regiomontanus and Topocentric do not refuse --",
            "they invert, returning cusps that run backwards. That is what the",
            "geometry does, so the chart is returned with a HOUSE_SEQUENCE_DEGENERATE",
            "warning rather than presented as ordinary. Degeneracy inside the polar",
            "circles would be a defect and fails this gate.",
            "",
            "## Notes",
            "",
            *[f"- {note}" for note in report["notes"]],
            "",
        )
    )


def _validate_ayanamsa_parity(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = run_ayanamsa_parity(
        jpl_ephemeris_path=args.jpl_ephemeris_path,
        swiss_ephemeris_path=args.swiss_ephe_path,
    )
    _write_json(output_dir / "ayanamsa-parity.json", report)
    _write_text(output_dir / "AYANAMSA_PARITY.md", _ayanamsa_parity_markdown(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


def _ayanamsa_parity_markdown(report: dict[str, Any]) -> str:
    reference = report["reference"]
    rows = [
        f"| {c['utc'][:10]} | {c['spicaLongitudeDeg']:.6f} | {c['referenceAyanamsaDeg']:.6f} "
        f"| {c['engineAyanamsaDeg']:.6f} | {c['deltaArcsec']:.3f} |"
        for c in report["trueCitraComparisons"]
    ]
    drift = [
        f"| {d['ayanamsa']} | {d['arcsecPerYear']:.4f} | "
        f"{'PASS' if d['withinTolerance'] else 'FAIL'} |"
        for d in report["precessionDrift"]
    ]
    return "\n".join(
        (
            "# Ayanamsa Parity",
            "",
            f"Status: {report['status']}",
            "",
            f"Reference: `{reference['id']}` -- {reference['star']} (HIP {reference['hip']})",
            f"Catalogue: {reference['catalogue']}",
            f"Frame: {reference['frame']}",
            "",
            "## True Chitrapaksha against Spica",
            "",
            "The only ayanamsa with an observable definition, and therefore the only",
            "one that can be validated absolutely rather than structurally.",
            "",
            "| Epoch | Spica longitude | Reference ayanamsa | Engine | Delta (arcsec) |",
            "|---|---:|---:|---:|---:|",
            *rows,
            "",
            f"Max delta: {report['trueCitraMaxDeltaArcsec']:.3f} arcsec "
            f"(tolerance {report['tolerance']['trueCitraArcsec']:.0f})",
            f"Outside tolerance: {report['outsideToleranceCount']}",
            "",
            "## Precession drift",
            "",
            "Every ayanamsa must advance at the rate of general precession, because",
            "that is what an ayanamsa is. IAU 2006 general precession in longitude is",
            f"{report['tolerance'].get('expected', 50.2877)} arcsec/year.",
            "",
            "| Ayanamsa | Measured (arcsec/yr) | Result |",
            "|---|---:|---|",
            *drift,
            "",
            "## Notes",
            "",
            *[f"- {note}" for note in report["notes"]],
            "",
            f"Tolerance rationale: {report['tolerance']['rationale']}",
            "",
        )
    )


def _validate_chiron_parity(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fixture = load_chiron_fixture(args.fixture_path)
    report = run_chiron_parity(fixture, swiss_ephemeris_path=args.swiss_ephe_path)

    _write_json(output_dir / "chiron-parity.json", report)
    _write_text(output_dir / "CHIRON_PARITY.md", _chiron_parity_markdown(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


def _chiron_parity_markdown(report: dict[str, Any]) -> str:
    reference = report["reference"]
    date_range = report.get("range") or {}
    return "\n".join(
        (
            "# Chiron Parity",
            "",
            f"Status: {report['status']}",
            "",
            f"Reference: `{reference['id']}` -- {reference['source']}, {reference['target']}",
            f"Frame: {reference['frame']}",
            f"Captured: {reference['capturedAt']}",
            "",
            f"Samples: {report['sampleCount']}",
            f"Range: {date_range.get('start', '?')} to {date_range.get('stop', '?')}",
            "",
            "| Metric | p95 (deg) | max (deg) | max (arcsec) | tolerance (deg) |",
            "|---|---:|---:|---:|---:|",
            f"| Longitude | {report['longitude']['p95Deg']:.3e} | "
            f"{report['longitude']['maxDeg']:.3e} | {report['longitude']['maxArcsec']:.4f} | "
            f"{report['tolerance']['longitudeDeg']:.1e} |",
            f"| Latitude | {report['latitude']['p95Deg']:.3e} | "
            f"{report['latitude']['maxDeg']:.3e} | {report['latitude']['maxArcsec']:.4f} | "
            f"{report['tolerance']['latitudeDeg']:.1e} |",
            "",
            f"Outside tolerance: {report['outsideToleranceCount']}",
            "",
            "## Why a frozen fixture",
            "",
            "DE440S contains only the major planets, so the JPL track that validates",
            "Sun through Pluto cannot reach Chiron. JPL Horizons publishes its own",
            "small-body orbit solution for 2060 Chiron, independent of the Swiss",
            "`seas_18.se1` integration under validation.",
            "",
            "The samples are committed and read offline, so this gate is deterministic",
            "and needs no network access in CI. Regenerate with",
            "`python tools/fetch_chiron_horizons.py`.",
            "",
            f"Tolerance rationale: {report['tolerance']['rationale']}",
            "",
        )
    )


def _angle_parity_markdown(report: dict[str, Any]) -> str:
    reference = report["reference"]
    ascendant = report["ascendant"]
    midheaven = report["midheaven"]
    return "\n".join(
        (
            "# Angle Parity",
            "",
            f"Status: {report['status']}",
            "",
            f"Reference: `{reference['id']}` {reference['version']} ({reference['method']})",
            "",
            f"Cases compared: {report['comparedCount']} of {report['caseCount']}",
            "",
            "| Angle | p95 (deg) | max (deg) | max (arcsec) | tolerance (deg) | outside |",
            "|---|---:|---:|---:|---:|---:|",
            _angle_row("Ascendant", ascendant),
            _angle_row("MC", midheaven),
            "",
            "DSC and IC are the opposing points of ASC and MC in both implementations,",
            "so they carry the same deltas and are not reported separately.",
            "",
            "## Method",
            "",
            "The reference derives sidereal time and true obliquity from Skyfield and",
            "solves the defining spherical condition for each angle numerically. It shares",
            "no code with Swiss Ephemeris, which satisfies the independence requirement in",
            "`docs/HOUSE_REFERENCE_METHODOLOGY.md`.",
            "",
            f"Tolerance rationale: {report['tolerance']['rationale']}",
            "",
        )
    )


def _placidus_parity_markdown(report: dict[str, Any]) -> str:
    reference = report["reference"]
    cusps = report["houseCusps"]
    return "\n".join(
        (
            "# Placidus Parity",
            "",
            f"Status: {report['status']}",
            "",
            f"Reference: `{reference['id']}` {reference['version']} ({reference['method']})",
            "",
            f"Cases compared: {report['comparedCount']} of {report['caseCount']}",
            f"Cusp comparisons: {cusps['cases']}",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Cusp p95 delta (deg) | {cusps['p95Deg']:.3e} |",
            f"| Cusp max delta (deg) | {cusps['maxDeg']:.3e} |",
            f"| Cusp max delta (arcsec) | {cusps['maxDeg'] * 3600.0:.6f} |",
            f"| Tolerance (deg) | {cusps['toleranceDeg']:.1e} |",
            f"| Outside tolerance | {cusps['outsideToleranceCount']} |",
            f"| House assignment mismatches | {report['houseAssignmentMismatchCount']} |",
            f"| Undefined, both sides agree (excluded) | {report['agreedUndefinedCount']} |",
            f"| Convention differences (engine stricter) | {report['conventionDifferenceCount']} |",
            f"| Undefined-branch disagreements | {report['disagreementCount']} |",
            f"| Time-resolution errors | {report['timeErrorCount']} |",
            "",
            "## Undefined Placidus cases",
            "",
            "Beyond the polar circles the semi-diurnal arc does not exist for part of the",
            "ecliptic and Placidus has no solution. Such cases are excluded from the",
            "statistics above and are never compared against a substitute house system,",
            "as `docs/HOUSE_REFERENCE_METHODOLOGY.md` requires.",
            "",
            "Exclusion is not taken on trust. Each case is cross-checked both ways: the",
            "engine must refuse with a structured error exactly where the independent",
            "reference finds no solution. A case where either side produced cusps while",
            "the other could not is counted as a disagreement and fails the gate -- that",
            "is how a silent fallback to a different house system would surface.",
            "",
            f"Agreed undefined: {report['agreedUndefinedCount']} case(s).",
            f"Disagreements: {report['disagreementCount']} case(s).",
            "",
            "### Convention difference at the polar circles",
            "",
            f"Recorded: {report['conventionDifferenceCount']} case(s).",
            "",
            "Swiss Ephemeris declines Placidus categorically for any latitude beyond the",
            "polar circles, whereas the reference declines per case and can still solve",
            "some of them. Probed directly at 69.65 N: `houses_ex(..., b\"P\")` raises while",
            "`b\"O\"` (Porphyry) returns values, so the engine is refusing rather than",
            "substituting a different house system. Declining more often than strictly",
            "necessary cannot yield a wrong chart, so these are recorded as a convention",
            "difference in the safe direction and do not fail the gate. The opposite",
            "direction -- cusps emitted where Placidus has no solution -- is counted as a",
            "disagreement and does fail it.",
            "",
            "## House assignment",
            "",
            "Every body in every compared chart was re-assigned to a house using the",
            "independently derived cusps and checked against the engine's assignment.",
            f"Mismatches: {report['houseAssignmentMismatchCount']}.",
            "",
            f"Tolerance rationale: {report['tolerance']['rationale']}",
            "",
        )
    )


def _angle_row(label: str, metrics: dict[str, Any]) -> str:
    return (
        f"| {label} | {metrics['p95Deg']:.3e} | {metrics['maxDeg']:.3e} | "
        f"{metrics['maxDeg'] * 3600.0:.6f} | {metrics['toleranceDeg']:.1e} | "
        f"{metrics['outsideToleranceCount']} |"
    )


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

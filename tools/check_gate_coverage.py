#!/usr/bin/env python3
"""Fail if any `gbc validate` subcommand is not run by a CI workflow.

A gate nobody runs is not a gate. This has already happened twice in this
repository: the v0.1 differential swallowed its own BLOCKED exit code, and the
house-system and ayanamsa gates shipped without a workflow step. Rather than
rely on remembering, the check is mechanical.
"""

from __future__ import annotations

import pathlib
import re
import sys

# Gates that are deliberately not run in CI, with the reason.
EXEMPT = {
    "health": "a diagnostic, not a gate",
    "differential": "superseded by the astronomy and geometry tracks",
}


def declared_gates() -> set[str]:
    import gbc_astro.cli as cli

    parser = cli._build_parser()
    validate = parser._subparsers._group_actions[0].choices["validate"]
    return set(validate._subparsers._group_actions[0].choices)


def gates_run_by_ci() -> set[str]:
    found: set[str] = set()
    for workflow in pathlib.Path(".github/workflows").glob("*.yml"):
        for match in re.finditer(r"gbc validate ([a-z-]+)", workflow.read_text()):
            found.add(match.group(1))
    return found


def main() -> int:
    declared = declared_gates()
    covered = gates_run_by_ci() | set(EXEMPT)
    missing = sorted(declared - covered)

    for gate in missing:
        print(f"::error::validation gate '{gate}' is declared but no workflow runs it")
    if missing:
        return 1

    print(f"All {len(declared)} declared gates are covered or exempt.")
    for gate, reason in sorted(EXEMPT.items()):
        print(f"  exempt: {gate} ({reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

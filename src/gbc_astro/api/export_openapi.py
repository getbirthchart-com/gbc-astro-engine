"""Export a deterministic OpenAPI snapshot for frontend type generation.

Usage:

    python -m gbc_astro.api.export_openapi
    python -m gbc_astro.api.export_openapi --output openapi/gbc-astro-v1.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gbc_astro.api.app import create_app
from gbc_astro.api.dependencies import API_VERSION
from gbc_astro.constants import ENGINE_VERSION


def export_openapi(output: Path) -> Path:
    app = create_app()
    schema = app.openapi()
    schema.setdefault("info", {})
    schema["info"]["x-gbc-engine-version"] = ENGINE_VERSION
    schema["info"]["x-gbc-api-version"] = API_VERSION
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export gbc-astro OpenAPI snapshot.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("openapi/gbc-astro-v1.json"),
        help="Output JSON path (default: openapi/gbc-astro-v1.json)",
    )
    args = parser.parse_args(argv)
    path = export_openapi(args.output)
    print(f"Wrote OpenAPI snapshot to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

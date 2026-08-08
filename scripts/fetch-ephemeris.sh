#!/usr/bin/env bash
# Provision ephemeris data for a deployment.
#
# These files are not committed and not baked into the image: Swiss Ephemeris
# data and JPL kernels carry redistribution terms. Run this once per host, or
# as a deploy step that writes into a mounted volume.
#
#   ./scripts/fetch-ephemeris.sh [target-dir]   (default: ./ephemeris)
#
# Swiss files cover 1800-2399, which contains the v0.1 production range of
# 1900-2026. The JPL kernel is only needed to run the validation gates, not to
# serve charts, and is skipped unless --with-jpl is passed.

set -euo pipefail

TARGET="${1:-./ephemeris}"
WITH_JPL="${WITH_JPL:-0}"
[[ "${2:-}" == "--with-jpl" || "${1:-}" == "--with-jpl" ]] && WITH_JPL=1
[[ "${1:-}" == "--with-jpl" ]] && TARGET="./ephemeris"

SWISS_BASE="https://raw.githubusercontent.com/aloistr/swisseph/master/ephe"
JPL_URL="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp"

mkdir -p "$TARGET/swiss"
for file in sepl_18.se1 semo_18.se1 seas_18.se1; do
  if [[ -s "$TARGET/swiss/$file" ]]; then
    echo "have    $file"
  else
    echo "fetch   $file"
    curl -fsSL -o "$TARGET/swiss/$file" "$SWISS_BASE/$file"
  fi
done

if [[ "$WITH_JPL" == "1" ]]; then
  mkdir -p "$TARGET/jpl"
  if [[ -s "$TARGET/jpl/de440s.bsp" ]]; then
    echo "have    de440s.bsp"
  else
    echo "fetch   de440s.bsp (~32MB)"
    curl -fsSL -o "$TARGET/jpl/de440s.bsp" "$JPL_URL"
  fi
fi

echo
echo "Provisioned into $TARGET:"
find "$TARGET" -type f -exec ls -lh {} \; | awk '{print "  " $9 "  " $5}'
echo
echo "Point the engine at it:"
echo "  export GBC_SWISS_EPHE_PATH=$(cd "$TARGET" && pwd)/swiss"

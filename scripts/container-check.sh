#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# Compose verlangt den internen Bridge-Token bereits beim Parsen. Die isolierten
# Regressionen starten kein DB-Backend und brauchen deshalb nur einen Testwert.
export DB_CFFI_TOKEN="${DB_CFFI_TOKEN:-0000000000000000000000000000000000000000000000000000000000000000}"

trap 'printf "\nCONTAINER-TEST ABGEBROCHEN\n" >&2; exit 130' INT TERM

docker compose run --rm --no-deps \
  -v "$ROOT:/source:ro" \
  -e SOURCE_ROOT=/source \
  app sh -lc '
    set -eu
    export PYTHONPATH=/source/tool
    for f in /source/tests/test_*.py; do
      echo "--- $(basename "$f")"
      python "$f"
    done
    python - <<"PY"
import reisevergleich.api, reisevergleich.service, reisevergleich.presentation
print("Produktionsimporte: OK")
PY
  '

echo
printf '%s\n' 'CONTAINER-CHECK: OK'

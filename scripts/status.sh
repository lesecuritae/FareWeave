#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo '=== Container ==='
docker compose ps
echo
echo '=== Backend ==='
curl -fsS http://127.0.0.1:8791/api/health | python3 -m json.tool
echo
echo '=== Diagnostik ==='
curl -fsS --max-time 90 http://127.0.0.1:8791/api/diagnostics | python3 -m json.tool

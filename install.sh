#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
trap 'printf "\nINSTALLATION ABGEBROCHEN\n" >&2; exit 130' INT TERM

die(){ printf 'FEHLER: %s\n' "$*" >&2; exit 1; }
say(){ printf '\n=== %s ===\n' "$1"; }

command -v docker >/dev/null 2>&1 || die "Docker fehlt."
docker compose version >/dev/null 2>&1 || die "Docker Compose Plugin fehlt."

if [[ ! -f .env ]]; then
  say "Konfiguration anlegen"
  cp .env.example .env
  if command -v openssl >/dev/null 2>&1; then
    token="$(openssl rand -hex 32)"
  elif command -v python3 >/dev/null 2>&1; then
    token="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
  else
    token="$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')"
  fi
  [[ "$token" =~ ^[0-9a-fA-F]{64}$ ]] || die "Sicherer DB_CFFI_TOKEN konnte nicht erzeugt werden."
  sed -i "s/^DB_CFFI_TOKEN=.*/DB_CFFI_TOKEN=$token/" .env
  chmod 600 .env
  echo ".env wurde mit zufälligem internem Bridge-Token angelegt."
else
  echo "Bestehende .env wird unverändert verwendet."
fi

if grep -Eq '^DB_CFFI_TOKEN=(CHANGE_ME)?$' .env; then
  die "DB_CFFI_TOKEN in .env ist nicht gesetzt."
fi

say "Compose prüfen"
docker compose config -q

action_log="${TMPDIR:-/tmp}/fareweave-install-$$.log"
cleanup(){ rm -f "$action_log"; }
trap cleanup EXIT

run(){
  local label="$1"; shift
  printf '%-52s' "$label"
  if "$@" >"$action_log" 2>&1; then
    echo "OK"
  else
    echo "FEHLER"
    tail -n 120 "$action_log" >&2 || true
    exit 1
  fi
}

run "Veröffentlichte Images laden" docker compose pull
run "Dienste starten" docker compose up -d --no-build --remove-orphans

printf '%-52s' "Healthcheck"
ok=0
for _ in $(seq 1 45); do
  if docker compose exec -T app python - <<'PY' >/dev/null 2>&1
import json
from urllib.request import urlopen
with urlopen("http://127.0.0.1:8000/api/health", timeout=3) as response:
    data=json.load(response)
assert data.get("status") == "ok", data
PY
  then
    ok=1
    break
  fi
  sleep 2
done
[[ "$ok" -eq 1 ]] || { echo "FEHLER"; docker compose logs --no-color --tail=120 app db-api >&2 || true; exit 1; }
echo "OK"

bind_host="$(sed -n 's/^FAREWEAVE_BIND_HOST=//p' .env | tail -n1)"
port="$(sed -n 's/^FAREWEAVE_PORT=//p' .env | tail -n1)"
bind_host="${bind_host:-127.0.0.1}"
port="${port:-8791}"

echo
printf '%s\n' 'FAREWEAVE: INSTALLATION OK'
printf 'UI: http://%s:%s\n' "$bind_host" "$port"
printf 'Health: http://%s:%s/api/health\n' "$bind_host" "$port"

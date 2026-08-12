from pathlib import Path
import os

root = Path(os.environ.get("SOURCE_ROOT", Path(__file__).resolve().parents[1]))
compose = (root / "compose.yml").read_text(encoding="utf-8")
env_example = (root / ".env.example").read_text(encoding="utf-8")
third_party = (root / "THIRD_PARTY.md").read_text(encoding="utf-8")
check = (root / "scripts" / "check.sh").read_text(encoding="utf-8")
container_check = (root / "scripts" / "container-check.sh").read_text(encoding="utf-8")
installer = root / "install.sh"
license_file = root / "LICENSE"

assert installer.is_file(), "install.sh fehlt"
assert license_file.is_file(), "LICENSE fehlt"
assert "MIT License" in license_file.read_text(encoding="utf-8")
assert 'STAY22_API_KEY: ${STAY22_API_KEY:-}' in compose
assert '${FAREWEAVE_BIND_HOST:-127.0.0.1}:${FAREWEAVE_PORT:-8791}:8000' in compose
assert '0.0.0.0:8791:8000' not in compose
assert 'fareweave-state:/var/lib/reisevergleich' in compose
assert '${DB_CFFI_TOKEN:?DB_CFFI_TOKEN in .env setzen}' in compose
assert "DB_CFFI_TOKEN=CHANGE_ME" in env_example
assert "STAY22_API_KEY=" in env_example
assert "PolyForm Noncommercial License 1.0.0" in third_party
assert "Required Notice" in third_party
assert "ISC License" in third_party
assert "curl_cffi" in check.split('if python3 -c', 1)[1].split('then', 1)[0]
assert '-v "$ROOT:/source:ro"' in container_check
assert 'export DB_CFFI_TOKEN="${DB_CFFI_TOKEN:-' in container_check, (
    "container-check.sh muss aus einem frischen Archiv ohne .env lauffaehig sein"
)

for forbidden in ("192.168.", "10.0.", "tailscale", "CHANGE_ME="):
    assert forbidden not in compose

print("GitHub-Paketvertrag, sichere Defaults und Lizenzhinweise: OK")

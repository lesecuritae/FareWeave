from pathlib import Path
import os

root = Path(os.environ.get("SOURCE_ROOT", Path(__file__).resolve().parents[1]))
dockerfile = (root / "tool" / "Dockerfile").read_text()
compose = (root / "compose.yml").read_text()
third_party = (root / "THIRD_PARTY.md").read_text()

assert "ARG TRVL_REF=v1.21.3" in dockerfile
assert 'TRVL_VERSION="${TRVL_REF#v}"' in dockerfile
assert "main.Version=${TRVL_VERSION}" in dockerfile
assert 'grep -F "trvl ${TRVL_VERSION}"' in dockerfile
assert "main.Version=1.21.3" not in dockerfile
for contract in ("trvl hotels --help", '"--enrich-rooms"', "trvl flights --help", "trvl ground --help"):
    assert contract in dockerfile
assert "TRVL_REF: ${TRVL_REF:-v1.21.3}" in compose
assert "Tag `v1.21.3`" in third_party

print("trvl-Version ist einstellbar und CLI-Verträge werden beim Build geprüft: OK")

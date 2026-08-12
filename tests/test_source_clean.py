from pathlib import Path
import os

root = Path(os.environ.get("SOURCE_ROOT", Path(__file__).resolve().parents[1]))
decode = lambda value: bytes.fromhex(value).decode("utf-8")
forbidden = {
    decode("4f70656e5765625549"): "entfernte Oberfläche",
    decode("4c4c4d"): "entfernte Laufzeitklasse",
    decode("50726f6d7074"): "entfernte Texteingabeschicht",
    decode("4b492d66726569"): "historischer Abgrenzungstext",
    decode("61695f7265717569726564"): "entferntes Health-Kompatibilitätsfeld",
    "request_" + "text": "freie Texteingabe",
    "Reise" + "Assistent": "alter Werkzeugvertrag",
    "response_" + "instruction": "alte Antwortregeln",
    "TOOL_" + "API_KEY": "alter Werkzeugtoken",
    "BETTER" + "BAHN_URL": "alte Laufzeitkopplung",
}
text_suffixes = {".py", ".js", ".html", ".css", ".mjs", ".sh", ".md", ".yml", ".yaml", ".txt", ".example"}
text_names = {"Dockerfile", ".dockerignore", ".gitignore"}
paths = []
for base in (root / "tool", root / "db-api", root / "scripts", root / "tests"):
    paths.extend(path for path in base.rglob("*") if path.is_file() and (path.suffix in text_suffixes or path.name in text_names))
paths.extend([root / "README.md", root / "compose.yml", root / ".env.example"])
for path in paths:
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8")
    for needle, label in forbidden.items():
        assert needle not in text, f"{label} noch in {path}: {needle}"
print("Altlastenprüfung: OK")


# Laufzeit-Namensfehler wie ein versehentlich stehen gebliebenes variables
# aus einer alten API-Idee müssen bereits statisch auffallen. symtable erkennt
# globale Referenzen in verschachtelten Funktionen, die weder importiert noch
# auf Modulebene definiert noch Python-Builtins sind.
import builtins
import symtable

builtin_names = set(dir(builtins))
undefined_globals = []
for path in sorted((root / "tool" / "reisevergleich").rglob("*.py")):
    table = symtable.symtable(path.read_text(encoding="utf-8"), str(path), "exec")
    module_defined = {
        symbol.get_name()
        for symbol in table.get_symbols()
        if symbol.is_assigned() or symbol.is_imported() or symbol.is_parameter() or symbol.is_namespace()
    }

    def walk(scope):
        for symbol in scope.get_symbols():
            if (
                symbol.is_referenced()
                and symbol.is_global()
                and symbol.get_name() not in module_defined
                and symbol.get_name() not in builtin_names
            ):
                undefined_globals.append((str(path.relative_to(root)), scope.get_name(), symbol.get_name()))
        for child in scope.get_children():
            walk(child)

    walk(table)

assert not undefined_globals, f"Undefinierte Laufzeitnamen: {undefined_globals}"
print("Statische Laufzeit-Namensprüfung: OK")

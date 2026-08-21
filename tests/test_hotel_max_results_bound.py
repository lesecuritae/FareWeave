"""TripRequest.max_results darf nicht ungebremst in HotelRequest.max_results laufen.

Ohne Begrenzung wirft pydantic beim Bauen des HotelRequest einen ValidationError,
der bis in den Request-Handler durchschlägt: jede Flug-Suche mit Hotel endet dann in
HTTP 500. Die UI sendet fest max_results=24, der Fall ist also der Normalfall.
"""

import ast
import os
from pathlib import Path

from reisevergleich.models import HotelRequest, TripRequest

root = Path(os.environ.get("SOURCE_ROOT", Path(__file__).resolve().parents[1]))


def field_bound(model, name):
    return next(rule.le for rule in model.model_fields[name].metadata if hasattr(rule, "le"))


hotel_bound = field_bound(HotelRequest, "max_results")
trip_bound = field_bound(TripRequest, "max_results")
assert trip_bound > hotel_bound, "Nur bei unterschiedlichen Grenzen ist die Begrenzung nötig"
assert TripRequest(
    origin="Berlin", destination="Barcelona", departure_date="2030-09-15"
).max_results > hotel_bound, "Der TripRequest-Default liegt bereits über der Hotelgrenze"


def hotel_max_results_expression() -> ast.expr:
    """Der Ausdruck, den planner.py als max_results an HotelRequest übergibt."""
    tree = ast.parse((root / "tool" / "reisevergleich" / "planner.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if not (isinstance(target, ast.Name) and target.id == "HotelRequest"):
            continue
        for keyword in node.keywords:
            if keyword.arg == "max_results":
                return keyword.value
    raise AssertionError("Kein HotelRequest(max_results=...) in planner.py gefunden")


expression = compile(ast.Expression(hotel_max_results_expression()), "<planner>", "eval")


class FakeRequest:
    def __init__(self, max_results):
        self.max_results = max_results


# Jeder von TripRequest erlaubte Wert muss zu einem gültigen HotelRequest führen.
# Der Test prüft damit die Eigenschaft, nicht eine bestimmte Schreibweise: eine
# spätere Umformulierung der Begrenzung bleibt grün, ein Wegfall nicht.
for value in (1, 6, hotel_bound, hotel_bound + 1, 24, trip_bound):
    resolved = eval(expression, {}, {"request": FakeRequest(value)})
    assert resolved <= hotel_bound, (
        f"planner.py würde HotelRequest(max_results={resolved}) bauen, "
        f"erlaubt sind höchstens {hotel_bound} (TripRequest.max_results={value})"
    )
    HotelRequest(
        location="Barcelona",
        checkin_date="2030-09-15",
        checkout_date="2030-09-18",
        max_results=resolved,
    )

# Kleinere Wünsche bleiben unangetastet.
assert eval(expression, {}, {"request": FakeRequest(4)}) == 4

print("Hotel-max_results bleibt innerhalb der HotelRequest-Grenze: OK")

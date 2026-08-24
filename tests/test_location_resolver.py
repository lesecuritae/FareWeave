import asyncio

from reisevergleich import db
from reisevergleich.airports import provider_location_query
from reisevergleich.gtfs_flix import stop_score
from reisevergleich.location_resolver import has_airport_context, location_candidates, location_match_is_safe


def test_exact_station_names_are_first_and_never_airports():
    assert location_candidates("Leipzig Hbf")[0] == "Leipzig Hbf"
    assert location_candidates("Frankfurt(Main) Hbf")[0] == "Frankfurt(Main) Hbf"
    assert provider_location_query("Leipzig Hbf") == "Leipzig Hbf"
    assert provider_location_query("Frankfurt(Main) Hbf") == "Frankfurt(Main) Hbf"
    assert not has_airport_context("Frankfurt(Main) Hbf")


def test_international_city_aliases_are_fallbacks_only():
    assert location_candidates("München") == ("München", "munich")
    assert location_candidates("Muenchen") == ("Muenchen", "munich")
    assert location_candidates("Munich") == ("Munich",)
    assert location_candidates("Köln") == ("Köln", "cologne")
    assert location_candidates("Koeln") == ("Koeln", "cologne")
    assert location_candidates("Wien") == ("Wien", "vienna")
    assert location_candidates("Vienna") == ("Vienna",)
    assert location_candidates("Prag") == ("Prag", "prague")
    assert location_candidates("Mailand") == ("Mailand", "milan")
    assert location_candidates("Rom") == ("Rom", "rome")
    assert all("hbf" not in candidate.casefold() for value in ("München", "Köln", "Wien") for candidate in location_candidates(value))
    assert not location_match_is_safe("Vienna", "Vienna, Virginia")
    assert location_match_is_safe("Vienna", "Wien Hbf")


def test_airport_aliases_require_airport_context():
    assert provider_location_query("Leipzig Flughafen") == "Leipzig Halle Flughafen"
    assert provider_location_query("Frankfurt Airport") == "Frankfurt Flughafen"
    assert provider_location_query("FRA") == "Frankfurt Flughafen"
    assert has_airport_context("FRA")
    assert has_airport_context("Frankfurt(Main)Flugh")
    assert has_airport_context("Görlitz Flugplatz")


def test_flix_prefers_exact_stop_before_translated_alias():
    assert stop_score("München Hbf", "München Hbf") > stop_score("München Hbf", "Munich Hbf")
    assert stop_score("München Hbf", "München Hbf") > stop_score("München Hbf", "Munchen Hbf")
    assert stop_score("Rom", "Rome Tiburtina Bus station") > stop_score("Rom", "Lyngdal (Rom terminal)")
    assert stop_score("Prag", "Prague Florenc") > stop_score("Prag", "Prague Václav Havel Airport")


def test_db_uses_alias_only_after_exact_lookup_is_empty(monkeypatch):
    seen = []

    async def fake_search(**kwargs):
        seen.append((kwargs["origin"], kwargs["destination"]))
        return ({"journeys": [{"id": "found"}], "origin": {"name": "München Hbf"}, "destination": {"name": "Berlin Hbf"}}
                if kwargs["origin"] == "munich" else {"journeys": []})

    monkeypatch.setattr(db, "db_search", fake_search)
    result, _ = asyncio.run(db.db_search_with_retry(
        origin="München", destination="Berlin", travel_date="2030-10-27",
        departure_after="03:00", mode="all", max_transfers=None, results=10,
    ))
    assert seen == [("München", "Berlin"), ("munich", "Berlin")]
    assert result["journeys"][0]["id"] == "found"

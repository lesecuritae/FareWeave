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
    assert location_candidates("München")[:2] == ("München", "München Hbf")
    assert location_candidates("Muenchen")[:2] == ("Muenchen", "München Hbf")
    assert location_candidates("Munchen")[:2] == ("Munchen", "München Hbf")
    assert location_candidates("Köln")[:2] == ("Köln", "Köln Hbf")
    assert location_candidates("Koeln")[:2] == ("Koeln", "Köln Hbf")
    assert location_candidates("Koln")[:2] == ("Koln", "Köln Hbf")
    assert location_candidates("Wien")[:2] == ("Wien", "Wien Hbf")
    assert location_candidates("Zürich")[:2] == ("Zürich", "Zürich HB")
    assert location_candidates("Zuerich")[:2] == ("Zuerich", "Zürich HB")
    assert location_candidates("Zurich")[:2] == ("Zurich", "Zürich HB")
    assert location_candidates("Munich")[:2] == ("Munich", "München Hbf")
    assert location_candidates("Cologne")[:2] == ("Cologne", "Köln Hbf")
    assert location_candidates("Vienna")[:2] == ("Vienna", "Wien Hbf")
    assert location_candidates("Prag")[:2] == ("Prag", "Praha hlavní nádraží")
    assert location_candidates("Prague")[:2] == ("Prague", "Praha hlavní nádraží")
    assert location_candidates("Mailand")[:2] == ("Mailand", "Milano Centrale")
    assert location_candidates("Milan")[:2] == ("Milan", "Milano Centrale")
    assert location_candidates("Rom")[:2] == ("Rom", "Roma Termini")
    assert location_candidates("Rome")[:2] == ("Rome", "Roma Termini")
    assert not location_match_is_safe("Vienna", "Vienna, Virginia")
    assert location_match_is_safe("Vienna", "Wien Hbf")


def test_airport_aliases_require_airport_context():
    assert provider_location_query("Leipzig Flughafen") == "Leipzig Halle Flughafen"
    assert provider_location_query("Frankfurt Airport") == "Frankfurt Flughafen"
    assert provider_location_query("FRA") == "Frankfurt Flughafen"
    assert has_airport_context("FRA")


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
                if kwargs["origin"] == "München Hbf" else {"journeys": []})

    monkeypatch.setattr(db, "db_search", fake_search)
    result, _ = asyncio.run(db.db_search_with_retry(
        origin="München", destination="Berlin", travel_date="2030-10-27",
        departure_after="03:00", mode="all", max_transfers=None, results=10,
    ))
    assert seen == [("München", "Berlin"), ("München Hbf", "Berlin")]
    assert result["journeys"][0]["id"] == "found"

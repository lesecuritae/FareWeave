import asyncio
import tempfile
from pathlib import Path

from reisevergleich.coverage import opencellid


def point(name, latitude, longitude, distance):
    return {"name": name, "latitude": latitude, "longitude": longitude, "distance_km": distance}


def cell(mnc, latitude, longitude, identifier, radio="LTE"):
    return opencellid.parse_cell({
        "radio": radio, "mcc": 262, "net": mnc, "area": 100,
        "cell": identifier, "lat": latitude, "lon": longitude, "range": 3000,
    })


def test_german_mcc_mnc_mapping_rejects_other_providers():
    assert opencellid.operator_for(262, 1) == "Telekom"
    assert opencellid.operator_for("262", "02") == "Vodafone"
    assert opencellid.operator_for(262, 3) == "Telefónica/O2"
    assert opencellid.operator_for(262, 23) == "1&1"
    assert opencellid.operator_for(262, 10) is None
    assert opencellid.parse_cell({"mcc": 262, "net": 10, "cell": 1, "radio": "LTE", "lat": 51, "lon": 12}) is None
    assert opencellid.parse_cell({"mcc": 262, "net": 1, "cell": 1, "radio": "GSM", "lat": 51, "lon": 12}) is None


def test_leipzig_halle_kassel_uses_complete_route_and_detects_gaps():
    points = [
        point("Leipzig Hbf", 51.345, 12.382, 0),
        point("Leipzig-West", 51.36, 12.20, 18),
        point("Halle (Saale) Hbf", 51.478, 11.987, 38),
        point("Ländlicher Abschnitt", 51.30, 10.80, 125),
        point("Kassel-Wilhelmshöhe", 51.313, 9.447, 200),
    ]
    cells = [
        cell(1, 51.345, 12.382, 101), cell(1, 51.478, 11.987, 102), cell(1, 51.313, 9.447, 103),
        cell(2, 51.345, 12.382, 201), cell(2, 51.478, 11.987, 202),
        cell(3, 51.36, 12.20, 301), cell(3, 51.30, 10.80, 302), cell(3, 51.313, 9.447, 303),
        cell(23, 51.345, 12.382, 401),
    ]
    result = opencellid.calculate(points, [item for item in cells if item])
    by_name = {item["name"]: item for item in result}
    assert set(by_name) == {"Telekom", "Vodafone", "Telefónica/O2", "1&1"}
    assert by_name["Telekom"]["coverage_percent"] == 60
    assert by_name["Telefónica/O2"]["coverage_percent"] == 60
    assert by_name["Vodafone"]["weak_sections"]
    assert all(item["evaluated_points"] == len(points) for item in result)
    assert sum(item["cell_count"] for item in result) == 9


def test_sparse_opencellid_data_is_not_presented_as_coverage():
    points = [point("A", 51.0, 10.0, 0), point("B", 52.0, 11.0, 150)]
    assert opencellid.calculate(points, [cell(1, 51.0, 10.0, 1)]) == []


def test_csv_pipeline_reports_route_debug_and_unknown_codes():
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "cells.csv"
        source.write_text(
            "radio,mcc,net,area,cell,lon,lat,range\n"
            "LTE,262,1,1,101,12.382,51.345,3000\n"
            "LTE,262,2,1,201,12.383,51.346,3000\n"
            "NR,262,3,1,301,12.381,51.344,3000\n"
            "LTE,262,99,1,999,12.380,51.343,3000\n",
            encoding="utf-8",
        )
        previous = opencellid.CSV_PATH
        opencellid.CSV_PATH = str(source)
        try:
            points = [
                point("Leipzig Hbf", 51.345, 12.382, 0),
                point("Leipzig Zentrum", 51.346, 12.383, 1),
            ]
            result = asyncio.run(opencellid.sample_operators(points))
        finally:
            opencellid.CSV_PATH = previous
    assert result["debug"] == {
        "source": "csv", "evaluated_points": 2, "cells_found": 3,
        "recognized_operators": ["Telekom", "Vodafone", "Telefónica/O2"],
        "unknown_mcc_mnc": ["262-99"], "api_errors": 0, "data_quality": "good",
    }
    assert {item["name"] for item in result["networks"]} == {"Telekom", "Vodafone", "Telefónica/O2"}


if __name__ == "__main__":
    test_german_mcc_mnc_mapping_rejects_other_providers()
    test_leipzig_halle_kassel_uses_complete_route_and_detects_gaps()
    test_sparse_opencellid_data_is_not_presented_as_coverage()
    test_csv_pipeline_reports_route_debug_and_unknown_codes()
    print("OpenCellID Betreiber-, Vollstrecken- und Qualitätsregression: OK")

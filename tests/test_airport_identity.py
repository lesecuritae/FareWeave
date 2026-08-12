from datetime import datetime

from reisevergleich.feeder_common import valid_feeder_options
from reisevergleich.transitous import choose_match


def option(destination: str, *, departure: str = '2030-09-15T07:00:00+02:00', arrival: str = '2030-09-15T08:00:00+02:00') -> dict:
    return {
        'type': 'regression',
        'departure': departure,
        'arrival': arrival,
        'total_price': 10.0,
        'segments': [{
            'origin': 'Berlin Hbf',
            'destination': destination,
            'departure': departure,
            'arrival': arrival,
            'legs': [],
        }],
    }


def check_transitous_prefers_right_airport() -> None:
    matches = [
        {'id': 'fra-t2', 'name': 'Frankfurt (Main) Flughafen Terminal 2', 'type': 'STOP', 'score': 9999},
        {'id': 'ber-t12', 'name': 'Flughafen BER - Terminal 1-2', 'type': 'STOP', 'score': 1},
    ]
    selected = choose_match(matches, 'Flughafen BER - Terminal 1-2')
    assert selected and selected.get('id') == 'ber-t12', selected


def check_transitous_rejects_wrong_airport_only() -> None:
    matches = [
        {'id': 'fra-t2', 'name': 'Frankfurt (Main) Flughafen Terminal 2', 'type': 'STOP', 'score': 9999},
        {'id': 'cgn-t1', 'name': 'Flughafen Köln/Bonn Terminal 1, Köln', 'type': 'STOP', 'score': 9000},
    ]
    selected = choose_match(matches, 'Flughafen BER - Terminal 1-2')
    assert selected is None, selected


def check_transitous_generic_airport_uses_city_tokens() -> None:
    matches = [
        {"id": "wrong", "name": "Bari Airport", "type": "STOP", "score": 90},
        {"id": "right", "name": "Madrid Barajas Airport Terminal 4", "type": "STOP", "score": -30},
    ]
    selected = choose_match(matches, "Madrid Airport MAD")
    assert selected and selected.get("id") == "right", selected


def check_final_feeder_guard_rejects_wrong_airport() -> None:
    lower = datetime.fromisoformat('2030-09-15T06:00:00+02:00')
    cutoff = datetime.fromisoformat('2030-09-15T11:45:00+02:00')
    candidates = [
        option('Flughafen Köln/Bonn Terminal 1, Köln'),
        option('Frankfurt (Main) Flughafen Terminal 2'),
        option('Flughafen BER - Terminal 1-2'),
    ]
    valid = valid_feeder_options(
        candidates,
        lower_bound=lower,
        arrival_cutoff=cutoff,
        expected_destination_station='Flughafen BER - Terminal 1-2',
    )
    destinations = [x['segments'][-1]['destination'] for x in valid]
    assert destinations == ['Flughafen BER - Terminal 1-2'], destinations


def main() -> None:
    tests = [
        ('Transitous bevorzugt BER vor Frankfurt', check_transitous_prefers_right_airport),
        ('Transitous verwirft Frankfurt/Köln bei BER-Anfrage', check_transitous_rejects_wrong_airport_only),
        ("Transitous wählt internationalen Flughafen nach Stadtidentität", check_transitous_generic_airport_uses_city_tokens),
        ('Letzter Zubringer-Guard verwirft falschen Flughafen', check_final_feeder_guard_rejects_wrong_airport),
    ]
    failures=[]
    for name, func in tests:
        try:
            func()
            print(name + ': OK')
        except Exception as exc:
            failures.append((name, exc))
            print(name + ': ROT -> ' + repr(exc))
    if failures:
        raise SystemExit(1)
    print('Provider-Flughafenidentität Regression: OK')


if __name__ == '__main__':
    main()

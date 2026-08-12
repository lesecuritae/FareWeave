from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import reisevergleich.db as db
import reisevergleich.feeder as feeder
from reisevergleich.compare import _route_departure_in_window
from reisevergleich.trvl import _filter_ground_window

TZ = ZoneInfo('Europe/Berlin')
assert _route_departure_in_window({"departure": {"time": "2030-09-15T05:59:00+02:00"}}, "2030-09-15", "06:00") is False
assert _route_departure_in_window({"departure": {"time": "2030-09-15T06:00:00+02:00"}}, "2030-09-15", "06:00") is True
assert _filter_ground_window([{"departure": {"time": "2030-09-15T10:46:00Z"}, "timezone": "Europe/Madrid"}], "2030-09-15", depart_after="12:00")
assert _filter_ground_window([{"departure": "2030-09-15T10:46:00Z", "timezone": "Europe/Madrid"}], "2030-09-15", depart_after="12:00")


async def test_db_keeps_departure_floor_with_arrival_ceiling() -> None:
    captured = {}

    class Response:
        status_code = 200
        text = ''
        def json(self):
            return {'status': 'ok', 'journeys': []}

    class Client:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def post(self, url, json):
            captured.update(json)
            return Response()

    original = db.httpx.AsyncClient
    db.httpx.AsyncClient = lambda *args, **kwargs: Client()
    try:
        await db.db_search(
            origin='Berlin Hbf',
            destination='Flughafen BER - Terminal 1-2',
            travel_date='2030-09-15',
            departure_after='06:00',
            mode='all',
            max_transfers=5,
            results=12,
            arrival_before=datetime.fromisoformat('2030-09-15T11:45:00+02:00'),
            bestprice=True,
            not_only_fast_routes=True,
        )
    finally:
        db.httpx.AsyncClient = original

    assert captured.get('departure', '').startswith('2030-09-15T06:00:00'), captured
    assert captured.get('arrival_before', '').startswith('2030-09-15T11:45:00'), captured
    assert 'arrival' not in captured, captured


async def test_invalid_dticket_candidate_must_not_suppress_fallback() -> None:
    paid = {
        'id': 'paid',
        'provider': 'Deutsche Bahn',
        'type': 'train',
        'origin': 'Berlin Hbf',
        'destination': 'Flughafen BER - Terminal 1-2',
        'departure': '2030-09-15T07:00:00+02:00',
        'arrival': '2030-09-15T07:40:00+02:00',
        'duration_minutes': 40,
        'price': 12.0,
        'currency': 'EUR',
        'legs': [{
            'mode': 'train',
            'origin': {'name': 'Berlin Hbf'},
            'destination': {'name': 'Flughafen BER - Terminal 1-2'},
            'departure': '2030-09-15T07:00:00+02:00',
            'arrival': '2030-09-15T07:40:00+02:00',
        }],
    }
    invalid_dt = {
        'id': 'dt-wrong-terminal',
        'provider': 'Deutsche Bahn',
        'type': 'train',
        'origin': 'Berlin Hbf',
        'destination': 'Flughafen BER - Terminal 5 [Bus Terminal], Schönefeld',
        'departure': '2030-09-15T07:05:00+02:00',
        'arrival': '2030-09-15T08:00:00+02:00',
        'duration_minutes': 55,
        'price': 0,
        'currency': 'EUR',
        'legs': [{
            'mode': 'train',
            'origin': {'name': 'Berlin Hbf'},
            'destination': {'name': 'Flughafen BER - Terminal 5 [Bus Terminal], Schönefeld'},
            'departure': '2030-09-15T07:05:00+02:00',
            'arrival': '2030-09-15T08:00:00+02:00',
        }],
    }
    fallback = {
        'type': 'deutschlandticket_transitous',
        'label': 'Nahverkehrs-Zubringer als Deutschlandticket-Kandidat',
        'departure': '2030-09-15T07:10:00+02:00',
        'arrival': '2030-09-15T08:05:00+02:00',
        'duration_minutes': 55,
        'total_price': 0.0,
        'price_known': True,
        'currency': 'EUR',
        'requires_deutschlandticket': True,
        'segments': [{
            'provider': 'Transitous',
            'type': 'public_transport',
            'origin': 'Berlin Hbf',
            'destination': 'Flughafen BER - Terminal 1-2',
            'departure': '2030-09-15T07:10:00+02:00',
            'arrival': '2030-09-15T08:05:00+02:00',
            'legs': [],
        }],
    }
    fallback_called = {'value': False}

    async def fake_db_routes(origin, destination, travel_date, departure_after, **kwargs):
        if kwargs.get('mode') == 'deutschlandticket':
            return [invalid_dt], [], 'dbnav'
        return [paid], [{'source': 'db-api', 'ok': True, 'routes': 1}], 'dbnav'

    async def fake_transitous(*args, **kwargs):
        fallback_called['value'] = True
        return [fallback], {'ok': True, 'source': 'transitous', 'routes': 1}

    async def fake_split(*args, **kwargs):
        return []

    async def fake_flix(*args, **kwargs):
        return [], {'tested': True}

    originals = {
        '_db_routes': feeder._db_routes,
        '_transitous_dticket_feeder_options': feeder._transitous_dticket_feeder_options,
        '_native_split_options': feeder._native_split_options,
        '_feeder_handoffs': feeder._feeder_handoffs,
        '_flix_outbound_feeder_options': feeder._flix_outbound_feeder_options,
    }
    feeder._db_routes = fake_db_routes
    feeder._transitous_dticket_feeder_options = fake_transitous
    feeder._native_split_options = fake_split
    feeder._feeder_handoffs = lambda *args, **kwargs: []
    feeder._flix_outbound_feeder_options = fake_flix
    try:
        result = await feeder.feeder_outbound(
            'Berlin Hbf',
            'BER',
            'Flughafen BER - Terminal 1-2',
            '2030-09-15',
            '06:00',
            datetime.fromisoformat('2030-09-15T13:45:00+02:00'),
            120,
            preference='dticket_first',
            deutschlandticket_available=True,
            split_ticket_check=True,
            include_flixbus=False,
            include_flixtrain=False,
        )
    finally:
        for name, value in originals.items():
            setattr(feeder, name, value)

    options=[]
    if isinstance(result.get('selected_option'), dict):
        options.append(result['selected_option'])
    options.extend(x for x in (result.get('alternatives') or []) if isinstance(x, dict))
    assert fallback_called['value'] is True, result
    assert any(x.get('requires_deutschlandticket') is True for x in options), result
    assert any(x.get('requires_deutschlandticket') is not True for x in options), result
    assert result.get('deutschlandticket_fallback', {}).get('ok') is True, result


async def main() -> None:
    failures=[]
    for name, func in [
        ('DB departure_after + arrival ceiling', test_db_keeps_departure_floor_with_arrival_ceiling),
        ('D-Ticket fallback after validation', test_invalid_dticket_candidate_must_not_suppress_fallback),
    ]:
        try:
            await func()
            print(name + ': OK')
        except Exception as exc:
            failures.append((name, exc))
            print(name + ': ROT -> ' + repr(exc))
    if failures:
        raise SystemExit(1)
    print('Live-window/Fallback-Regression: OK')


if __name__ == '__main__':
    asyncio.run(main())

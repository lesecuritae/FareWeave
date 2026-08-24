import asyncio

from reisevergleich import compare


async def main():
    routes = [{"id": "db-1", "price": 29.99}]
    original_enrich = compare.enrich_routes_history
    original_timeout = compare.HISTORY_ENRICH_TIMEOUT

    async def slow_enrich(_routes):
        await asyncio.sleep(1)
        return [{"id": "should-not-win"}]

    compare.enrich_routes_history = slow_enrich
    compare.HISTORY_ENRICH_TIMEOUT = 0.01
    try:
        started = asyncio.get_running_loop().time()
        result = await compare._enrich_history_bounded(routes)
        elapsed = asyncio.get_running_loop().time() - started
    finally:
        compare.enrich_routes_history = original_enrich
        compare.HISTORY_ENRICH_TIMEOUT = original_timeout

    assert result == routes
    assert elapsed < 0.2, elapsed


asyncio.run(main())
print("Additive History-Anreicherung blockiert die Kernsuche nicht: OK")

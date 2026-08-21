from reisevergleich.progress import begin, end, get, update, valid_search_id

assert valid_search_id("fw_12345678") == "fw_12345678"
assert valid_search_id("bad/id") is None

first = begin("fw_first_search")
update("db", "completed")
update("gtfs", "failed", "Timeout")
end(first)
status = get("fw_first_search")
assert status["status"] == "completed"
assert status["steps"]["db"]["status"] == "completed"
assert status["steps"]["gtfs"]["status"] == "failed"

second = begin("fw_second_search")
update("db", "loading")
assert get("fw_second_search")["steps"] == {"db": get("fw_second_search")["steps"]["db"]}
assert get("fw_first_search")["steps"]["db"]["status"] == "completed"
end(second, status="cancelled")
assert get("fw_second_search")["status"] == "cancelled"

print("Suchfortschritt und Request-Isolation: OK")

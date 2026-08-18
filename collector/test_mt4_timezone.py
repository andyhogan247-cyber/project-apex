from pathlib import Path

from collector.mt4_source import MT4MarketDataSource


TEST_FILE = Path("data/test_mt4_timezone.csv")


TEST_FILE.write_text(
    "2026.08.17 19:32:41,"
    "XAUUSD,"
    "4422.77,"
    "4423.23,"
    "0.46,"
    "4424.49,"
    "4424.66,"
    "4422.87,"
    "4422.89,"
    "281\n",
    encoding="utf-8",
)


source = MT4MarketDataSource(
    data_file=str(TEST_FILE),
    server_utc_offset_hours=3,
)

snapshot = source.get_snapshot()

print("MT4 server timestamp: 2026-08-17 19:32:41")
print(
    "APEX UTC timestamp:",
    snapshot.timestamp.isoformat(),
)

assert snapshot.timestamp.isoformat() == "2026-08-17T16:32:41"

assert snapshot.symbol == "XAUUSD"
assert snapshot.bid == 4422.77
assert snapshot.ask == 4423.23
assert snapshot.m1_open == 4424.49
assert snapshot.m1_high == 4424.66
assert snapshot.m1_low == 4422.87
assert snapshot.m1_close == 4422.89

TEST_FILE.unlink()

print()
print("✅ MT4 timezone conversion test passed")
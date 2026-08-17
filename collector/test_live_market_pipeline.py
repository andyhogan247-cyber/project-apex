from datetime import datetime
from pathlib import Path

from collector.market_collector import MarketCollector
from collector.mt4_source import MT4MarketDataSource
from database.market_memory_repository import MarketMemoryRepository


TEST_FILE = Path("data/test_mt4_live.csv")


def create_fresh_test_data():
    now = datetime.now().replace(microsecond=0)

    row = (
        f"{now.strftime('%Y.%m.%d %H:%M:%S')},"
        "XAUUSD,"
        "4326.40,"
        "4326.60,"
        "0.20,"
        "4326.40,"
        "4326.70,"
        "4326.20,"
        "4326.50,"
        "1842\n"
    )

    TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEST_FILE.write_text(row, encoding="utf-8")


create_fresh_test_data()

source = MT4MarketDataSource(
    data_file=str(TEST_FILE)
)

repository = MarketMemoryRepository()

collector = MarketCollector(
    source=source,
    repository=repository,
    interval_seconds=60,
)

before = repository.count_observations("XAUUSD")

print(f"Observations before: {before}")

snapshot = collector.collect_once()

after = repository.count_observations("XAUUSD")

print(f"Observations after: {after}")

print()
print("Latest observation:")

latest = repository.latest_observation("XAUUSD")

if latest is None:
    raise AssertionError(
        "No market observation found after collection"
    )

print(dict(latest))

assert latest["source"] == "MT4"
assert latest["symbol"] == "XAUUSD"

repository.close()

try:
    TEST_FILE.unlink()
except FileNotFoundError:
    pass

print()
print("✅ Live market pipeline test passed")
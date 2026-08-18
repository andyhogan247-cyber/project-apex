from datetime import datetime, timedelta, timezone
from pathlib import Path

from collector.market_collector import MarketCollector
from collector.mt4_source import MT4MarketDataSource
from database.market_memory_repository import MarketMemoryRepository


TEST_FILE = Path("data/test_collector_cycles.csv")


def create_test_data():
    now = (
    datetime.now(timezone.utc)
    + timedelta(hours=3)
).replace(microsecond=0)

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


create_test_data()

source = MT4MarketDataSource(
    data_file=str(TEST_FILE)
)

repository = MarketMemoryRepository()

collector = MarketCollector(
    source=source,
    repository=repository,
    interval_seconds=0,
)

collector.start(max_cycles=3)

stats = collector.get_stats()

print()
print("Collector statistics:")
print(stats)

assert stats["total_attempts"] == 3
assert stats["successful_collections"] == 3
assert stats["failed_collections"] == 0

repository.close()

try:
    TEST_FILE.unlink()
except FileNotFoundError:
    pass

print()
print("✅ Collector cycle test passed")
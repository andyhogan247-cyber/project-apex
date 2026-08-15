from datetime import datetime

from collector.market_collector import MarketCollector
from collector.market_snapshot import MarketSnapshot
from database.market_repository import MarketRepository


class TestMarketDataSource:

    def get_snapshot(self):

        now = datetime.now()

        return MarketSnapshot(
            timestamp=now,
            symbol="XAUUSD",
            bid=4326.40,
            ask=4326.60,
            mid=4326.50,
            spread=0.20,
            volume=1842,
            timeframe="M1",
            source="TEST",
        )


source = TestMarketDataSource()

repository = MarketRepository()

collector = MarketCollector(
    source=source,
    repository=repository,
    interval_seconds=1,
)

snapshot = collector.collect_once()

print()
print("Statistics:")
print(collector.get_stats())

repository.close()

print()
print("✅ Collector test passed")
print(snapshot)
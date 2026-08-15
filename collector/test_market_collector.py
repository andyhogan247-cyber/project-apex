from collector.market_collector import MarketCollector
from collector.mt4_source import MT4MarketDataSource
from database.market_repository import MarketRepository


source = MT4MarketDataSource()

repository = MarketRepository()

collector = MarketCollector(
    source=source,
    repository=repository,
    interval_seconds=1,
)

snapshot = collector.collect_once()

collector.stop()

print()
print("✅ Collector test passed")
print(snapshot)
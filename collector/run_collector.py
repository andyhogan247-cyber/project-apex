from collector.market_collector import MarketCollector
from collector.mt4_source import MT4MarketDataSource
from database.market_memory_repository import MarketMemoryRepository


source = MT4MarketDataSource()

repository = MarketMemoryRepository()

collector = MarketCollector(
    source=source,
    repository=repository,
    interval_seconds=60,
)

collector.start()
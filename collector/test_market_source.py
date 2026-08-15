from datetime import datetime

from collector.market_source import MarketDataSource
from collector.market_snapshot import MarketSnapshot


class TestMarketDataSource(MarketDataSource):

    def get_snapshot(self) -> MarketSnapshot:

        return MarketSnapshot(
            timestamp=datetime.now(),
            symbol="XAUUSD",
            bid=4326.40,
            ask=4326.60,
            mid=4326.50,
            spread=0.20,
            volume=1842,
            timeframe="M1",
            source="TEST"
        )


source = TestMarketDataSource()

snapshot = source.get_snapshot()

print(snapshot)
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
            m1_open=4326.40,
            m1_high=4326.70,
            m1_low=4326.20,
            m1_close=4326.50,
            volume=1842,
            timeframe="M1",
            source="TEST",
        )


source = TestMarketDataSource()

snapshot = source.get_snapshot()

print(snapshot)
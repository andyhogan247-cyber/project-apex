from datetime import datetime

from collector.market_snapshot import MarketSnapshot
from database.market_repository import MarketRepository


snapshot = MarketSnapshot(
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


repo = MarketRepository()

repo.save_snapshot(snapshot)

repo.close()
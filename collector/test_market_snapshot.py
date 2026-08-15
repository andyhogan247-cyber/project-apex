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
    volume=1842,
    timeframe="M1",
    source="TEST"
)


repo = MarketRepository()

repo.save_snapshot(snapshot)

repo.close()
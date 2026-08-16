from datetime import datetime

from collector.market_snapshot import MarketSnapshot
from database.market_memory_repository import MarketMemoryRepository


repository = MarketMemoryRepository()


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


saved = repository.save_observation(snapshot)

print(f"Saved new observation: {saved}")

count = repository.count_observations("XAUUSD")

print(f"XAUUSD observations: {count}")

latest = repository.latest_observation("XAUUSD")

print("Latest observation:")
print(dict(latest))

repository.close()

print("✅ Market memory test passed")
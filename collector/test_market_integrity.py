from datetime import datetime, timedelta

from collector.market_snapshot import MarketSnapshot
from database.market_repository import MarketRepository


repository = MarketRepository()


def create_snapshot(timestamp):

    return MarketSnapshot(
        timestamp=timestamp,
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


base_time = datetime.now().replace(second=0, microsecond=0)


repository.save_snapshot(
    create_snapshot(base_time)
)

repository.save_snapshot(
    create_snapshot(
        base_time + timedelta(minutes=1)
    )
)

repository.save_snapshot(
    create_snapshot(
        base_time + timedelta(minutes=3)
    )
)


existing = repository.snapshot_exists(
    base_time,
    symbol="XAUUSD",
    timeframe="M1",
)

if existing:
    print("✅ Existing snapshot detected")
else:
    raise AssertionError(
        "Existing snapshot was not detected"
    )


missing = repository.snapshot_exists(
    base_time + timedelta(minutes=2),
    symbol="XAUUSD",
    timeframe="M1",
)

if not missing:
    print("✅ Non-existent snapshot correctly identified")
else:
    raise AssertionError(
        "Non-existent snapshot was incorrectly detected"
    )


missing_minutes = repository.find_missing_minutes(
    base_time,
    base_time + timedelta(minutes=3),
    symbol="XAUUSD",
    timeframe="M1",
)

print(
    f"Missing minutes detected: "
    f"{len(missing_minutes)}"
)


if len(missing_minutes) == 1:
    print("✅ Missing-minute detection passed")
else:
    raise AssertionError(
        f"Expected 1 missing minute, "
        f"found {len(missing_minutes)}"
    )


repository.close()

print("✅ Market integrity tests passed")
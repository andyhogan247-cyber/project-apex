from datetime import datetime, timedelta

from collector.market_snapshot import MarketSnapshot
from database.market_repository import MarketRepository


repository = MarketRepository()


base_time = datetime.now().replace(second=0, microsecond=0)


def create_snapshot(timestamp):

    return MarketSnapshot(
        timestamp=timestamp,
        symbol="XAUUSD",
        bid=4326.40,
        ask=4326.60,
        mid=4326.50,
        spread=0.20,
        volume=1842,
        timeframe="M1",
        source="TEST",
    )


# Create three consecutive observations.
repository.save_snapshot(
    create_snapshot(base_time)
)

repository.save_snapshot(
    create_snapshot(base_time + timedelta(minutes=1))
)

repository.save_snapshot(
    create_snapshot(base_time + timedelta(minutes=2))
)


# Check that an existing snapshot is detected.
exists = repository.snapshot_exists(
    base_time
)

assert exists is True

print("✅ Existing snapshot detected")


# Check that a non-existent snapshot is detected.
missing = repository.snapshot_exists(
    base_time + timedelta(minutes=10)
)

assert missing is False

print("✅ Non-existent snapshot correctly identified")


# Check for missing minutes.
missing_minutes = repository.find_missing_minutes(
    base_time,
    base_time + timedelta(minutes=4)
)

print(
    f"Missing minutes detected: "
    f"{len(missing_minutes)}"
)

assert len(missing_minutes) == 2

print("✅ Missing-minute detection passed")


repository.close()

print("✅ Market integrity tests passed")
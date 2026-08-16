from datetime import datetime, timedelta

from collector.market_collector import MarketCollector
from collector.market_snapshot import MarketSnapshot
from database.market_repository import MarketRepository


repository = MarketRepository()

collector = MarketCollector(
    source=None,
    repository=repository,
)


def test_invalid_bid():

    snapshot = MarketSnapshot(
        timestamp=datetime.now(),
        symbol="XAUUSD",
        bid=-1,
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

    try:
        collector.validate_snapshot(snapshot)
        raise AssertionError("Invalid bid was accepted")

    except ValueError as error:
        print(f"✅ Invalid bid rejected: {error}")


def test_invalid_spread():

    snapshot = MarketSnapshot(
        timestamp=datetime.now(),
        symbol="XAUUSD",
        bid=4326.60,
        ask=4326.40,
        mid=4326.50,
        spread=-0.20,
        m1_open=4326.40,
        m1_high=4326.70,
        m1_low=4326.20,
        m1_close=4326.50,
        volume=1842,
        timeframe="M1",
        source="TEST",
    )

    try:
        collector.validate_snapshot(snapshot)
        raise AssertionError("Invalid spread was accepted")

    except ValueError as error:
        print(f"✅ Invalid spread rejected: {error}")


def test_stale_snapshot():

    snapshot = MarketSnapshot(
        timestamp=datetime.now() - timedelta(minutes=10),
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

    try:
        collector.validate_snapshot(snapshot)
        raise AssertionError("Stale snapshot was accepted")

    except ValueError as error:
        print(f"✅ Stale snapshot rejected: {error}")


test_invalid_bid()
test_invalid_spread()
test_stale_snapshot()

repository.close()

print("✅ Market validation tests passed")
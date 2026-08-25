from datetime import datetime, time

from collector.market_session import MarketSessionManager


manager = MarketSessionManager(
    trading_start=time(6, 0),
    trading_end=time(18, 0),
)


def test_saturday_closed():
    timestamp = datetime(
        2026,
        8,
        22,
        12,
        0,
    )

    result = manager.get_status(timestamp)

    assert result.state == "MARKET_CLOSED"
    assert result.trading_allowed is False

    print("✅ Saturday → MARKET_CLOSED")


def test_sunday_closed():
    timestamp = datetime(
        2026,
        8,
        23,
        12,
        0,
    )

    result = manager.get_status(timestamp)

    assert result.state == "MARKET_CLOSED"
    assert result.trading_allowed is False

    print("✅ Sunday → MARKET_CLOSED")


def test_before_session():
    timestamp = datetime(
        2026,
        8,
        20,
        5,
        59,
    )

    result = manager.get_status(timestamp)

    assert result.state == "SESSION_CLOSED"
    assert result.trading_allowed is False

    print("✅ Before 06:00 → SESSION_CLOSED")


def test_session_open():
    timestamp = datetime(
        2026,
        8,
        20,
        10,
        30,
    )

    result = manager.get_status(timestamp)

    assert result.state == "OPEN"
    assert result.trading_allowed is True

    print("✅ 10:30 → OPEN")


def test_session_end():
    timestamp = datetime(
        2026,
        8,
        20,
        18,
        0,
    )

    result = manager.get_status(timestamp)

    assert result.state == "SESSION_CLOSED"
    assert result.trading_allowed is False

    print("✅ 18:00 → SESSION_CLOSED")


def test_after_session():
    timestamp = datetime(
        2026,
        8,
        20,
        21,
        0,
    )

    result = manager.get_status(timestamp)

    assert result.state == "SESSION_CLOSED"
    assert result.trading_allowed is False

    print("✅ After 18:00 → SESSION_CLOSED")


def test_friday_before_close():
    timestamp = datetime(
        2026,
        8,
        21,
        17,
        59,
    )

    result = manager.get_status(timestamp)

    assert result.state == "OPEN"
    assert result.trading_allowed is True

    print("✅ Friday 17:59 → OPEN")


def test_saturday_during_trading_window():
    timestamp = datetime(
        2026,
        8,
        22,
        10,
        30,
    )

    result = manager.get_status(timestamp)

    assert result.state == "MARKET_CLOSED"
    assert result.trading_allowed is False

    print("✅ Saturday 10:30 → MARKET_CLOSED")


def main():
    print()
    print("=== APEX Market Session Test Suite ===")
    print()

    test_saturday_closed()
    test_sunday_closed()
    test_before_session()
    test_session_open()
    test_session_end()
    test_after_session()
    test_friday_before_close()
    test_saturday_during_trading_window()

    print()
    print("=======================================")
    print("✅ ALL MARKET SESSION TESTS PASSED")
    print("=======================================")


if __name__ == "__main__":
    main()
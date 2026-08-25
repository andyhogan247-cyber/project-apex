from collector.market_session import MarketSessionManager
from collector.trading_gate import (
    TradeRequest,
    TradingGate,
)


def healthy_market():
    return {
        "status": "HEALTHY",
    }


def open_session():
    manager = MarketSessionManager()

    return manager.get_status(
        timestamp=__import__("datetime").datetime(
            2026,
            8,
            21,
            10,
            30,
        )
    )


def valid_request():
    return TradeRequest(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=4640.00,
        bid=4639.80,
        ask=4640.20,
        spread=0.40,
    )


def test_valid_trade_allowed():

    gate = TradingGate(
        symbol="XAUUSD",
        max_spread=1.00,
    )

    result = gate.evaluate(
        valid_request(),
        open_session(),
        healthy_market(),
    )

    assert result.allowed is True
    assert result.reason == (
        "ALL_TRADING_GATE_CHECKS_PASSED"
    )

    print("✅ Valid trade → ALLOWED")


def test_closed_session_blocked():

    gate = TradingGate()

    manager = MarketSessionManager()

    session = manager.get_status(
        timestamp=__import__("datetime").datetime(
            2026,
            8,
            22,
            10,
            30,
        )
    )

    result = gate.evaluate(
        valid_request(),
        session,
        healthy_market(),
    )

    assert result.allowed is False
    assert result.reason == (
        "SESSION_NOT_OPEN:MARKET_CLOSED"
    )

    print("✅ Market closed → BLOCKED")


def test_unhealthy_market_blocked():

    gate = TradingGate()

    result = gate.evaluate(
        valid_request(),
        open_session(),
        {"status": "FAILED"},
    )

    assert result.allowed is False
    assert result.reason == (
        "MARKET_HEALTH_FAILED"
    )

    print("✅ Failed market health → BLOCKED")


def test_degraded_market_blocked():

    gate = TradingGate()

    result = gate.evaluate(
        valid_request(),
        open_session(),
        {"status": "DEGRADED"},
    )

    assert result.allowed is False
    assert result.reason == (
        "MARKET_HEALTH_DEGRADED"
    )

    print("✅ Degraded market → BLOCKED")


def test_wrong_symbol_blocked():

    gate = TradingGate(
        symbol="XAUUSD",
    )

    request = TradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.10,
        bid=1.0999,
        ask=1.1001,
        spread=0.0002,
    )

    result = gate.evaluate(
        request,
        open_session(),
        healthy_market(),
    )

    assert result.allowed is False
    assert result.reason == "SYMBOL_MISMATCH"

    print("✅ Wrong symbol → BLOCKED")


def test_invalid_direction_blocked():

    gate = TradingGate()

    request = valid_request()

    request = TradeRequest(
        symbol=request.symbol,
        direction="HOLD",
        entry_price=request.entry_price,
        bid=request.bid,
        ask=request.ask,
        spread=request.spread,
    )

    result = gate.evaluate(
        request,
        open_session(),
        healthy_market(),
    )

    assert result.allowed is False
    assert result.reason == "INVALID_DIRECTION"

    print("✅ Invalid direction → BLOCKED")


def test_invalid_entry_blocked():

    gate = TradingGate()

    request = valid_request()

    request = TradeRequest(
        symbol=request.symbol,
        direction=request.direction,
        entry_price=0,
        bid=request.bid,
        ask=request.ask,
        spread=request.spread,
    )

    result = gate.evaluate(
        request,
        open_session(),
        healthy_market(),
    )

    assert result.allowed is False
    assert result.reason == "INVALID_ENTRY_PRICE"

    print("✅ Invalid entry price → BLOCKED")


def test_invalid_bid_blocked():

    gate = TradingGate()

    request = valid_request()

    request = TradeRequest(
        symbol=request.symbol,
        direction=request.direction,
        entry_price=request.entry_price,
        bid=0,
        ask=request.ask,
        spread=request.spread,
    )

    result = gate.evaluate(
        request,
        open_session(),
        healthy_market(),
    )

    assert result.allowed is False
    assert result.reason == "INVALID_BID"

    print("✅ Invalid bid → BLOCKED")


def test_invalid_ask_blocked():

    gate = TradingGate()

    request = valid_request()

    request = TradeRequest(
        symbol=request.symbol,
        direction=request.direction,
        entry_price=request.entry_price,
        bid=request.bid,
        ask=0,
        spread=request.spread,
    )

    result = gate.evaluate(
        request,
        open_session(),
        healthy_market(),
    )

    assert result.allowed is False
    assert result.reason == "INVALID_ASK"

    print("✅ Invalid ask → BLOCKED")


def test_ask_below_bid_blocked():

    gate = TradingGate()

    request = TradeRequest(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=4640.00,
        bid=4640.20,
        ask=4640.10,
        spread=0.10,
    )

    result = gate.evaluate(
        request,
        open_session(),
        healthy_market(),
    )

    assert result.allowed is False
    assert result.reason == "ASK_BELOW_BID"

    print("✅ Ask below bid → BLOCKED")


def test_negative_spread_blocked():

    gate = TradingGate()

    request = valid_request()

    request = TradeRequest(
        symbol=request.symbol,
        direction=request.direction,
        entry_price=request.entry_price,
        bid=request.bid,
        ask=request.ask,
        spread=-0.10,
    )

    result = gate.evaluate(
        request,
        open_session(),
        healthy_market(),
    )

    assert result.allowed is False
    assert result.reason == "NEGATIVE_SPREAD"

    print("✅ Negative spread → BLOCKED")


def test_wide_spread_blocked():

    gate = TradingGate(
        max_spread=1.00,
    )

    request = valid_request()

    request = TradeRequest(
        symbol=request.symbol,
        direction=request.direction,
        entry_price=request.entry_price,
        bid=request.bid,
        ask=request.ask,
        spread=1.01,
    )

    result = gate.evaluate(
        request,
        open_session(),
        healthy_market(),
    )

    assert result.allowed is False
    assert result.reason == "SPREAD_TOO_WIDE"

    print("✅ Wide spread → BLOCKED")


def test_missing_session_blocked():

    gate = TradingGate()

    result = gate.evaluate(
        valid_request(),
        None,
        healthy_market(),
    )

    assert result.allowed is False
    assert result.reason == (
        "SESSION_STATUS_UNAVAILABLE"
    )

    print("✅ Missing session → BLOCKED")


def test_missing_health_blocked():

    gate = TradingGate()

    result = gate.evaluate(
        valid_request(),
        open_session(),
        None,
    )

    assert result.allowed is False
    assert result.reason == (
        "MARKET_HEALTH_UNAVAILABLE"
    )

    print("✅ Missing market health → BLOCKED")


def test_missing_request_blocked():

    gate = TradingGate()

    result = gate.evaluate(
        None,
        open_session(),
        healthy_market(),
    )

    assert result.allowed is False
    assert result.reason == (
        "TRADE_REQUEST_UNAVAILABLE"
    )

    print("✅ Missing trade request → BLOCKED")


def main():

    print()
    print("=== APEX Trading Gate Test Suite ===")
    print()

    test_valid_trade_allowed()
    test_closed_session_blocked()
    test_unhealthy_market_blocked()
    test_degraded_market_blocked()
    test_wrong_symbol_blocked()
    test_invalid_direction_blocked()
    test_invalid_entry_blocked()
    test_invalid_bid_blocked()
    test_invalid_ask_blocked()
    test_ask_below_bid_blocked()
    test_negative_spread_blocked()
    test_wide_spread_blocked()
    test_missing_session_blocked()
    test_missing_health_blocked()
    test_missing_request_blocked()

    print()
    print("===================================")
    print("✅ ALL TRADING GATE TESTS PASSED")
    print("===================================")


if __name__ == "__main__":
    main()
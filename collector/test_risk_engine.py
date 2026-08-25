from collector.risk_engine import (
    RiskEngine,
    RiskRequest,
)


def valid_request():
    return RiskRequest(
        account_balance=10_000.00,
        risk_percent=1.0,
        direction="BUY",
        entry_price=100.00,
        stop_loss=98.00,
        value_per_price_unit=1.0,
        minimum_position_size=0.01,
        maximum_position_size=100.0,
        position_size_step=0.01,
    )


def test_valid_risk_calculation():

    engine = RiskEngine()

    result = engine.calculate(
        valid_request()
    )

    assert result.allowed is True
    assert result.reason == "RISK_CHECKS_PASSED"

    assert result.maximum_risk_amount == 100.0
    assert result.stop_distance == 2.0
    assert result.calculated_position_size == 50.0
    assert result.position_size == 50.0

    print("✅ Valid BUY risk calculation → ALLOWED")


def test_valid_sell_risk_calculation():

    engine = RiskEngine()

    request = RiskRequest(
        account_balance=10_000.00,
        risk_percent=1.0,
        direction="SELL",
        entry_price=100.00,
        stop_loss=102.00,
        value_per_price_unit=1.0,
        minimum_position_size=0.01,
        maximum_position_size=100.0,
        position_size_step=0.01,
    )

    result = engine.calculate(request)

    assert result.allowed is True
    assert result.reason == "RISK_CHECKS_PASSED"

    assert result.maximum_risk_amount == 100.0
    assert result.stop_distance == 2.0
    assert result.calculated_position_size == 50.0
    assert result.position_size == 50.0

    print("✅ Valid SELL risk calculation → ALLOWED")


def test_zero_balance_blocked():

    engine = RiskEngine()

    request = valid_request()

    request = RiskRequest(
        account_balance=0,
        risk_percent=request.risk_percent,
        direction=request.direction,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        value_per_price_unit=request.value_per_price_unit,
        minimum_position_size=request.minimum_position_size,
        maximum_position_size=request.maximum_position_size,
        position_size_step=request.position_size_step,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == "INVALID_ACCOUNT_BALANCE"

    print("✅ Zero account balance → BLOCKED")


def test_negative_balance_blocked():

    engine = RiskEngine()

    request = valid_request()

    request = RiskRequest(
        account_balance=-1000,
        risk_percent=request.risk_percent,
        direction=request.direction,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        value_per_price_unit=request.value_per_price_unit,
        minimum_position_size=request.minimum_position_size,
        maximum_position_size=request.maximum_position_size,
        position_size_step=request.position_size_step,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == "INVALID_ACCOUNT_BALANCE"

    print("✅ Negative account balance → BLOCKED")


def test_zero_risk_blocked():

    engine = RiskEngine()

    request = valid_request()

    request = RiskRequest(
        account_balance=request.account_balance,
        risk_percent=0,
        direction=request.direction,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        value_per_price_unit=request.value_per_price_unit,
        minimum_position_size=request.minimum_position_size,
        maximum_position_size=request.maximum_position_size,
        position_size_step=request.position_size_step,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == "INVALID_RISK_PERCENT"

    print("✅ Zero risk percentage → BLOCKED")


def test_risk_above_100_percent_blocked():

    engine = RiskEngine()

    request = valid_request()

    request = RiskRequest(
        account_balance=request.account_balance,
        risk_percent=100.01,
        direction=request.direction,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        value_per_price_unit=request.value_per_price_unit,
        minimum_position_size=request.minimum_position_size,
        maximum_position_size=request.maximum_position_size,
        position_size_step=request.position_size_step,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == "INVALID_RISK_PERCENT"

    print("✅ Risk above 100% → BLOCKED")


def test_invalid_direction_blocked():

    engine = RiskEngine()

    request = valid_request()

    request = RiskRequest(
        account_balance=request.account_balance,
        risk_percent=request.risk_percent,
        direction="HOLD",
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        value_per_price_unit=request.value_per_price_unit,
        minimum_position_size=request.minimum_position_size,
        maximum_position_size=request.maximum_position_size,
        position_size_step=request.position_size_step,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == "INVALID_DIRECTION"

    print("✅ Invalid direction → BLOCKED")


def test_invalid_entry_blocked():

    engine = RiskEngine()

    request = valid_request()

    request = RiskRequest(
        account_balance=request.account_balance,
        risk_percent=request.risk_percent,
        direction=request.direction,
        entry_price=0,
        stop_loss=request.stop_loss,
        value_per_price_unit=request.value_per_price_unit,
        minimum_position_size=request.minimum_position_size,
        maximum_position_size=request.maximum_position_size,
        position_size_step=request.position_size_step,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == "INVALID_ENTRY_PRICE"

    print("✅ Invalid entry price → BLOCKED")


def test_invalid_stop_blocked():

    engine = RiskEngine()

    request = valid_request()

    request = RiskRequest(
        account_balance=request.account_balance,
        risk_percent=request.risk_percent,
        direction=request.direction,
        entry_price=request.entry_price,
        stop_loss=0,
        value_per_price_unit=request.value_per_price_unit,
        minimum_position_size=request.minimum_position_size,
        maximum_position_size=request.maximum_position_size,
        position_size_step=request.position_size_step,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == "INVALID_STOP_LOSS"

    print("✅ Invalid stop-loss → BLOCKED")


def test_buy_stop_above_entry_blocked():

    engine = RiskEngine()

    request = RiskRequest(
        account_balance=10_000,
        risk_percent=1.0,
        direction="BUY",
        entry_price=100.0,
        stop_loss=101.0,
        value_per_price_unit=1.0,
        minimum_position_size=0.01,
        maximum_position_size=100.0,
        position_size_step=0.01,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == (
        "BUY_STOP_MUST_BE_BELOW_ENTRY"
    )

    print("✅ BUY stop above entry → BLOCKED")


def test_sell_stop_below_entry_blocked():

    engine = RiskEngine()

    request = RiskRequest(
        account_balance=10_000,
        risk_percent=1.0,
        direction="SELL",
        entry_price=100.0,
        stop_loss=99.0,
        value_per_price_unit=1.0,
        minimum_position_size=0.01,
        maximum_position_size=100.0,
        position_size_step=0.01,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == (
        "SELL_STOP_MUST_BE_ABOVE_ENTRY"
    )

    print("✅ SELL stop below entry → BLOCKED")


def test_zero_stop_distance_blocked():

    engine = RiskEngine()

    request = valid_request()

    request = RiskRequest(
        account_balance=request.account_balance,
        risk_percent=request.risk_percent,
        direction=request.direction,
        entry_price=100,
        stop_loss=100,
        value_per_price_unit=request.value_per_price_unit,
        minimum_position_size=request.minimum_position_size,
        maximum_position_size=request.maximum_position_size,
        position_size_step=request.position_size_step,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == "ZERO_STOP_DISTANCE"

    print("✅ Zero stop distance → BLOCKED")


def test_invalid_value_per_price_unit_blocked():

    engine = RiskEngine()

    request = valid_request()

    request = RiskRequest(
        account_balance=request.account_balance,
        risk_percent=request.risk_percent,
        direction=request.direction,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        value_per_price_unit=0,
        minimum_position_size=request.minimum_position_size,
        maximum_position_size=request.maximum_position_size,
        position_size_step=request.position_size_step,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == "INVALID_VALUE_PER_PRICE_UNIT"

    print("✅ Invalid price-unit value → BLOCKED")


def test_invalid_minimum_position_blocked():

    engine = RiskEngine()

    request = valid_request()

    request = RiskRequest(
        account_balance=request.account_balance,
        risk_percent=request.risk_percent,
        direction=request.direction,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        value_per_price_unit=request.value_per_price_unit,
        minimum_position_size=0,
        maximum_position_size=request.maximum_position_size,
        position_size_step=request.position_size_step,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == (
        "INVALID_MINIMUM_POSITION_SIZE"
    )

    print("✅ Invalid minimum position → BLOCKED")


def test_invalid_position_limits_blocked():

    engine = RiskEngine()

    request = valid_request()

    request = RiskRequest(
        account_balance=request.account_balance,
        risk_percent=request.risk_percent,
        direction=request.direction,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        value_per_price_unit=request.value_per_price_unit,
        minimum_position_size=10,
        maximum_position_size=1,
        position_size_step=request.position_size_step,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == (
        "INVALID_POSITION_SIZE_LIMITS"
    )

    print("✅ Invalid position limits → BLOCKED")


def test_invalid_position_step_blocked():

    engine = RiskEngine()

    request = valid_request()

    request = RiskRequest(
        account_balance=request.account_balance,
        risk_percent=request.risk_percent,
        direction=request.direction,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        value_per_price_unit=request.value_per_price_unit,
        minimum_position_size=request.minimum_position_size,
        maximum_position_size=request.maximum_position_size,
        position_size_step=0,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == (
        "INVALID_POSITION_SIZE_STEP"
    )

    print("✅ Invalid position step → BLOCKED")


def test_position_below_minimum_blocked():

    engine = RiskEngine()

    request = RiskRequest(
        account_balance=100,
        risk_percent=1.0,
        direction="BUY",
        entry_price=100,
        stop_loss=90,
        value_per_price_unit=1.0,
        minimum_position_size=1.0,
        maximum_position_size=10.0,
        position_size_step=0.1,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == (
        "CALCULATED_POSITION_BELOW_MINIMUM"
    )

    print("✅ Position below minimum → BLOCKED")


def test_position_above_maximum_blocked():

    engine = RiskEngine()

    request = RiskRequest(
        account_balance=10_000,
        risk_percent=5.0,
        direction="BUY",
        entry_price=100,
        stop_loss=99,
        value_per_price_unit=1.0,
        minimum_position_size=0.01,
        maximum_position_size=1.0,
        position_size_step=0.01,
    )

    result = engine.calculate(request)

    assert result.allowed is False
    assert result.reason == (
        "CALCULATED_POSITION_ABOVE_MAXIMUM"
    )

    print("✅ Position above maximum → BLOCKED")


def test_position_size_rounds_down():

    engine = RiskEngine()

    request = RiskRequest(
        account_balance=10_000,
        risk_percent=1.0,
        direction="BUY",
        entry_price=100,
        stop_loss=98,
        value_per_price_unit=1.0,
        minimum_position_size=0.01,
        maximum_position_size=100.0,
        position_size_step=0.03,
    )

    result = engine.calculate(request)

    assert result.allowed is True
    assert result.calculated_position_size == 50.0
    assert result.position_size == 49.98

    print("✅ Position size rounds down correctly")


def test_missing_request_blocked():

    engine = RiskEngine()

    result = engine.calculate(None)

    assert result.allowed is False
    assert result.reason == "RISK_REQUEST_UNAVAILABLE"

    print("✅ Missing risk request → BLOCKED")


def main():

    print()
    print("=== APEX Risk Engine Test Suite ===")
    print()

    test_valid_risk_calculation()
    test_valid_sell_risk_calculation()

    test_zero_balance_blocked()
    test_negative_balance_blocked()

    test_zero_risk_blocked()
    test_risk_above_100_percent_blocked()

    test_invalid_direction_blocked()

    test_invalid_entry_blocked()
    test_invalid_stop_blocked()

    test_buy_stop_above_entry_blocked()
    test_sell_stop_below_entry_blocked()

    test_zero_stop_distance_blocked()

    test_invalid_value_per_price_unit_blocked()

    test_invalid_minimum_position_blocked()
    test_invalid_position_limits_blocked()
    test_invalid_position_step_blocked()

    test_position_below_minimum_blocked()
    test_position_above_maximum_blocked()

    test_position_size_rounds_down()

    test_missing_request_blocked()

    print()
    print("===================================")
    print("✅ ALL RISK ENGINE TESTS PASSED")
    print("===================================")


if __name__ == "__main__":
    main()
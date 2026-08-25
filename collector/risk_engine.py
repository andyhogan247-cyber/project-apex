from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN


@dataclass(frozen=True)
class RiskRequest:
    account_balance: float
    risk_percent: float

    direction: str
    entry_price: float
    stop_loss: float

    value_per_price_unit: float

    minimum_position_size: float
    maximum_position_size: float
    position_size_step: float


@dataclass(frozen=True)
class RiskResult:
    allowed: bool
    reason: str

    maximum_risk_amount: float
    stop_distance: float
    calculated_position_size: float
    position_size: float

    checks: dict


class RiskEngine:

    def calculate(
        self,
        request: RiskRequest,
    ) -> RiskResult:

        checks = {}

        if request is None:
            return self._block(
                "RISK_REQUEST_UNAVAILABLE",
                checks,
            )

        if request.account_balance <= 0:
            checks["account_balance"] = "FAIL"

            return self._block(
                "INVALID_ACCOUNT_BALANCE",
                checks,
            )

        checks["account_balance"] = "PASS"

        if (
            request.risk_percent <= 0
            or request.risk_percent > 100
        ):
            checks["risk_percent"] = "FAIL"

            return self._block(
                "INVALID_RISK_PERCENT",
                checks,
            )

        checks["risk_percent"] = "PASS"

        direction = request.direction.upper()

        if direction not in ("BUY", "SELL"):
            checks["direction"] = "FAIL"

            return self._block(
                "INVALID_DIRECTION",
                checks,
            )

        checks["direction"] = "PASS"

        if request.entry_price <= 0:
            checks["entry_price"] = "FAIL"

            return self._block(
                "INVALID_ENTRY_PRICE",
                checks,
            )

        checks["entry_price"] = "PASS"

        if request.stop_loss <= 0:
            checks["stop_loss"] = "FAIL"

            return self._block(
                "INVALID_STOP_LOSS",
                checks,
            )

        checks["stop_loss"] = "PASS"

        # Calculate stop distance before checking direction.
        # This gives zero-distance stops their own explicit
        # validation result.
        stop_distance = abs(
            request.entry_price
            - request.stop_loss
        )

        if stop_distance <= 0:
            checks["stop_distance"] = "FAIL"

            return self._block(
                "ZERO_STOP_DISTANCE",
                checks,
            )

        checks["stop_distance"] = "PASS"

        if direction == "BUY":
            if request.stop_loss >= request.entry_price:
                checks["stop_direction"] = "FAIL"

                return self._block(
                    "BUY_STOP_MUST_BE_BELOW_ENTRY",
                    checks,
                )

        if direction == "SELL":
            if request.stop_loss <= request.entry_price:
                checks["stop_direction"] = "FAIL"

                return self._block(
                    "SELL_STOP_MUST_BE_ABOVE_ENTRY",
                    checks,
                )

        checks["stop_direction"] = "PASS"

        if request.value_per_price_unit <= 0:
            checks["value_per_price_unit"] = "FAIL"

            return self._block(
                "INVALID_VALUE_PER_PRICE_UNIT",
                checks,
            )

        checks["value_per_price_unit"] = "PASS"

        if request.minimum_position_size <= 0:
            checks["minimum_position_size"] = "FAIL"

            return self._block(
                "INVALID_MINIMUM_POSITION_SIZE",
                checks,
            )

        checks["minimum_position_size"] = "PASS"

        if (
            request.maximum_position_size
            < request.minimum_position_size
        ):
            checks["maximum_position_size"] = "FAIL"

            return self._block(
                "INVALID_POSITION_SIZE_LIMITS",
                checks,
            )

        checks["maximum_position_size"] = "PASS"

        if request.position_size_step <= 0:
            checks["position_size_step"] = "FAIL"

            return self._block(
                "INVALID_POSITION_SIZE_STEP",
                checks,
            )

        checks["position_size_step"] = "PASS"

        maximum_risk_amount = (
            request.account_balance
            * request.risk_percent
            / 100
        )

        calculated_position_size = (
            maximum_risk_amount
            / (
                stop_distance
                * request.value_per_price_unit
            )
        )

        # Use Decimal so position-size rounding is
        # deterministic and always rounds DOWN.
        calculated_decimal = Decimal(
            str(calculated_position_size)
        )

        step_decimal = Decimal(
            str(request.position_size_step)
        )

        position_size_decimal = (
            calculated_decimal
            / step_decimal
        ).to_integral_value(
            rounding=ROUND_DOWN
        ) * step_decimal

        position_size = float(
            position_size_decimal
        )

        if position_size < request.minimum_position_size:
            checks["position_size"] = "FAIL"

            return RiskResult(
                allowed=False,
                reason="CALCULATED_POSITION_BELOW_MINIMUM",
                maximum_risk_amount=maximum_risk_amount,
                stop_distance=stop_distance,
                calculated_position_size=calculated_position_size,
                position_size=position_size,
                checks=checks,
            )

        if position_size > request.maximum_position_size:
            checks["position_size"] = "FAIL"

            return RiskResult(
                allowed=False,
                reason="CALCULATED_POSITION_ABOVE_MAXIMUM",
                maximum_risk_amount=maximum_risk_amount,
                stop_distance=stop_distance,
                calculated_position_size=calculated_position_size,
                position_size=position_size,
                checks=checks,
            )

        checks["position_size"] = "PASS"

        return RiskResult(
            allowed=True,
            reason="RISK_CHECKS_PASSED",
            maximum_risk_amount=maximum_risk_amount,
            stop_distance=stop_distance,
            calculated_position_size=calculated_position_size,
            position_size=position_size,
            checks=checks,
        )

    def _block(
        self,
        reason,
        checks,
    ):
        return RiskResult(
            allowed=False,
            reason=reason,
            maximum_risk_amount=0.0,
            stop_distance=0.0,
            calculated_position_size=0.0,
            position_size=0.0,
            checks=checks,
        )
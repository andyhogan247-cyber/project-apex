from dataclasses import dataclass


@dataclass(frozen=True)
class TradeRequest:
    symbol: str
    direction: str
    entry_price: float
    bid: float
    ask: float
    spread: float


@dataclass(frozen=True)
class TradeGateResult:
    allowed: bool
    reason: str
    checks: dict


class TradingGate:

    def __init__(
        self,
        symbol="XAUUSD",
        max_spread=1.00,
    ):
        self.symbol = symbol
        self.max_spread = max_spread

    def evaluate(
        self,
        request: TradeRequest,
        session_status,
        market_health,
    ) -> TradeGateResult:

        checks = {}

        # --------------------------------------------------
        # Session
        # --------------------------------------------------

        if session_status is None:
            checks["session"] = "FAIL"
            return self._block(
                "SESSION_STATUS_UNAVAILABLE",
                checks,
            )

        if session_status.state != "OPEN":
            checks["session"] = "FAIL"
            return self._block(
                f"SESSION_NOT_OPEN:{session_status.state}",
                checks,
            )

        if not session_status.trading_allowed:
            checks["session"] = "FAIL"
            return self._block(
                "TRADING_NOT_ALLOWED_BY_SESSION",
                checks,
            )

        checks["session"] = "PASS"

        # --------------------------------------------------
        # Market health
        # --------------------------------------------------

        if market_health is None:
            checks["market_health"] = "FAIL"
            return self._block(
                "MARKET_HEALTH_UNAVAILABLE",
                checks,
            )

        if market_health.get("status") != "HEALTHY":
            checks["market_health"] = "FAIL"
            return self._block(
                f"MARKET_HEALTH_{market_health.get('status')}",
                checks,
            )

        checks["market_health"] = "PASS"

        # --------------------------------------------------
        # Request validation
        # --------------------------------------------------

        if request is None:
            checks["request"] = "FAIL"
            return self._block(
                "TRADE_REQUEST_UNAVAILABLE",
                checks,
            )

        if request.symbol != self.symbol:
            checks["symbol"] = "FAIL"
            return self._block(
                "SYMBOL_MISMATCH",
                checks,
            )

        checks["symbol"] = "PASS"

        direction = request.direction.upper()

        if direction not in ("BUY", "SELL"):
            checks["direction"] = "FAIL"
            return self._block(
                "INVALID_DIRECTION",
                checks,
            )

        checks["direction"] = "PASS"

        # --------------------------------------------------
        # Price validation
        # --------------------------------------------------

        if request.entry_price <= 0:
            checks["entry_price"] = "FAIL"
            return self._block(
                "INVALID_ENTRY_PRICE",
                checks,
            )

        checks["entry_price"] = "PASS"

        if request.bid <= 0:
            checks["bid"] = "FAIL"
            return self._block(
                "INVALID_BID",
                checks,
            )

        if request.ask <= 0:
            checks["ask"] = "FAIL"
            return self._block(
                "INVALID_ASK",
                checks,
            )

        if request.ask < request.bid:
            checks["price_relationship"] = "FAIL"
            return self._block(
                "ASK_BELOW_BID",
                checks,
            )

        checks["bid"] = "PASS"
        checks["ask"] = "PASS"
        checks["price_relationship"] = "PASS"

        # --------------------------------------------------
        # Spread validation
        # --------------------------------------------------

        if request.spread < 0:
            checks["spread"] = "FAIL"
            return self._block(
                "NEGATIVE_SPREAD",
                checks,
            )

        if request.spread > self.max_spread:
            checks["spread"] = "FAIL"
            return self._block(
                "SPREAD_TOO_WIDE",
                checks,
            )

        checks["spread"] = "PASS"

        # --------------------------------------------------
        # All checks passed
        # --------------------------------------------------

        return TradeGateResult(
            allowed=True,
            reason="ALL_TRADING_GATE_CHECKS_PASSED",
            checks=checks,
        )

    def _block(
        self,
        reason,
        checks,
    ):
        return TradeGateResult(
            allowed=False,
            reason=reason,
            checks=checks,
        )
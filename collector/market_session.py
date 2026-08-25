from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class MarketSessionStatus:
    state: str
    trading_allowed: bool
    reason: str


class MarketSessionManager:

    def __init__(
        self,
        trading_start=time(6, 0),
        trading_end=time(18, 0),
    ):
        self.trading_start = trading_start
        self.trading_end = trading_end

    def get_status(self, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()

        weekday = timestamp.weekday()
        current_time = timestamp.time()

        # Saturday
        if weekday == 5:
            return MarketSessionStatus(
                state="MARKET_CLOSED",
                trading_allowed=False,
                reason="Saturday market closure",
            )

        # Sunday
        if weekday == 6:
            return MarketSessionStatus(
                state="MARKET_CLOSED",
                trading_allowed=False,
                reason="Sunday market closure",
            )

        # Outside APEX trading window
        if current_time < self.trading_start:
            return MarketSessionStatus(
                state="SESSION_CLOSED",
                trading_allowed=False,
                reason="Before APEX trading session",
            )

        if current_time >= self.trading_end:
            return MarketSessionStatus(
                state="SESSION_CLOSED",
                trading_allowed=False,
                reason="After APEX trading session",
            )

        return MarketSessionStatus(
            state="OPEN",
            trading_allowed=True,
            reason="Market and APEX trading session open",
        )

    def is_trading_allowed(self, timestamp=None):
        return self.get_status(
            timestamp
        ).trading_allowed
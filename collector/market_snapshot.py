from dataclasses import dataclass
from datetime import datetime


@dataclass
class MarketSnapshot:
    timestamp: datetime
    symbol: str

    bid: float
    ask: float
    mid: float
    spread: float

    m1_open: float
    m1_high: float
    m1_low: float
    m1_close: float

    volume: float | None

    timeframe: str
    source: str
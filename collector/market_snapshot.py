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

    volume: float | None

    timeframe: str
    source: str
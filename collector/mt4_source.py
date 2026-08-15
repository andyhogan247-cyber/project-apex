from datetime import datetime
from pathlib import Path

from .market_source import MarketDataSource
from .market_snapshot import MarketSnapshot


class MT4MarketDataSource(MarketDataSource):

    def __init__(self, data_file="data/mt4_market.csv"):
        self.data_file = Path(data_file)

    def get_snapshot(self) -> MarketSnapshot:

        if not self.data_file.exists():
            raise FileNotFoundError(
                f"MT4 market data file not found: {self.data_file}"
            )

        lines = self.data_file.read_text(encoding="utf-8").strip().splitlines()

        if len(lines) < 2:
            raise ValueError("MT4 market data file contains no data")

        values = lines[-1].split(",")

        timestamp = datetime.fromisoformat(values[0])

        bid = float(values[1])
        ask = float(values[2])
        volume = float(values[3])

        mid = (bid + ask) / 2
        spread = ask - bid

        return MarketSnapshot(
            timestamp=timestamp,
            symbol="XAUUSD",
            bid=bid,
            ask=ask,
            mid=mid,
            spread=spread,
            volume=volume,
            timeframe="M1",
            source="MT4"
        )
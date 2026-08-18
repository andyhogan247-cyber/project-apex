from datetime import datetime, timedelta
from pathlib import Path
import os

from .market_source import MarketDataSource
from .market_snapshot import MarketSnapshot


class MT4MarketDataSource(MarketDataSource):

    def __init__(
        self,
        data_file=None,
        server_utc_offset_hours=3,
    ):
        self.server_utc_offset_hours = server_utc_offset_hours

        if data_file:
            self.data_file = Path(data_file)
        else:
            appdata = os.getenv("APPDATA")

            if appdata:
                self.data_file = (
                    Path(appdata)
                    / "MetaQuotes"
                    / "Terminal"
                    / "Common"
                    / "Files"
                    / "APEX"
                    / "xauusd_market.csv"
                )
            else:
                self.data_file = Path("data/mt4_market.csv")

    def get_snapshot(self) -> MarketSnapshot:

        if not self.data_file.exists():
            raise FileNotFoundError(
                f"MT4 market data file not found: {self.data_file}"
            )

        lines = (
            self.data_file
            .read_text(encoding="utf-8")
            .strip()
            .splitlines()
        )

        if len(lines) < 1:
            raise ValueError(
                "MT4 market data file contains no data"
            )

        values = lines[-1].split(",")

        if len(values) < 10:
            raise ValueError(
                "MT4 market data row contains insufficient fields"
            )

        timestamp_text = values[0].strip()

        try:
            server_timestamp = datetime.strptime(
                timestamp_text,
                "%Y.%m.%d %H:%M:%S",
            )
        except ValueError:

            server_timestamp = datetime.fromisoformat(
                timestamp_text
            )

        # MT4 writes broker/server time.
        # Convert it to UTC before storing it in APEX memory.
        timestamp = (
            server_timestamp
            - timedelta(hours=self.server_utc_offset_hours)
        )

        symbol = values[1].strip()

        bid = float(values[2])
        ask = float(values[3])
        spread = float(values[4])

        m1_open = float(values[5])
        m1_high = float(values[6])
        m1_low = float(values[7])
        m1_close = float(values[8])

        volume = float(values[9])

        mid = (bid + ask) / 2

        return MarketSnapshot(
            timestamp=timestamp,
            symbol=symbol,
            bid=bid,
            ask=ask,
            mid=mid,
            spread=spread,
            m1_open=m1_open,
            m1_high=m1_high,
            m1_low=m1_low,
            m1_close=m1_close,
            volume=volume,
            timeframe="M1",
            source="MT4",
        )
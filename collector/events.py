from dataclasses import dataclass
from datetime import datetime


@dataclass
class TradeEvent:

    event_id: str

    signal_id: str | None

    timestamp: datetime

    event_type: str

    value: str | None

    raw_message: str
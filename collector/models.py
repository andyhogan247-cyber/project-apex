from dataclasses import dataclass
from datetime import datetime


@dataclass
class Signal:

    signal_id: str

    timestamp: datetime

    direction: str

    symbol: str

    entry_high: float

    entry_low: float

    stop_loss: float

    tp1: float

    tp2: float

    tp3: float

    open_target: bool

    source: str

    raw_message: str
import re
from datetime import datetime
from uuid import uuid4

from .models import Signal


def parse_signal(message: str):

    original_message = message
    message = message.upper()

    direction = "BUY" if "BUY" in message else "SELL"

    entries = re.search(r'@\s*(\d+\.?\d*)/(\d+\.?\d*)', message)
    tps = re.findall(r'TP\s+(\d+\.?\d*)', message)
    sl = re.search(r'SL\s+(\d+\.?\d*)', message)

    if not entries:
        raise ValueError("Entry prices not found")

    if not sl:
        raise ValueError("Stop loss not found")

    if len(tps) < 3:
        raise ValueError("Not enough TP levels found")

    open_target = "TP OPEN" in message

    return Signal(
        signal_id=str(uuid4()),
        timestamp=datetime.now(),
        direction=direction,
        symbol="XAUUSD",
        entry_high=float(entries.group(1)),
        entry_low=float(entries.group(2)),
        stop_loss=float(sl.group(1)),
        tp1=float(tps[0]),
        tp2=float(tps[1]),
        tp3=float(tps[2]),
        open_target=open_target,
        source="Telegram",
        raw_message=original_message
    )
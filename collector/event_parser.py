import re
from datetime import datetime
from uuid import uuid4

from .events import TradeEvent


def parse_event(message: str):

    original_message = message
    text = message.upper()

    event_type = None
    value = None

    if "STOP LOSS" in text:
        event_type = "STOP_LOSS"

    elif "TP1" in text:
        event_type = "TP1"

    elif "TP2" in text:
        event_type = "TP2"

    elif "TP3" in text:
        event_type = "TP3"

    elif "BREAK EVEN" in text or "BE" in text:
        event_type = "MOVE_TO_BREAKEVEN"

    elif "PARTIAL" in text or "CASH ANOTHER PARTIAL" in text:
        event_type = "TAKE_PARTIAL"

    elif "OPEN TP" in text:
        event_type = "RUNNER_UPDATE"

        match = re.search(r"\+(\d+)\s*PIPS", text)
        if match:
            value = match.group(1)

    if event_type is None:
        return None

    return TradeEvent(
        event_id=str(uuid4()),
        signal_id=None,          # we'll link this later
        timestamp=datetime.now(),
        event_type=event_type,
        value=value,
        raw_message=original_message
    )
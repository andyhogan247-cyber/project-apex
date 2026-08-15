from collector.event_parser import parse_event
from database.repository import SignalRepository

message = """
TP2 🔥
Let's cash a partial and leave the remainder to run risk free
"""

event = parse_event(message)

repo = SignalRepository()

repo.save_event(event)

repo.close()
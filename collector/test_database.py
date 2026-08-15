from collector.parser import parse_signal
from database.repository import SignalRepository

msg = """
BUY GOLD @ 4169/4162

TP 4173
TP 4176
TP 4183
TP OPEN

SL 4161

HIGH RISK TRADE
"""

signal = parse_signal(msg)

repo = SignalRepository()

repo.save_signal(signal)

repo.close()

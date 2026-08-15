from datetime import datetime
from models import Signal

signal = Signal(
    signal_id="TEST001",
    timestamp=datetime.now(),
    direction="BUY",
    symbol="XAUUSD",
    entry_high=4169,
    entry_low=4162,
    stop_loss=4161,
    tp1=4173,
    tp2=4176,
    tp3=4183,
    open_target=True,
    source="Telegram",
    raw_message="BUY GOLD @ 4169/4162"
)

print(signal)
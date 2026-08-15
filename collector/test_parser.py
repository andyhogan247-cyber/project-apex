from parser import parse_signal

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

print(signal)
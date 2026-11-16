"""Telegram listener: saves gold signals from the channel(s) and sends each one to the committee.

Needs in .env (from https://my.telegram.org -> API development tools):
    TG_API_ID=12345
    TG_API_HASH=abcdef...
    TG_CHANNELS=channel_username_or_id[,another]
The first run asks for your phone number and the login code Telegram sends you; the
session is then kept in apex_listener.session (never share or commit that file).

Run from the project folder:   python -m collector.telegram_listener
"""

import asyncio
import os
import sqlite3
from datetime import timezone
from pathlib import Path

from collector.parser import parse_signal
from desk import gold_desk

ROOT = Path(__file__).resolve().parents[1]


def save(signal, db=None):
    """Insert the parsed signal (UTC timestamp). Returns False if it was already stored."""
    with sqlite3.connect(db or gold_desk.DB) as con:
        con.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
        try:
            con.execute(
                "INSERT INTO signals (signal_id, timestamp, direction, symbol, entry_high, entry_low, stop_loss, "
                "tp1, tp2, tp3, open_target, source, raw_message) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (signal.signal_id, signal.timestamp.isoformat(timespec="seconds"), signal.direction, signal.symbol,
                 signal.entry_high, signal.entry_low, signal.stop_loss, signal.tp1, signal.tp2, signal.tp3,
                 int(signal.open_target), signal.source, signal.raw_message))
            return True
        except sqlite3.IntegrityError:
            return False


def handle_text(text, when_utc, source, db=None, post=None):
    """Parse one message; if it is a signal, store it and run the committee. -> decision or None."""
    try:
        sig = parse_signal(text or "")
    except (ValueError, IndexError):
        return None                      # chat, results, updates: not a new signal
    sig.timestamp = when_utc.astimezone(timezone.utc).replace(tzinfo=None)
    sig.source = source
    sig.signal_id = f"{source}:{int(when_utc.timestamp())}"
    if not save(sig, db):
        return None
    return gold_desk.sweep(db, post).get(sig.signal_id)


def main():
    from telethon import TelegramClient, events

    gold_desk._load_env()
    api_id, api_hash = os.getenv("TG_API_ID"), os.getenv("TG_API_HASH")
    chans = [c.strip() for c in os.getenv("TG_CHANNELS", "").split(",") if c.strip()]
    if not (api_id and api_hash and chans):
        raise SystemExit("Set TG_API_ID, TG_API_HASH and TG_CHANNELS in .env first.")
    chans = [int(c) if c.lstrip("-").isdigit() else c for c in chans]
    client = TelegramClient(str(ROOT / "apex_listener"), int(api_id), api_hash)

    @client.on(events.NewMessage(chats=chans))
    async def on_message(event):
        src = str(getattr(event.chat, "username", None) or event.chat_id)
        decision = await asyncio.to_thread(handle_text, event.raw_text, event.message.date, src)
        if decision:
            print(f"{event.message.date:%H:%M:%S} signal from {src}: committee {decision}")

    async def background():
        while True:   # grading + dashboard even when no signals arrive
            await asyncio.to_thread(gold_desk.sweep)
            await asyncio.sleep(60)

    print(f"Listening to {chans}. Committee: {gold_desk.committee().status}. Dashboard: {gold_desk.HTML}")
    client.start()
    client.loop.create_task(background())
    client.run_until_disconnected()


if __name__ == "__main__":
    main()

import sqlite3

DATABASE = "database/apex.db"


class SignalRepository:

    def __init__(self):
        self.conn = sqlite3.connect(DATABASE)
        self.cursor = self.conn.cursor()

    def save_signal(self, signal):

        try:
            self.cursor.execute("""
            INSERT INTO signals (
                signal_id,
                timestamp,
                direction,
                symbol,
                entry_high,
                entry_low,
                stop_loss,
                tp1,
                tp2,
                tp3,
                open_target,
                source,
                raw_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.signal_id,
                signal.timestamp.isoformat(),
                signal.direction,
                signal.symbol,
                signal.entry_high,
                signal.entry_low,
                signal.stop_loss,
                signal.tp1,
                signal.tp2,
                signal.tp3,
                int(signal.open_target),
                signal.source,
                signal.raw_message
            ))

            self.conn.commit()

            print(f"✅ Saved signal {signal.signal_id}")

        except sqlite3.IntegrityError:
            print(f"⚠ Signal already exists: {signal.signal_id}")

    def save_event(self, event):

        self.cursor.execute("""
        INSERT INTO trade_events (
            event_id,
            signal_id,
            timestamp,
            event_type,
            value,
            raw_message
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.signal_id,
            event.timestamp.isoformat(),
            event.event_type,
            event.value,
            event.raw_message
        ))

        self.conn.commit()

        print(f"✅ Saved event {event.event_type}")

    def close(self):
        self.conn.close()
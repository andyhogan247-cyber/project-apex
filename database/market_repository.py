import sqlite3
from datetime import datetime, timedelta

from collector.market_snapshot import MarketSnapshot


DATABASE = "database/apex.db"


class MarketRepository:

    def __init__(self):
        self.conn = sqlite3.connect(DATABASE)
        self.cursor = self.conn.cursor()

    def save_snapshot(self, snapshot: MarketSnapshot):

        self.cursor.execute("""
        INSERT OR IGNORE INTO market_snapshots (
            timestamp,
            symbol,
            bid,
            ask,
            mid,
            spread,
            volume,
            timeframe,
            source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot.timestamp.isoformat(),
            snapshot.symbol,
            snapshot.bid,
            snapshot.ask,
            snapshot.mid,
            snapshot.spread,
            snapshot.volume,
            snapshot.timeframe,
            snapshot.source
        ))

        self.conn.commit()

        print(
            f"✅ Saved market snapshot "
            f"{snapshot.symbol} "
            f"{snapshot.timestamp.isoformat()}"
        )

    def snapshot_exists(
        self,
        timestamp,
        symbol="XAUUSD",
        timeframe="M1",
    ):
        """Check whether a snapshot already exists."""

        cursor = self.cursor.execute("""
        SELECT 1
        FROM market_snapshots
        WHERE timestamp = ?
        AND symbol = ?
        AND timeframe = ?
        LIMIT 1
        """, (
            timestamp.isoformat(),
            symbol,
            timeframe,
        ))

        return cursor.fetchone() is not None

    def get_snapshots_between(
        self,
        start_time,
        end_time,
        symbol="XAUUSD",
        timeframe="M1",
    ):
        """Return snapshots between two timestamps."""

        cursor = self.cursor.execute("""
        SELECT timestamp
        FROM market_snapshots
        WHERE timestamp >= ?
        AND timestamp <= ?
        AND symbol = ?
        AND timeframe = ?
        ORDER BY timestamp
        """, (
            start_time.isoformat(),
            end_time.isoformat(),
            symbol,
            timeframe,
        ))

        return cursor.fetchall()

    def find_missing_minutes(
        self,
        start_time,
        end_time,
        symbol="XAUUSD",
        timeframe="M1",
    ):
        """Find missing one-minute observations."""

        rows = self.get_snapshots_between(
            start_time,
            end_time,
            symbol,
            timeframe,
        )

        existing = {
            datetime.fromisoformat(row[0])
            for row in rows
        }

        missing = []

        current = start_time

        while current <= end_time:

            if current not in existing:
                missing.append(current)

            current += timedelta(minutes=1)

        return missing

    def close(self):
        self.conn.close()
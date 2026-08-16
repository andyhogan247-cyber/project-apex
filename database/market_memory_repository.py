import sqlite3

from collector.market_snapshot import MarketSnapshot


DATABASE = "database/apex.db"


class MarketMemoryRepository:

    def __init__(self):
        self.conn = sqlite3.connect(DATABASE)
        self.conn.row_factory = sqlite3.Row

    def save_observation(self, snapshot: MarketSnapshot):

        cursor = self.conn.execute(
            """
            INSERT OR IGNORE INTO market_observations (
                timestamp,
                symbol,
                bid,
                ask,
                mid,
                spread,
                m1_open,
                m1_high,
                m1_low,
                m1_close,
                tick_volume,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.timestamp.isoformat(),
                snapshot.symbol,
                snapshot.bid,
                snapshot.ask,
                snapshot.mid,
                snapshot.spread,
                snapshot.m1_open,
                snapshot.m1_high,
                snapshot.m1_low,
                snapshot.m1_close,
                snapshot.volume,
                snapshot.source,
            ),
        )

        self.conn.commit()

        return cursor.rowcount > 0

    def save_snapshot(self, snapshot: MarketSnapshot):
        """Compatibility alias for the existing collector."""
        return self.save_observation(snapshot)

    def observation_exists(
        self,
        timestamp,
        symbol="XAUUSD",
        source="MT4",
    ):

        cursor = self.conn.execute(
            """
            SELECT 1
            FROM market_observations
            WHERE timestamp = ?
            AND symbol = ?
            AND source = ?
            LIMIT 1
            """,
            (
                timestamp.isoformat(),
                symbol,
                source,
            ),
        )

        return cursor.fetchone() is not None

    def count_observations(self, symbol="XAUUSD"):

        cursor = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM market_observations
            WHERE symbol = ?
            """,
            (symbol,),
        )

        return cursor.fetchone()[0]

    def latest_observation(self, symbol="XAUUSD"):

        cursor = self.conn.execute(
            """
            SELECT *
            FROM market_observations
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (symbol,),
        )

        return cursor.fetchone()

    def get_range(
        self,
        start_time,
        end_time,
        symbol="XAUUSD",
    ):

        cursor = self.conn.execute(
            """
            SELECT *
            FROM market_observations
            WHERE timestamp >= ?
            AND timestamp <= ?
            AND symbol = ?
            ORDER BY timestamp
            """,
            (
                start_time.isoformat(),
                end_time.isoformat(),
                symbol,
            ),
        )

        return cursor.fetchall()

    def close(self):
        self.conn.close()
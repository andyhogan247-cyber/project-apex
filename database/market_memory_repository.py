import sqlite3

from collector.market_snapshot import MarketSnapshot


DATABASE = "database/apex.db"


class MarketMemoryRepository:

    def __init__(self):
        self.conn = sqlite3.connect(DATABASE)
        self.conn.row_factory = sqlite3.Row

    def save_observation(self, snapshot: MarketSnapshot):

        cursor = self.conn.cursor()

        cursor.execute(
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

    def get_latest(self, symbol="XAUUSD"):

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

    def close(self):

        self.conn.close()
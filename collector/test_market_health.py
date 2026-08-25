import sqlite3
from datetime import datetime, timedelta, timezone

from collector.market_health import MarketHealthMonitor


TEST_DATABASE = "database/test_market_health.db"
def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_database():
    conn = sqlite3.connect(TEST_DATABASE)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS market_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            bid REAL NOT NULL,
            ask REAL NOT NULL,
            mid REAL NOT NULL,
            spread REAL NOT NULL,
            m1_open REAL NOT NULL,
            m1_high REAL NOT NULL,
            m1_low REAL NOT NULL,
            m1_close REAL NOT NULL,
            tick_volume REAL NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    return conn


class TestRepository:

    def __init__(self, conn):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

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


def insert_observation(
    conn,
    timestamp,
    source="MT4",
    symbol="XAUUSD",
    bid=4500.00,
    ask=4500.50,
    spread=0.50,
):
    mid = (bid + ask) / 2

    conn.execute(
        """
        INSERT INTO market_observations (
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
            timestamp.isoformat(),
            symbol,
            bid,
            ask,
            mid,
            spread,
            bid,
            ask,
            bid,
            mid,
            100,
            source,
        ),
    )

    conn.commit()


def reset_database(conn):
    conn.execute("DELETE FROM market_observations")
    conn.commit()


def test_no_mt4_data(conn, repository):
    reset_database(conn)

    monitor = MarketHealthMonitor(
        repository=repository,
        source="MT4",
    )

    result = monitor.run()

    assert result["status"] == "FAILED"
    assert (
        result["checks"]["freshness"]["status"]
        == "FAILED"
    )

    print("✅ No MT4 data → FAILED")


def test_fresh_mt4_data(conn, repository):
    reset_database(conn)

    now = utc_now()

    insert_observation(
        conn,
        now,
        source="MT4",
    )

    monitor = MarketHealthMonitor(
        repository=repository,
        source="MT4",
        max_age_seconds=120,
        degraded_age_seconds=60,
    )

    result = monitor.run()

    assert (
        result["checks"]["freshness"]["status"]
        == "HEALTHY"
    )

    print("✅ Fresh MT4 data → HEALTHY freshness")


def test_degraded_freshness(conn, repository):
    reset_database(conn)

    timestamp = utc_now() - timedelta(
        seconds=90
    )

    insert_observation(
        conn,
        timestamp,
        source="MT4",
    )

    monitor = MarketHealthMonitor(
        repository=repository,
        source="MT4",
        max_age_seconds=120,
        degraded_age_seconds=60,
    )

    result = monitor.run()

    assert (
        result["checks"]["freshness"]["status"]
        == "DEGRADED"
    )

    assert result["status"] == "DEGRADED"

    print("✅ 90-second-old MT4 data → DEGRADED")


def test_stale_data(conn, repository):
    reset_database(conn)

    timestamp = utc_now() - timedelta(
        minutes=5
    )

    insert_observation(
        conn,
        timestamp,
        source="MT4",
    )

    monitor = MarketHealthMonitor(
        repository=repository,
        source="MT4",
        max_age_seconds=120,
        degraded_age_seconds=60,
    )

    result = monitor.run()

    assert (
        result["checks"]["freshness"]["status"]
        == "FAILED"
    )

    assert result["status"] == "FAILED"

    print("✅ Stale MT4 data → FAILED")


def test_invalid_prices(conn, repository):
    reset_database(conn)

    insert_observation(
        conn,
        utc_now(),
        source="MT4",
        bid=-1,
        ask=4500,
        spread=4501,
    )

    monitor = MarketHealthMonitor(
        repository=repository,
        source="MT4",
    )

    result = monitor.run()

    assert (
        result["checks"]["latest_values"]["status"]
        == "FAILED"
    )

    assert result["status"] == "FAILED"

    print("✅ Invalid MT4 prices → FAILED")


def test_missing_minutes(conn, repository):
    reset_database(conn)

    now = utc_now().replace(
        second=0,
        microsecond=0,
    )

    for minutes_ago in [0, 1, 2, 4, 5]:
        insert_observation(
            conn,
            now - timedelta(minutes=minutes_ago),
            source="MT4",
        )

    monitor = MarketHealthMonitor(
        repository=repository,
        source="MT4",
    )

    result = monitor.run(
        lookback_minutes=5
    )

    continuity = result[
        "checks"
    ]["minute_continuity"]

    assert continuity["status"] == "DEGRADED"
    assert len(
        continuity["missing_minutes"]
    ) >= 1

    print("✅ Missing M1 minute → DEGRADED")


def test_duplicate_observations(conn, repository):
    reset_database(conn)

    timestamp = utc_now().replace(
        microsecond=0
    )

    insert_observation(
        conn,
        timestamp,
        source="MT4",
    )

    insert_observation(
        conn,
        timestamp,
        source="MT4",
    )

    monitor = MarketHealthMonitor(
        repository=repository,
        source="MT4",
    )

    result = monitor.run()

    duplicates = result[
        "checks"
    ]["duplicates"]

    assert duplicates["status"] == "DEGRADED"
    assert len(
        duplicates["duplicates"]
    ) >= 1

    print("✅ Duplicate MT4 observation → DEGRADED")


def test_test_source_is_ignored(conn, repository):
    reset_database(conn)

    old_timestamp = utc_now() - timedelta(
        days=7
    )

    insert_observation(
        conn,
        old_timestamp,
        source="TEST",
    )

    insert_observation(
        conn,
        utc_now(),
        source="MT4",
    )

    monitor = MarketHealthMonitor(
        repository=repository,
        source="MT4",
    )

    latest = monitor.get_latest()

    assert latest is not None
    assert latest["source"] == "MT4"

    print("✅ TEST observations ignored by MT4 monitor")


def test_healthy_overall_status(conn, repository):
    reset_database(conn)

    now = datetime(
        2026,
        8,
        21,
        10,
        30,
    )

    for minutes_ago in range(11):
        insert_observation(
            conn,
            now - timedelta(minutes=minutes_ago),
            source="MT4",
        )

    monitor = MarketHealthMonitor(
        repository=repository,
        source="MT4",
        max_age_seconds=120,
        degraded_age_seconds=60,
    )

    result = monitor.run(
        lookback_minutes=10,
        timestamp=datetime(
            2026,
            8,
            21,
            10,
            30,
        ),
    )

    assert result["status"] == "HEALTHY"

    assert result["checks"]["session"]["status"] == "OPEN"

    for name, check in result["checks"].items():
        if name != "session":
            assert check["status"] == "HEALTHY"

    print("✅ Complete healthy MT4 feed → HEALTHY")



def main():
    conn = create_database()
    repository = TestRepository(conn)

    print()
    print("=== APEX Market Health Test Suite ===")
    print()

    test_no_mt4_data(
        conn,
        repository,
    )

    test_fresh_mt4_data(
        conn,
        repository,
    )

    test_degraded_freshness(
        conn,
        repository,
    )

    test_stale_data(
        conn,
        repository,
    )

    test_invalid_prices(
        conn,
        repository,
    )

    test_missing_minutes(
        conn,
        repository,
    )

    test_duplicate_observations(
        conn,
        repository,
    )

    test_test_source_is_ignored(
        conn,
        repository,
    )

    test_healthy_overall_status(
        conn,
        repository,
    )

    conn.close()

    print()
    print("===================================")
    print("✅ ALL MARKET HEALTH TESTS PASSED")
    print("===================================")


if __name__ == "__main__":
    main()
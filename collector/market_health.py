from datetime import datetime, timedelta, timezone

from database.market_memory_repository import MarketMemoryRepository


class MarketHealthMonitor:

    def __init__(
        self,
        repository: MarketMemoryRepository,
        symbol="XAUUSD",
        source="MT4",
        max_age_seconds=120,
        degraded_age_seconds=60,
    ):
        self.repository = repository
        self.symbol = symbol
        self.source = source
        self.max_age_seconds = max_age_seconds
        self.degraded_age_seconds = degraded_age_seconds

    def _now_utc(self):
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _parse_timestamp(self, value):
        return datetime.fromisoformat(value)

    def get_latest(self):
        cursor = self.repository.conn.execute(
            """
            SELECT *
            FROM market_observations
            WHERE symbol = ?
            AND source = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (
                self.symbol,
                self.source,
            ),
        )

        return cursor.fetchone()

    def check_freshness(self):
        latest = self.get_latest()

        if latest is None:
            return {
                "status": "FAILED",
                "reason": "No market observations found",
                "age_seconds": None,
            }

        timestamp = self._parse_timestamp(
            latest["timestamp"]
        )

        age_seconds = (
            self._now_utc() - timestamp
        ).total_seconds()

        if age_seconds < 0:
            return {
                "status": "FAILED",
                "reason": "Latest observation is in the future",
                "age_seconds": age_seconds,
            }

        if age_seconds > self.max_age_seconds:
            return {
                "status": "FAILED",
                "reason": "Market observation is stale",
                "age_seconds": age_seconds,
            }

        if age_seconds > self.degraded_age_seconds:
            return {
                "status": "DEGRADED",
                "reason": "Market observation is becoming stale",
                "age_seconds": age_seconds,
            }

        return {
            "status": "HEALTHY",
            "reason": "Market observation is fresh",
            "age_seconds": age_seconds,
        }

    def check_latest_values(self):
        latest = self.get_latest()

        if latest is None:
            return {
                "status": "FAILED",
                "reason": "No market observations found",
            }

        bid = latest["bid"]
        ask = latest["ask"]
        mid = latest["mid"]
        spread = latest["spread"]

        if bid <= 0 or ask <= 0 or mid <= 0:
            return {
                "status": "FAILED",
                "reason": "Invalid market price",
            }

        if ask < bid:
            return {
                "status": "FAILED",
                "reason": "Ask price below bid price",
            }

        if spread < 0:
            return {
                "status": "FAILED",
                "reason": "Negative spread",
            }

        return {
            "status": "HEALTHY",
            "reason": "Latest market values valid",
        }

    def check_minute_continuity(
        self,
        lookback_minutes=10,
    ):
        latest = self.get_latest()

        if latest is None:
            return {
                "status": "FAILED",
                "reason": "No market observations found",
                "missing_minutes": [],
            }

        latest_time = self._parse_timestamp(
            latest["timestamp"]
        )

        start_time = (
            latest_time
            - timedelta(minutes=lookback_minutes)
        )

        cursor = self.repository.conn.execute(
            """
            SELECT timestamp
            FROM market_observations
            WHERE timestamp >= ?
            AND timestamp <= ?
            AND symbol = ?
            AND source = ?
            ORDER BY timestamp
            """,
            (
                start_time.isoformat(),
                latest_time.isoformat(),
                self.symbol,
                self.source,
            ),
        )

        observations = cursor.fetchall()

        timestamps = {
            self._parse_timestamp(
                row["timestamp"]
            ).replace(
                second=0,
                microsecond=0,
            )
            for row in observations
        }

        expected = {
            start_time.replace(
                second=0,
                microsecond=0,
            )
            + timedelta(minutes=i)
            for i in range(lookback_minutes + 1)
        }

        missing = sorted(
            expected - timestamps
        )

        if missing:
            return {
                "status": "DEGRADED",
                "reason": "Missing market minutes detected",
                "missing_minutes": [
                    value.isoformat()
                    for value in missing
                ],
            }

        return {
            "status": "HEALTHY",
            "reason": "Market minute continuity is intact",
            "missing_minutes": [],
        }

    def check_duplicates(self):
        cursor = self.repository.conn.execute(
            """
            SELECT timestamp, source, COUNT(*) AS count
            FROM market_observations
            WHERE symbol = ?
            AND source = ?
            GROUP BY timestamp, source
            HAVING COUNT(*) > 1
            """,
            (
                self.symbol,
                self.source,
            ),
        )

        duplicates = cursor.fetchall()

        if duplicates:
            return {
                "status": "DEGRADED",
                "reason": "Duplicate observations detected",
                "duplicates": [
                    {
                        "timestamp": row["timestamp"],
                        "source": row["source"],
                        "count": row["count"],
                    }
                    for row in duplicates
                ],
            }

        return {
            "status": "HEALTHY",
            "reason": "No duplicate observations detected",
            "duplicates": [],
        }

    def check_observation_count(self):
        cursor = self.repository.conn.execute(
            """
            SELECT COUNT(*)
            FROM market_observations
            WHERE symbol = ?
            AND source = ?
            """,
            (
                self.symbol,
                self.source,
            ),
        )

        count = cursor.fetchone()[0]

        if count == 0:
            return {
                "status": "FAILED",
                "reason": "No observations stored",
                "count": count,
            }

        return {
            "status": "HEALTHY",
            "reason": "Market observations are being stored",
            "count": count,
        }

    def run(self, lookback_minutes=10):
        checks = {
            "freshness": self.check_freshness(),
            "latest_values": self.check_latest_values(),
            "minute_continuity": (
                self.check_minute_continuity(
                    lookback_minutes
                )
            ),
            "duplicates": self.check_duplicates(),
            "observation_count": (
                self.check_observation_count()
            ),
        }

        statuses = [
            result["status"]
            for result in checks.values()
        ]

        if "FAILED" in statuses:
            overall_status = "FAILED"
        elif "DEGRADED" in statuses:
            overall_status = "DEGRADED"
        else:
            overall_status = "HEALTHY"

        return {
            "status": overall_status,
            "symbol": self.symbol,
            "source": self.source,
            "checked_at": self._now_utc().isoformat(),
            "checks": checks,
        }
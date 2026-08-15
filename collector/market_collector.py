import time
from datetime import datetime, timedelta

from .market_source import MarketDataSource
from database.market_repository import MarketRepository


class MarketCollector:

    def __init__(
        self,
        source: MarketDataSource,
        repository: MarketRepository,
        interval_seconds: int = 60,
    ):
        self.source = source
        self.repository = repository
        self.interval_seconds = interval_seconds
        self.running = False

        self.successful_collections = 0
        self.failed_collections = 0

    def collect_once(self):
        """Collect and store one market snapshot."""

        snapshot = self.source.get_snapshot()

        self.validate_snapshot(snapshot)

        self.repository.save_snapshot(snapshot)

        self.successful_collections += 1

        print(
            f"📊 {datetime.now().isoformat()} "
            f"| {snapshot.symbol} "
            f"| Bid: {snapshot.bid} "
            f"| Ask: {snapshot.ask}"
        )

        return snapshot

    def validate_snapshot(self, snapshot):
        """Validate a market snapshot before storing it."""

        if snapshot.bid <= 0:
            raise ValueError("Invalid bid price")

        if snapshot.ask <= 0:
            raise ValueError("Invalid ask price")

        if snapshot.ask < snapshot.bid:
            raise ValueError("Ask price cannot be below bid price")

        if snapshot.mid <= 0:
            raise ValueError("Invalid mid price")

        if snapshot.spread < 0:
            raise ValueError("Spread cannot be negative")

        now = datetime.now()

        if snapshot.timestamp > now + timedelta(minutes=1):
            raise ValueError("Snapshot timestamp is in the future")

        if snapshot.timestamp < now - timedelta(minutes=5):
            raise ValueError("Snapshot is stale")

    def get_stats(self):
        """Return collector performance statistics."""

        return {
            "successful_collections": self.successful_collections,
            "failed_collections": self.failed_collections,
            "total_attempts": (
                self.successful_collections
                + self.failed_collections
            ),
        }

    def start(self):
        """Continuously collect market data."""

        self.running = True

        print("🚀 APEX Market Collector starting...")
        print(
            f"⏱ Collection interval: "
            f"{self.interval_seconds} seconds"
        )

        try:
            while self.running:

                try:
                    self.collect_once()

                except Exception as error:
                    self.failed_collections += 1
                    print(f"❌ Collection error: {error}")

                time.sleep(self.interval_seconds)

        except KeyboardInterrupt:
            print("\n🛑 Market Collector stopped")

        finally:
            self.stop()

    def stop(self):
        """Stop the collector and close the repository."""

        self.running = False
        self.repository.close()

        print("✅ Market Collector shutdown complete")
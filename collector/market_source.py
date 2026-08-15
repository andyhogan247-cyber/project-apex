from abc import ABC, abstractmethod

from .market_snapshot import MarketSnapshot


class MarketDataSource(ABC):

    @abstractmethod
    def get_snapshot(self) -> MarketSnapshot:
        """Return the latest market snapshot."""
        raise NotImplementedError
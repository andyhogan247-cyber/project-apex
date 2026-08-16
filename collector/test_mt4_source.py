from collector.mt4_source import MT4MarketDataSource


source = MT4MarketDataSource()

snapshot = source.get_snapshot()

print(snapshot)
from collector.mt4_source import MT4MarketDataSource


source = MT4MarketDataSource(
    data_file="data/mt4_market.csv"
)

snapshot = source.get_snapshot()

print(snapshot)
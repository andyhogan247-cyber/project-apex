CREATE TABLE IF NOT EXISTS signals (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    signal_id TEXT UNIQUE NOT NULL,

    timestamp TEXT NOT NULL,

    direction TEXT NOT NULL,

    symbol TEXT NOT NULL,

    entry_high REAL NOT NULL,

    entry_low REAL NOT NULL,

    stop_loss REAL NOT NULL,

    tp1 REAL NOT NULL,

    tp2 REAL NOT NULL,

    tp3 REAL NOT NULL,

    open_target INTEGER NOT NULL,

    source TEXT NOT NULL,

    raw_message TEXT NOT NULL,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS trade_events (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    event_id TEXT UNIQUE NOT NULL,

    signal_id TEXT,

    timestamp TEXT NOT NULL,

    event_type TEXT NOT NULL,

    value TEXT,

    raw_message TEXT NOT NULL,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(signal_id) REFERENCES signals(signal_id)
);


CREATE TABLE IF NOT EXISTS market_snapshots (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    timestamp TEXT NOT NULL,

    symbol TEXT NOT NULL,

    bid REAL NOT NULL,

    ask REAL NOT NULL,

    mid REAL NOT NULL,

    spread REAL NOT NULL,

    volume REAL,

    timeframe TEXT NOT NULL,

    source TEXT NOT NULL,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(timestamp, symbol, timeframe)
);


CREATE INDEX IF NOT EXISTS idx_market_snapshots_timestamp
ON market_snapshots(timestamp);


CREATE INDEX IF NOT EXISTS idx_market_snapshots_symbol
ON market_snapshots(symbol);


CREATE INDEX IF NOT EXISTS idx_trade_events_signal
ON trade_events(signal_id);
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

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(timestamp, symbol, source)
);


CREATE INDEX IF NOT EXISTS idx_market_observations_timestamp
ON market_observations(timestamp);


CREATE INDEX IF NOT EXISTS idx_market_observations_symbol_timestamp
ON market_observations(symbol, timestamp);
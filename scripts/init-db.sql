-- Initialize YunMin development database

-- Create schemas
CREATE SCHEMA IF NOT EXISTS yunmin;

-- Create trades table
CREATE TABLE IF NOT EXISTS yunmin.trades (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    pnl DECIMAL(20, 8),
    strategy VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create positions table
CREATE TABLE IF NOT EXISTS yunmin.positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    side VARCHAR(10) NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    unrealized_pnl DECIMAL(20, 8),
    opened_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create portfolio history table
CREATE TABLE IF NOT EXISTS yunmin.portfolio_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    total_value DECIMAL(20, 8) NOT NULL,
    cash_balance DECIMAL(20, 8) NOT NULL,
    positions_value DECIMAL(20, 8) NOT NULL,
    daily_pnl DECIMAL(20, 8),
    metadata JSONB
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON yunmin.trades(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON yunmin.trades(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON yunmin.positions(symbol);
CREATE INDEX IF NOT EXISTS idx_portfolio_history_timestamp ON yunmin.portfolio_history(timestamp DESC);

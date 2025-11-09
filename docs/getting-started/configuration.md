# Configuration Guide

## Overview

YunMin uses a combination of environment variables and YAML configuration files for settings.

## Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env
```

### Required Variables

```bash
# Exchange API Keys
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET=your_binance_secret

# AI/LLM API Keys (choose one or more)
GROK_API_KEY=xai-xxxxxxxxxx          # For Grok AI
OPENAI_API_KEY=sk-xxxxxxxxxx          # For GPT models
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxx   # For Claude models

# Trading Mode
TRADING_MODE=dry_run  # Options: dry_run, paper, live
```

### Optional Variables

```bash
# Database
DATABASE_URL=sqlite:///yunmin.db  # Or PostgreSQL connection string

# Redis (for distributed systems)
REDIS_URL=redis://localhost:6379

# Logging
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR

# Notifications
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook

# Monitoring
PROMETHEUS_PORT=8000
```

## Configuration File

Main configuration is in `config/default.yaml`:

### Basic Trading Configuration

```yaml
trading:
  # Trading pair
  symbol: BTC/USDT
  
  # Timeframe for analysis
  timeframe: 5m
  
  # Maximum positions
  max_positions: 10
  
  # Position size (% of capital)
  position_size: 0.1  # 10%
  
  # Leverage (for futures)
  leverage: 3
```

### Risk Management

```yaml
risk:
  # Stop loss percentage
  stop_loss: 0.02  # 2%
  
  # Take profit percentage
  take_profit: 0.03  # 3%
  
  # Maximum drawdown before stopping
  max_drawdown: 0.10  # 10%
  
  # Daily loss limit
  daily_loss_limit: 0.05  # 5%
  
  # Risk per trade
  risk_per_trade: 0.01  # 1%
```

### Strategy Configuration

```yaml
strategy:
  # Strategy type
  type: ai_agent  # Options: ai_agent, rule_based, ml_model
  
  # AI Agent settings
  ai_agent:
    # Model to use
    model: grok-2-1212  # or gpt-4, claude-3-opus
    
    # Confidence threshold
    min_confidence: 0.65
    
    # Enable memory system
    use_memory: true
    
    # Context window
    lookback_candles: 500
    
    # Multi-agent settings
    agents:
      - market_analyst
      - risk_assessor
      - portfolio_manager
      - execution_agent
```

### Exchange Configuration

```yaml
exchange:
  # Exchange name
  name: binance
  
  # Exchange type
  type: futures  # or spot
  
  # Enable testnet
  testnet: true
  
  # Rate limiting
  rate_limit: true
  
  # Retry settings
  max_retries: 3
  retry_delay: 1  # seconds
```

### Memory System Configuration

```yaml
memory:
  # Enable/disable memory
  enabled: true
  
  # Vector store settings
  vector_store:
    backend: faiss  # or chromadb
    dimension: 1536
    index_path: ./data/vectors/
  
  # Trade history
  history:
    max_trades: 10000
    retention_days: 365
  
  # Retrieval settings
  retrieval:
    k_neighbors: 5
    similarity_threshold: 0.75
```

### Backtesting Configuration

```yaml
backtesting:
  # Date range
  start_date: "2024-01-01"
  end_date: "2024-12-31"
  
  # Initial capital
  initial_capital: 10000
  
  # Commission rate
  commission: 0.001  # 0.1%
  
  # Slippage
  slippage: 0.0005  # 0.05%
```

## Configuration Profiles

You can create multiple configuration profiles:

```bash
config/
├── default.yaml      # Default configuration
├── testnet.yaml      # Testnet settings
├── production.yaml   # Production settings
└── aggressive.yaml   # Aggressive trading parameters
```

Load a specific profile:

```bash
python run_testnet.py --config config/testnet.yaml
```

## Environment-Specific Configuration

YunMin supports environment-specific overrides:

1. **Development** (`.env.development`):
   ```bash
   TRADING_MODE=dry_run
   LOG_LEVEL=DEBUG
   ```

2. **Testnet** (`.env.testnet`):
   ```bash
   TRADING_MODE=paper
   BINANCE_TESTNET=true
   ```

3. **Production** (`.env.production`):
   ```bash
   TRADING_MODE=live
   LOG_LEVEL=WARNING
   ```

## Validation

Validate your configuration:

```bash
python -m yunmin.core.config validate
```

## Security Best Practices

1. **Never commit** `.env` files to version control
2. **Use environment variables** for sensitive data
3. **Rotate API keys** regularly
4. **Use IP whitelisting** on exchange accounts
5. **Enable 2FA** on all accounts
6. **Use read-only API keys** for analysis
7. **Restrict API permissions** to only what's needed

## Configuration Priority

YunMin loads configuration in this order (later overrides earlier):

1. Default values in code
2. `config/default.yaml`
3. Environment-specific config (e.g., `config/testnet.yaml`)
4. Environment variables (`.env`)
5. Command-line arguments

## Next Steps

- [Quickstart Guide](quickstart.md) - Run your first backtest
- [Strategy Configuration](../strategies/ai-strategies.md) - Configure trading strategies

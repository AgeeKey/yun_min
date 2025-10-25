# Yun Min - Quick Start Guide

This guide will get you up and running with the Yun Min trading agent in under 5 minutes.

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/AgeeKey/yun_min.git
cd yun_min
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Configuration

### 1. Copy Example Configuration

```bash
cp .env.example .env
cp config/default.yaml config/my_config.yaml
```

### 2. Edit Configuration (Optional for dry-run)

For dry-run mode, you don't need to configure API keys. The default configuration is safe to use.

If you want to connect to an exchange later:

**Edit `.env` file:**
```bash
# Exchange settings
YUNMIN_EXCHANGE_NAME=binance
YUNMIN_EXCHANGE_API_KEY=your_api_key_here
YUNMIN_EXCHANGE_API_SECRET=your_api_secret_here
YUNMIN_EXCHANGE_TESTNET=true  # Keep true for testing!

# Trading mode
YUNMIN_TRADING_MODE=dry_run  # Start with dry_run!
```

**Important Security Notes:**
- NEVER use API keys with withdrawal permissions
- ALWAYS start with testnet=true
- ALWAYS start with mode=dry_run

## Running the Bot

### Option 1: Run Examples (Recommended for First Time)

#### Risk Management Demo

```bash
python examples/risk_demo.py
```

This demonstrates the risk management system with various scenarios.

#### Basic Bot Example

```bash
python examples/basic_bot.py
```

This runs a simple trading bot in dry-run mode for 3 iterations.

### Option 2: Run via CLI

#### Dry-Run Mode (Safe - No Real Orders)

```bash
yunmin --config config/default.yaml --mode dry_run --iterations 5
```

#### With Custom Interval

```bash
yunmin --config config/default.yaml --interval 30 --iterations 10
```

This runs 10 iterations with 30-second intervals between each.

### Option 3: Run via Python

```python
from yunmin.core.config import load_config
from yunmin.bot import YunMinBot

# Load configuration
config = load_config('config/default.yaml')

# Create and run bot
bot = YunMinBot(config)
bot.run(iterations=5, interval=60)
```

## Understanding Trading Modes

### 1. Dry-Run Mode (Default - SAFE)

```bash
yunmin --mode dry_run
```

- ✅ **Safe**: No connection to exchange, no real orders
- ✅ **Learning**: See how the bot logic works
- ✅ **Testing**: Test configuration changes
- ❌ **Limitation**: Uses simulated data, not real market data

### 2. Paper Trading Mode

```bash
yunmin --mode paper
```

- ✅ **Safe**: No real money, simulated orders only
- ✅ **Real data**: Uses actual market data from exchange
- ✅ **Testing**: Test strategies with real market conditions
- ⚠️ **Requires**: Exchange API keys (read-only is fine)

### 3. Live Trading Mode (⚠️ DANGEROUS)

```bash
yunmin --mode live
```

- ⚠️ **REAL MONEY**: Executes actual trades
- ⚠️ **RISK**: Can lose money
- ⚠️ **REQUIRES**: Extensive testing in dry-run and paper modes first
- ⚠️ **CONFIRMATION**: Bot will ask for explicit confirmation

**NEVER start with live mode. Always test thoroughly first!**

## Running Tests

Verify your installation:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_risk.py -v

# Run with coverage
pytest --cov=yunmin tests/
```

## Docker Deployment

### Build and Run with Docker

```bash
# Build image
docker build -t yunmin .

# Run container
docker run -v $(pwd)/config:/app/config yunmin

# Or use docker-compose
docker-compose up
```

## Common Use Cases

### 1. Test Risk Management

```bash
python examples/risk_demo.py
```

Shows how the risk manager validates orders and manages positions.

### 2. Backtest a Strategy (Coming Soon)

```bash
# Not yet implemented - coming in next version
yunmin backtest --strategy ema_crossover --start 2024-01-01 --end 2024-12-31
```

### 3. Monitor Bot in Real-time

```bash
# Run with verbose logging
yunmin --log-level DEBUG --interval 60
```

Watch logs in real-time:
```bash
tail -f logs/yunmin_*.log
```

## Customizing Configuration

### Modify Risk Parameters

Edit `config/my_config.yaml`:

```yaml
risk:
  max_position_size: 0.05      # 5% max per position (conservative)
  max_leverage: 2.0            # Max 2x leverage
  max_daily_drawdown: 0.03     # 3% daily loss limit
  stop_loss_pct: 0.015         # 1.5% stop loss
  take_profit_pct: 0.025       # 2.5% take profit
```

### Modify Strategy Parameters

```yaml
strategy:
  name: ema_crossover
  fast_ema: 12                 # Fast EMA period
  slow_ema: 26                 # Slow EMA period
  rsi_period: 14
  rsi_overbought: 65.0
  rsi_oversold: 35.0
```

### Change Trading Pair

```yaml
trading:
  symbol: ETH/USDT            # Trade Ethereum instead
  timeframe: 15m              # Use 15-minute candles
```

## Troubleshooting

### Import Errors

```bash
# Reinstall in development mode
pip install -e .
```

### Missing Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt
```

### Exchange Connection Issues

1. Verify API keys are correct
2. Check `testnet: true` in config
3. Verify exchange is supported (use CCXT-compatible exchanges)

### Rate Limiting

The bot includes rate limiting by default. If you see rate limit errors:
- Increase the `interval` between iterations
- Check `enable_rate_limit: true` in config

## Next Steps

1. ✅ **Read the README**: Understand the architecture and features
2. ✅ **Run examples**: Familiarize yourself with the system
3. ✅ **Test in dry-run**: Experiment with configurations
4. 📝 **Configure API keys**: Set up testnet access
5. 📊 **Paper trade**: Test with real market data (no money)
6. 📈 **Backtest strategies**: Validate on historical data (coming soon)
7. 🤖 **Add ML models**: Integrate predictions (advanced)
8. ⚠️ **Live trading**: Only after extensive testing!

## Safety Checklist

Before running in any mode beyond dry-run:

- [ ] I understand how the risk management system works
- [ ] I have tested thoroughly in dry-run mode
- [ ] I am using testnet (not mainnet)
- [ ] My API keys have trading permissions ONLY (no withdrawal)
- [ ] I have set appropriate risk limits (position size, leverage, drawdown)
- [ ] I have enabled the circuit breaker
- [ ] I understand I can lose money
- [ ] I am not investing more than I can afford to lose

## Getting Help

- 📖 **Documentation**: See [README.md](README.md)
- 🐛 **Issues**: [GitHub Issues](https://github.com/AgeeKey/yun_min/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/AgeeKey/yun_min/discussions)
- 📝 **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

## Resources

- [CCXT Documentation](https://docs.ccxt.com/) - Exchange library
- [Binance Testnet](https://testnet.binancefuture.com/) - Test futures trading
- [Technical Analysis](https://www.investopedia.com/terms/t/technicalanalysis.asp) - Learn TA basics

---

**Happy Trading! Remember: Always start safe with dry-run mode! 🚀**

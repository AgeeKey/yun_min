# Quickstart Guide

Get YunMin up and running in 15 minutes!

## Prerequisites

- Python 3.11+
- Docker (optional, recommended for development)
- API keys for your exchange (Binance recommended)
- API keys for AI provider (Groq recommended - free tier available)

## Installation

### Option 1: Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/AgeeKey/yun_min.git
cd yun_min

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Option 2: Docker Development Environment

```bash
# Start all services (bot, database, monitoring)
docker-compose -f docker-compose.dev.yml up
```

## Configuration

### Using the Setup Wizard (Easiest)

```bash
yunmin setup-wizard
```

The wizard will guide you through:
1. Exchange selection (Binance Testnet recommended for first-timers)
2. Trading pair (BTC/USDT, ETH/USDT, etc.)
3. Initial capital
4. Risk tolerance (Conservative/Moderate/Aggressive)
5. Strategy type (AI V3 recommended)
6. AI provider (Groq recommended)
7. Position sizing
8. Alert channels

### Manual Configuration

Copy the example configuration:

```bash
cp config/default.yaml config/my_strategy.yaml
```

Edit `config/my_strategy.yaml`:

```yaml
exchange:
  name: binance
  testnet: true  # IMPORTANT: Start with testnet!

trading:
  mode: dry_run  # Options: dry_run, paper, live
  symbol: BTC/USDT
  initial_capital: 10000.0

risk:
  max_position_size: 0.08  # 8% per position
  stop_loss_pct: 0.025     # 2.5% stop loss

strategy:
  name: ai_v3

llm:
  enabled: true
  provider: groq
```

### Set Environment Variables

Create `.env` file:

```bash
# Exchange API Keys (get from Binance)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# AI Provider (get from Groq - free tier available)
GROQ_API_KEY=your_groq_key

# Optional: Other providers
OPENAI_API_KEY=your_openai_key
GROK_API_KEY=your_grok_key
```

## Running the Bot

### Dry Run Mode (No Real Trading)

Perfect for testing:

```bash
yunmin run --config config/my_strategy.yaml --mode dry_run
```

### Live Dashboard

Monitor your bot in real-time:

```bash
# In a separate terminal
yunmin dashboard
```

### Paper Trading Mode

Simulated trading with real market data:

```bash
yunmin run --config config/my_strategy.yaml --mode paper
```

### Live Trading (⚠️ Real Money!)

```bash
yunmin run --config config/my_strategy.yaml --mode live
```

!!! warning "Live Trading Risk"
    Only use live mode after:
    - Testing extensively in dry_run mode
    - Paper trading successfully for at least a week
    - Understanding all risks involved
    - Starting with small capital you can afford to lose

## Verify Installation

Run the test suite:

```bash
pytest tests/
```

Check system status:

```bash
yunmin --help
```

## Next Steps

1. ✅ Read the [Configuration Guide](configuration.md)
2. ✅ Learn about [AI Trading Strategies](../strategies/ai-strategies.md)
3. ✅ Explore [Architecture Overview](../architecture/overview.md)
4. ✅ Review [Backtesting Guide](../strategies/backtesting.md)

## Getting Help

- 📖 [Full Documentation](https://ageekey.github.io/yun_min/)
- 🐛 [Report Issues](https://github.com/AgeeKey/yun_min/issues)
- 💬 [Discord Community](https://discord.gg/yunmin)

---

**Ready to trade? Let's go! 🚀**

# Yun Min (云敏) - AI Trading Agent

<div align="center">

**Advanced Cryptocurrency Trading Agent with ML/AI Capabilities**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## 🎯 Overview

Yun Min is a modular, AI-powered cryptocurrency trading agent designed for futures trading with a strong emphasis on risk management and safety. The system follows a hybrid approach, combining proven trading strategies with modern ML/AI capabilities.

### Key Features

- 🛡️ **Risk-First Architecture**: Comprehensive risk management system with circuit breakers
- 🔄 **Multiple Trading Modes**: Dry-run, paper trading, and live trading
- 📊 **Technical Analysis**: Built-in EMA crossover strategy with RSI filters
- 🤖 **ML Ready**: Framework for integrating machine learning models
- 🧠 **LLM Integration**: Support for trade explanation and strategy generation
- 📈 **Backtesting**: Test strategies on historical data
- 🔌 **Exchange Support**: Via CCXT library (Binance, Bybit, OKX, etc.)

## 🏗️ Architecture

```
yunmin/
├── data_ingest/     # Exchange connectivity, data fetching
├── features/        # Technical indicators, feature engineering
├── strategy/        # Trading strategies (rule-based + ML)
├── risk/            # Risk management policies and circuit breakers
├── execution/       # Order management (dry-run/paper/live)
├── backtester/      # Historical testing framework
├── ml/              # Machine learning models
├── llm/             # LLM integration for analysis
├── ui/              # Web dashboard and notifications
└── core/            # Configuration and utilities
```

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/AgeeKey/yun_min.git
cd yun_min

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Configuration

```bash
# Copy example configuration
cp .env.example .env
cp config/default.yaml config/my_config.yaml

# Edit configuration files with your settings
# IMPORTANT: Start with testnet and dry_run mode!
```

### Running the Bot

```bash
# Dry-run mode (safe, no real orders)
yunmin --config config/default.yaml --mode dry_run

# Run for specific number of iterations
yunmin --iterations 10 --interval 30

# Paper trading mode (simulated orders)
yunmin --mode paper

# View help
yunmin --help
```

## ⚙️ Configuration

### Environment Variables

Key environment variables (see `.env.example`):

```bash
# Exchange
YUNMIN_EXCHANGE_NAME=binance
YUNMIN_EXCHANGE_TESTNET=true  # ALWAYS start with testnet!

# Trading
YUNMIN_TRADING_MODE=dry_run   # dry_run, paper, or live
YUNMIN_TRADING_SYMBOL=BTC/USDT

# Risk (CRITICAL - adjust carefully)
YUNMIN_RISK_MAX_POSITION_SIZE=0.1      # 10% max position
YUNMIN_RISK_MAX_LEVERAGE=3.0           # Max 3x leverage
YUNMIN_RISK_MAX_DAILY_DRAWDOWN=0.05    # 5% daily loss limit
```

### YAML Configuration

Edit `config/default.yaml` for detailed settings:

```yaml
trading:
  mode: dry_run
  symbol: BTC/USDT
  timeframe: 5m
  initial_capital: 10000.0

risk:
  max_position_size: 0.1
  max_leverage: 3.0
  stop_loss_pct: 0.02
  take_profit_pct: 0.03
  enable_circuit_breaker: true

strategy:
  name: ema_crossover
  fast_ema: 9
  slow_ema: 21
```

## 📚 Usage Examples

### Basic Trading Loop

```python
from yunmin.core.config import load_config
from yunmin.bot import YunMinBot

# Load configuration
config = load_config('config/default.yaml')

# Create bot instance
bot = YunMinBot(config)

# Run for 10 iterations with 60s interval
bot.run(iterations=10, interval=60)
```

### Custom Strategy

```python
from yunmin.strategy.base import BaseStrategy, Signal, SignalType
import pandas as pd

class MyStrategy(BaseStrategy):
    def analyze(self, data: pd.DataFrame) -> Signal:
        # Your strategy logic here
        return Signal(
            type=SignalType.BUY,
            confidence=0.8,
            reason="Custom signal"
        )
```

### Risk Management

```python
from yunmin.risk import RiskManager
from yunmin.risk.policies import OrderRequest

# Create risk manager
risk_manager = RiskManager(config.risk)

# Validate order
order = OrderRequest(
    symbol='BTC/USDT',
    side='buy',
    order_type='market',
    amount=0.1,
    leverage=2.0
)

context = {'capital': 10000, 'current_price': 50000}
approved, messages = risk_manager.validate_order(order, context)
```

## 🔒 Safety & Risk Management

### Five Rules of Yun Min

1. **Never store withdrawal keys** - Use API keys with trade-only permissions
2. **Dry-run is mandatory** - Test thoroughly before live trading
3. **Kill-switch ready** - One command stops everything (Ctrl+C)
4. **Rate limits respected** - Handle exchange 429/5xx responses
5. **Monitor anomalies** - Alert on latency spikes, order failures

### Risk Policies

- **Max Position Size**: Limits exposure per trade
- **Max Leverage**: Prevents excessive leverage
- **Daily Drawdown**: Halts trading if daily loss exceeds limit
- **Stop Loss/Take Profit**: Automatic position management
- **Circuit Breaker**: Emergency halt on anomalous conditions

## 🧪 Testing

### Backtesting

```bash
# Run backtest (coming soon)
python -m yunmin.backtester \
    --strategy ema_crossover \
    --symbol BTC/USDT \
    --start 2024-01-01 \
    --end 2024-12-31
```

### Unit Tests

```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=yunmin tests/
```

## 🤖 ML/AI Integration

### Machine Learning

The framework supports:
- **XGBoost/LightGBM**: For tabular feature predictions
- **Neural Networks**: LSTM/Transformer for time series
- **Reinforcement Learning**: Via Stable-Baselines3

### LLM Features

- Trade explanation generation
- Strategy hypothesis generation
- Market analysis and reporting
- Anomaly detection and alerts

## 📊 Monitoring

### Logs

Logs are stored in `logs/` directory with daily rotation.

### Metrics

Key metrics tracked:
- PnL (Profit and Loss)
- Win rate
- Maximum drawdown
- Sharpe ratio
- Order fill rates
- Latency

## 🛣️ Roadmap

- [x] Core architecture and configuration
- [x] Exchange adapter (CCXT)
- [x] Risk management system
- [x] EMA crossover strategy
- [x] Order execution (dry-run/paper/live)
- [ ] Backtesting engine
- [ ] ML model integration
- [ ] LLM assistant integration
- [ ] Web dashboard UI
- [ ] Telegram notifications
- [ ] Database persistence
- [ ] Multi-strategy support
- [ ] Portfolio management

## ⚠️ Disclaimer

**WARNING: Trading cryptocurrencies involves substantial risk of loss and is not suitable for every investor. This software is for educational purposes only.**

- Past performance does not guarantee future results
- Always test strategies thoroughly in dry-run and paper trading modes
- Never invest more than you can afford to lose
- This software comes with NO WARRANTY
- The developers are not responsible for any financial losses

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📧 Contact

- GitHub: [@AgeeKey](https://github.com/AgeeKey)
- Issues: [GitHub Issues](https://github.com/AgeeKey/yun_min/issues)

---

<div align="center">

**Built with ❤️ for the crypto trading community**

⭐ Star us on GitHub if you find this useful!

</div>
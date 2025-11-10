# Multi-Symbol Trading Implementation Summary

## Overview
This implementation adds support for trading multiple cryptocurrency symbols simultaneously (BTC/USDT, ETH/USDT, BNB/USDT) with intelligent portfolio management and correlation analysis.

## Quick Start

### 1. Using the Multi-Symbol Bot

```python
from run_multi_symbol_bot import MultiSymbolBot

# Initialize with default symbols
bot = MultiSymbolBot(
    symbols=['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
    initial_capital=10000.0
)

# Run the bot
bot.run(iterations=50, interval=60)  # 50 iterations, 60 seconds apart
```

### 2. Using Individual Components

#### Correlation Analysis

```python
from yunmin.analysis.correlation import CorrelationAnalyzer
import pandas as pd

analyzer = CorrelationAnalyzer(window=100)

# Calculate correlations between symbols
data = {
    'BTC/USDT': df_btc,  # DataFrame with 'close' column
    'ETH/USDT': df_eth,
}

correlations = analyzer.calculate_rolling_correlation(data)
# Returns: {'BTC/USDT_ETH/USDT': 0.82}

# Get diversification suggestions
suggestions = analyzer.suggest_diversification(
    positions={'BTC/USDT': 0.4, 'ETH/USDT': 0.3},
    correlations=correlations,
    threshold=0.8
)
```

#### Portfolio Management

```python
from yunmin.agents.portfolio_manager import MultiSymbolPortfolioManager

# Initialize with custom config
config = {
    'symbols': [
        {'symbol': 'BTC/USDT', 'allocation': 0.5, 'risk_limit': 0.15},
        {'symbol': 'ETH/USDT', 'allocation': 0.5, 'risk_limit': 0.15}
    ],
    'portfolio': {
        'total_capital': 20000,
        'max_total_exposure': 0.60,
        'rebalance_threshold': 0.15
    }
}

manager = MultiSymbolPortfolioManager(config)

# Allocate capital based on signals
from yunmin.strategy.base import Signal, SignalType

signals = {
    'BTC/USDT': Signal(type=SignalType.BUY, confidence=0.8, reason='Strong trend'),
    'ETH/USDT': Signal(type=SignalType.BUY, confidence=0.7, reason='Momentum')
}

allocations = manager.allocate_capital(signals)
# Returns: {'BTC/USDT': 0.32, 'ETH/USDT': 0.28}  # Adjusted for confidence
```

## Configuration

Edit `config/default.yaml` to customize multi-symbol settings:

```yaml
trading:
  symbols:
    - symbol: BTC/USDT
      allocation: 0.4      # 40% of capital
      risk_limit: 0.10     # 10% max position size
    - symbol: ETH/USDT
      allocation: 0.35     # 35% of capital
      risk_limit: 0.10
    - symbol: BNB/USDT
      allocation: 0.25     # 25% of capital
      risk_limit: 0.10
  
  portfolio:
    total_capital: 10000
    max_total_exposure: 0.50      # Max 50% in positions
    rebalance_threshold: 0.10     # Rebalance if drift >10%
```

## Key Features

### 1. Correlation-Based Diversification
- Calculates rolling correlation between trading pairs
- Suggests position adjustments when correlation exceeds threshold
- Prevents over-concentration in correlated assets

### 2. Dynamic Capital Allocation
- Allocates capital based on configured percentages
- Adjusts allocation by signal confidence
- Scales positions to respect maximum exposure limits
- Reduces positions when high correlation detected

### 3. Portfolio Rebalancing
- Monitors drift from target allocations
- Suggests rebalancing when drift exceeds threshold
- Maintains balanced exposure across symbols

### 4. Risk Management
- Per-symbol risk limits
- Portfolio-wide exposure limits
- Correlation-adjusted position sizing

## Architecture

```
run_multi_symbol_bot.py
├── MultiSymbolBot (orchestrator)
│   ├── Multiple YunMinBot instances (one per symbol)
│   ├── MultiSymbolPortfolioManager (allocation)
│   └── CorrelationAnalyzer (diversification)
│
yunmin/analysis/
├── correlation.py
│   └── CorrelationAnalyzer
│       ├── calculate_rolling_correlation()
│       ├── calculate_correlation_matrix()
│       ├── suggest_diversification()
│       └── calculate_diversification_score()
│
yunmin/agents/
└── portfolio_manager.py
    └── MultiSymbolPortfolioManager
        ├── allocate_capital()
        ├── check_correlation()
        ├── suggest_rebalancing()
        └── get_portfolio_metrics()
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_multi_symbol.py -v
```

Test coverage:
- ✅ Correlation analysis (7 tests)
- ✅ Portfolio management (8 tests)
- ✅ End-to-end integration (1 test)
- **Total: 16/16 tests passing**

## Example Output

The bot generates:
1. **Real-time logs** showing signals, correlations, and allocations
2. **`multi_symbol_test_results.json`** - Detailed metrics and performance
3. **`MULTI_SYMBOL_REPORT.md`** - Human-readable analysis report

### Sample Results

```json
{
  "symbols": ["BTC/USDT", "ETH/USDT", "BNB/USDT"],
  "initial_capital": 10000,
  "final_capital": 10850,
  "total_pnl": 850,
  "per_symbol_results": {
    "BTC/USDT": {"trades": 8, "win_rate": 0.625, "pnl": 420},
    "ETH/USDT": {"trades": 6, "win_rate": 0.50, "pnl": 280},
    "BNB/USDT": {"trades": 5, "win_rate": 0.60, "pnl": 150}
  },
  "correlations": {
    "BTC_ETH": 0.82,
    "BTC_BNB": 0.65,
    "ETH_BNB": 0.58
  },
  "diversification_score": 0.75
}
```

## Best Practices

1. **Start with paper trading** - Test with `mode: dry_run` first
2. **Monitor correlations** - High correlation (>0.8) limits diversification
3. **Diversify properly** - Use 3-5 symbols with low correlation
4. **Respect limits** - Keep total exposure under 50%
5. **Rebalance regularly** - Check rebalancing suggestions
6. **Test thoroughly** - Run backtest before live trading

## Troubleshooting

### Issue: High correlation between all symbols
**Solution**: Add symbols from different sectors (DeFi, Layer 1, Exchange tokens)

### Issue: Allocations always scaled down
**Solution**: Check `max_total_exposure` setting - might be too conservative

### Issue: No trades executed
**Solution**: Verify signals are BUY type and confidence > 0

## Advanced Usage

### Custom Correlation Window

```python
# Use larger window for more stable correlations
analyzer = CorrelationAnalyzer(window=200)
```

### Custom Allocation Strategy

```python
# Override base allocations dynamically
manager.capital_allocation = {
    'BTC/USDT': 0.6,   # Increase BTC allocation
    'ETH/USDT': 0.4
}
```

### Integration with Existing Bot

```python
from yunmin.bot import YunMinBot
from yunmin.agents.portfolio_manager import MultiSymbolPortfolioManager

# Use with existing bot
bot = YunMinBot(config)
portfolio_manager = MultiSymbolPortfolioManager(config.trading)

# In trading loop
signals = {'BTC/USDT': bot.strategy.analyze(data)}
allocations = portfolio_manager.allocate_capital(signals)
```

## Next Steps

1. **Extended Backtesting**: Run 7+ day backtest for statistical significance
2. **More Symbols**: Add SOL/USDT, MATIC/USDT for better diversification
3. **Dynamic Rebalancing**: Implement automatic rebalancing
4. **Market Regime Detection**: Adjust allocations based on market conditions
5. **Performance Tracking**: Add detailed P&L tracking per symbol

## Support

For issues or questions:
- Check test suite: `tests/test_multi_symbol.py`
- Review sample report: `MULTI_SYMBOL_REPORT.md`
- See example results: `multi_symbol_test_results.json`

"""
Integration Guide: Connecting Yun Min with External Repositories
=================================================================

This document outlines how external repositories are integrated with Yun Min.

REPOSITORY STRUCTURE
====================
/f/AgeeKey/
├── yun_min/           ← Main trading bot project
├── jesse/             ← Strategy framework (study: strategy patterns)
├── project-template/  ← Project structure reference
├── hummingbot/        ← Exchange connectors (study: order tracking, connectors)
├── gateway/           ← REST/WebSocket API gateway
└── freqtrade/         ← Backtesting engine (study: backtest patterns) [GPL - read only]

EXTERNAL PATHS CONFIGURATION
============================
Defined in: config/default.yaml
```yaml
external_paths:
  jesse: ../jesse
  hummingbot: ../hummingbot
  freqtrade: ../freqtrade
  gateway: ../gateway
```

YUN MIN MODULES TO IMPLEMENT
=============================

1. core/backtester.py
   - Pattern source: freqtrade/optimize/backtesting.py
   - Purpose: Run backtest on historical data
   - Key: Loop through candles, track trades, calculate metrics

2. core/exchange_connector.py
   - Pattern source: hummingbot/connector/exchange_base.pyx
   - Purpose: Abstract exchange API interface
   - Key: Implementations for Binance, Kraken, etc.

3. core/order_tracker.py
   - Pattern source: hummingbot/connector/in_flight_order_base.pyx
   - Purpose: Track order state and fills
   - Key: Update fills, commission tracking, state management

4. core/strategy_base.py
   - Pattern source: jesse/strategies/__init__.py
   - Purpose: Base class for all strategies
   - Key: Implement analyze() for signal generation

5. routes/route_manager.py
   - Purpose: Manage trading routes (symbol + timeframe + strategy)
   - Key: Enable/disable routes, track active routes

6. reports/report_generator.py
   - Pattern source: freqtrade/optimize/optimize_reports.py
   - Purpose: Generate trade reports and metrics
   - Key: Win rate, Sharpe ratio, max drawdown

NEXT STEPS
==========

✅ Done:
- [x] Organized folder structure
- [x] Added external_paths to config
- [x] Created base module files with docstrings

TODO:
- [ ] Study jesse/routes/ for route patterns
- [ ] Implement BinanceConnector inheriting ExchangeConnector
- [ ] Implement OrderTracker integration with exchange connector
- [ ] Implement Backtester with actual backtest loop
- [ ] Create test strategies (EMA crossover, RSI)
- [ ] Add configuration loading from config/default.yaml
- [ ] Test dry-run mode before any live trading

IMPORTANT NOTES
===============

1. DO NOT copy code directly from Freqtrade (GPL license)
   - Only use it as inspiration for algorithm patterns
   - Implement your own logic

2. Always test in testnet and dry_run mode first
   - config.yaml: trading.mode: dry_run
   - exchange.testnet: true

3. Keep external repos as READ-ONLY references
   - Don't modify them in AgeeKey
   - Link to them via external_paths config

4. Risk management is critical
   - risk.max_daily_drawdown: 0.05 (5%)
   - risk.stop_loss_pct: 0.02 (2%)
   - risk.take_profit_pct: 0.03 (3%)
"""

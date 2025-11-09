"""
Yun Min Architecture & Module Guide
====================================

OVERVIEW
--------
Yun Min is a modular trading bot with:
  - Dry-run, paper, and live trading modes
  - Multi-exchange, multi-symbol, multi-timeframe support
  - Strategy framework inspired by Jesse (MIT)
  - Order tracking inspired by Hummingbot (Apache-2.0)
  - Backtesting inspired by Freqtrade (GPL - patterns only)

ROOT STRUCTURE
--------------
yunmin/
├── core/              # Core trading logic
│   ├── data_contracts.py     # Data type definitions
│   ├── strategy_base.py      # Base class for all strategies
│   ├── exchange_connector.py # Exchange API interface
│   ├── order_tracker.py      # Order lifecycle tracking
│   ├── backtester.py         # Historical simulation
│   └── config.py             # Configuration loading
│
├── routes/            # Route management
│   └── route_manager.py      # Multi-route synchronization
│
├── strategy/          # User strategies
│   ├── builtin/       # Built-in test strategies
│   │   ├── ema_crossover.py
│   │   └── rsi_filter.py
│   └── user/          # Custom strategies
│
├── execution/         # Order execution
│   ├── executor.py         # Main execution engine
│   └── risk_manager.py     # Risk checks
│
├── data_ingest/       # Data handling
│   ├── candle_fetcher.py   # Fetch candles from exchange
│   └── data_cache.py       # Local data cache
│
├── reports/           # Reporting
│   └── report_generator.py  # Generate trade reports
│
├── infra/             # Infrastructure
│   ├── logger.py            # Logging setup
│   ├── db.py                # Database (sqlite/postgres)
│   └── clock.py             # Time management
│
└── bot.py             # Main bot class


KEY MODULES
-----------

1. core/strategy_base.py (YOUR IMPLEMENTATION)
   Base class: StrategyBase
   
   Methods to implement:
     - should_long() -> bool
     - should_short() -> bool
     - should_exit() -> bool
     - go_long()
     - go_short()
     - go_exit()
   
   Helper methods:
     - sma(candles, period) -> List[float]
     - ema(candles, period) -> List[float]
     - rsi(candles, period) -> List[float]
     - crossover(fast, slow) -> bool
     - crossunder(fast, slow) -> bool
   
   Data in: Multi-TF candles dictionary
   Data out: None (side effects through go_* methods)

2. core/order_tracker.py (TO IMPLEMENT)
   Main class: OrderTracker
   
   Tracks:
     - In-flight orders (client_oid ↔ exchange_oid mapping)
     - Partial fills
     - Commissions
     - Order state machine
   
   Data in: Order updates from exchange
   Data out: Order state, InFlightOrder objects

3. core/exchange_connector.py (TO IMPLEMENT)
   Base class: ExchangeConnector
   Implementations: BinanceConnector, KrakenConnector, etc.
   
   Methods:
     - get_balance() -> Dict[symbol, amount]
     - place_order(symbol, side, type, qty, price) -> Order
     - cancel_order(order_id) -> bool
     - get_order_status(order_id) -> Order
     - get_open_orders() -> List[Order]
   
   Data in: Trading commands
   Data out: Order confirmations, fills

4. routes/route_manager.py (YOUR IMPLEMENTATION ✓)
   Main class: RouteManager
   
   Manages:
     - Multiple (exchange, symbol, tf, strategy) routes
     - Per-route state (position, pending orders)
     - Global time synchronization (no look-ahead)
     - Per-route config overrides
   
   Data in: Route definitions
   Data out: Route state, formatted routes for UI

5. core/backtester.py (TO IMPLEMENT)
   Main class: Backtester
   
   Simulates:
     - Historical candle data
     - Order fills with slippage
     - Fees and commissions
     - Funding costs (futures)
     - PnL calculation
   
   Data in: Candles, strategy
   Data out: Trade history, metrics (BacktestResult)

6. reports/report_generator.py (TO IMPLEMENT FULLY)
   Main class: ReportGenerator
   
   Computes:
     - Win rate, avg trade size
     - Max drawdown, Sharpe ratio
     - CAGR, profit factor
     - Fee impact analysis
   
   Data in: Trade list
   Data out: PerformanceMetrics, formatted report (text/html/json)


DATA FLOW
---------

Live Trading:
  1. bot.py loads config → sets routes
  2. data_ingest fetches latest candles
  3. route_manager.set_global_time(now)
  4. For each route:
       a. Get candles for this symbol/tf
       b. Call strategy.should_long/short/exit()
       c. If true, call strategy.go_long/short/exit()
       d. execution.execute_decision() places order
       e. exchange_connector sends to exchange
       f. order_tracker monitors fills
       g. Update position, P&L
  5. report_generator computes metrics
  6. Data stored in DB or cache

Backtesting:
  1. Load historical candles
  2. For each candle (time-ordered):
       a. backtester simulates candle processing
       b. Call strategy methods (same as live)
       c. backtester simulates fill (with slippage)
       d. Update position, track P&L
       e. Close trades if exit signal
  3. Aggregate results
  4. report_generator analyzes performance


CONFIG STRUCTURE (config/default.yaml)
-------------------------------------
exchange:
  name: binance
  testnet: true

trading:
  mode: dry_run  # dry_run, paper, live
  routes:
    - exchange: binance
      symbol: BTC/USDT
      timeframe: 5m
      strategy: ema_crossover

risk:
  max_daily_drawdown: 0.05
  stop_loss_pct: 0.02
  take_profit_pct: 0.03
  max_leverage: 5

external_paths:
  jesse: ../jesse
  hummingbot: ../hummingbot
  freqtrade: ../freqtrade


NEXT IMPLEMENTATION STEPS
-------------------------

Priority 1 (Required for trading):
  ✓ strategy_base.py (should_long/short/exit, go_long/short/exit)
  ✓ route_manager.py (multi-route sync)
  ✓ ema_crossover.py (test strategy)
  ✓ rsi_filter.py (test strategy)
  - exchange_connector.py (BinanceConnector REST + WS)
  - order_tracker.py (in-flight order tracking)
  - execution/executor.py (place orders, manage positions)
  - risk_manager.py (check limits before orders)

Priority 2 (Backtesting):
  - backtester.py (simulate candles, fills, fees)
  - reports/report_generator.py (full metrics: Sharpe, Sortino, CAGR)
  - tests/test_backtest_*.py (verify backtester accuracy)

Priority 3 (Production):
  - infra/db.py (persist trades)
  - infra/clock.py (time sync)
  - core/config.py (load from YAML with per-route overrides)
  - Risk engine (circuit breaker, daily DD lock)
  - Live mode safeguards (kill-switch, audit log)

Priority 4 (UI/API):
  - API endpoint for route status
  - Metrics endpoint
  - Dashboard (basic HTML/React)


TESTING CHECKLIST (BEFORE LIVE)
-------------------------------
Dry-run (simulated fills, no real orders):
  ✓ Strategy logic correct (test with known data)
  ✓ Order tracking works (fills, cancels, retries)
  ✓ Risk limits enforced (no overleveraging)
  ✓ Multi-route sync (no time conflicts)
  ✓ Backtest metrics stable (repeatable with seed)
  - 7+ days without critical errors

Paper mode (real market data, simulated fills):
  - Risk limits enforced in paper
  - Slippage realistic
  - Commissions accurate
  - Daily report generation
  - 7+ days stable

Live mode (real trading):
  - Verify with minimal capital
  - Test with 1-2 small routes first
  - Monitor for 7+ days
  - Only scale after proven stability
"""

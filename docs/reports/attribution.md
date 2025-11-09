"""
Adapted From & Source Attribution
==================================

This document tracks which external repositories inspired each module
and the commit/version used as reference.

LICENSE COMPLIANCE
------------------

1. Jesse (MIT License)
   ✅ Can adapt code with attribution
   Used for: Strategy framework patterns

2. Hummingbot (Apache License 2.0)
   ✅ Can adapt code with attribution
   Used for: Exchange connector, order tracking

3. Freqtrade (GPL-3.0)
   ⚠️ GPL-3.0: MUST NOT COPY CODE DIRECTLY
   ✓ Can use as reference for CONCEPTS ONLY
   Used for: Backtesting loop concept, metrics calculation

PINNED VERSIONS
---------------

Repository: jesse
  URL: https://github.com/jesse-ai/jesse
  Version: Latest from workspace
  Last checked: 2025-10-26
  
  Files used as reference:
    - jesse/routes/__init__.py (Route class pattern)
    - jesse/models/Route.py (Route data model)
    - jesse/services/strategy_handler/ExampleStrategy/__init__.py (Strategy pattern)
  
  Adapted into:
    - yunmin/core/strategy_base.py (StrategyBase class)
      Methods: should_long/short/exit, go_long/short/exit
      Concept: Multi-timeframe candle access, decision-making
    
    - yunmin/routes/route_manager.py (RouteManager class)
      Concept: Route registry, enable/disable, formatted output
    
    - yunmin/strategy/builtin/ema_crossover.py (EMACrossover strategy)
    - yunmin/strategy/builtin/rsi_filter.py (RSIFilter strategy)


Repository: hummingbot
  URL: https://github.com/hummingbot/hummingbot
  Version: Latest from workspace
  Last checked: 2025-10-26
  
  Files used as reference:
    - hummingbot/connector/in_flight_order_base.pyx (Order tracking)
    - hummingbot/connector/client_order_tracker.py (Order state machine)
    - hummingbot/connector/exchange_base.pyx (Exchange API)
    - hummingbot/core/data_type/in_flight_order.py
  
  Adapted into:
    - yunmin/core/exchange_connector.py (ExchangeConnector base)
      Methods: place_order, cancel_order, get_balance, etc.
      Concept: Abstraction layer over exchange APIs
    
    - yunmin/core/order_tracker.py (OrderTracker class)
      Concept: client_oid ↔ exchange_oid mapping, partial fills
      Data: InFlightOrder, order state transitions


Repository: freqtrade
  URL: https://github.com/freqtrade/freqtrade
  Version: Latest from workspace (GPL-3.0)
  Last checked: 2025-10-26
  
  ⚠️ REFERENCE ONLY - NO CODE COPIED
  
  Files studied for CONCEPTS:
    - freqtrade/optimize/backtesting.py (Backtest loop structure)
    - freqtrade/optimize/optimize_reports.py (Metrics calculation)
    - freqtrade/data/btanalysis.py (Trade analysis functions)
  
  Conceptual patterns used in:
    - yunmin/core/backtester.py (Backtester class)
      Concept: Iterate candles → check signals → simulate fills → calc PnL
    
    - yunmin/reports/report_generator.py (ReportGenerator class)
      Concept: Collect metrics → compute Sharpe, drawdown, CAGR
  
  Note: All code in yun_min/core/backtester.py is original implementation
        inspired by Freqtrade's architecture, NOT copied code.


CUSTOM DATA CONTRACTS
---------------------

Designed independently for Yun Min (no direct adaptation):
  - yunmin/core/data_contracts.py
    Candle, Order, Fill, Trade, Decision, Position, BacktestResult
    
  These follow trading domain conventions but are original definitions.


ATTRIBUTION REQUIREMENTS (LICENSE COMPLIANCE)
---------------------------------------------

For Jesse (MIT):
  ✅ Include MIT license in: yunmin/strategy/builtin/
  ✅ Docstring mentions Jesse inspiration

For Hummingbot (Apache-2.0):
  ✅ Include Apache license in: yunmin/core/exchange_connector.py, yunmin/core/order_tracker.py
  ✅ Docstring mentions Hummingbot

For Freqtrade (GPL-3.0):
  ✓ NO LICENSE NEEDED (patterns only, no code copied)
  ✓ Docstring mentions "inspired by"


FILE HEADERS (LICENSE ATTRIBUTION)
----------------------------------

Example for Jesse-adapted code:
  # Adapted from Jesse framework (MIT License)
  # https://github.com/jesse-ai/jesse
  # Original concept: should_long/short/exit, go_long/short/exit pattern

Example for Hummingbot-adapted code:
  # Adapted from Hummingbot (Apache License 2.0)
  # https://github.com/hummingbot/hummingbot
  # Original concept: in_flight_order tracking, client_oid ↔ exchange_id mapping

Example for Freqtrade-inspired code:
  # Inspired by Freqtrade (GPL-3.0, patterns only)
  # https://github.com/freqtrade/freqtrade
  # Concept: backtest loop structure, metrics calculation
  # Note: All code is original implementation


WHAT CAN BE SHARED
------------------

✅ These files can be open-sourced (with attribution):
  - yunmin/core/strategy_base.py (Jesse patterns)
  - yunmin/routes/route_manager.py (Jesse patterns)
  - yunmin/strategy/builtin/* (Jesse-derived)
  - yunmin/core/exchange_connector.py (Hummingbot patterns)
  - yunmin/core/order_tracker.py (Hummingbot patterns)
  - yunmin/core/backtester.py (Freqtrade concepts)
  - yunmin/reports/report_generator.py (Freqtrade concepts)

⚠️ DO NOT SHARE (private/confidential):
  - yunmin/execution/executor.py (specific logic)
  - yunmin/risk/ (trading logic)
  - config/default.yaml (API keys, settings)
  - data/ (historical data, trades)

🚫 ALWAYS FORBIDDEN:
  - Direct GPL code (Freqtrade)
  - Modified versions of Jesse/Hummingbot without license header


AUDIT CHECKLIST
---------------

Before publishing Yun Min code:
  ☑ Review each module for GPL violations
  ☑ Ensure MIT headers on Jesse-adapted code
  ☑ Ensure Apache headers on Hummingbot-adapted code
  ☑ Verify no direct Freqtrade copy-paste
  ☑ Run plagiarism check if needed
  ☑ Include ATTRIBUTION.md in root


FUTURE VERSIONS
---------------

If adding dependencies:
  - Always document which repo inspired which module
  - Update this file immediately
  - Check license compatibility before integration
  - Prefer MIT/Apache over GPL for new features
"""

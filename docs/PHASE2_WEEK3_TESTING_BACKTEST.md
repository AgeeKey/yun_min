# Phase 2 Week 3: Testing & Backtesting Guide

## Overview

Week 3 implementation includes:
- **E2E Integration Tests** (10+ test cases, all execution modes)
- **Historical Backtester** (OHLCV simulation, market/limit execution)
- **Report Generator** (JSON/CSV/HTML metrics, Sharpe/Sortino/Calmar)
- **Dry-run Engine** (7-day telemetry, CRIT/WARN alerts, decision logging)

**Target:** Go/No-Go for Phase 3 (live trading approval)

---

## 1. Integration Tests (E2E)

### Location
`tests/integration/test_e2e_pipeline.py`

### Running Tests

```bash
# All E2E tests
pytest tests/integration/test_e2e_pipeline.py -v -m e2e

# Specific test
pytest tests/integration/test_e2e_pipeline.py::test_decision_to_order_pipeline -v

# With coverage
pytest tests/integration/test_e2e_pipeline.py -v --cov=yunmin.core --cov-report=html

# Slow tests only
pytest tests/integration/test_e2e_pipeline.py -v -m slow
```

### Test Matrix

| Mode | Scenario | Test | Status |
|------|----------|------|--------|
| DRY_RUN | Create order | `test_dry_run_mode` | ✓ |
| PAPER | Simulated fill | `test_paper_mode` | ✓ |
| LIVE | Real (mocked) | `test_live_mode_simulation` | ✓ |
| Pipeline | Full flow | `test_decision_to_order_pipeline` | ✓ |
| Partial | Multi-fill avg price | `test_partial_fill_average_price` | ✓ |
| Cancel | Reissue | `test_reissue_after_cancel` | ✓ |
| Risk | Position limit | `test_position_size_limit` | ✓ |
| Risk | DD lock | `test_daily_dd_lock` | ✓ |
| WS | Order update | `test_ws_order_update_event` | ✓ |
| WS | Kline update | `test_ws_kline_update_event` | ✓ |
| Error | Invalid intent | `test_invalid_decision_intent` | ✓ |
| Concurrent | Multi-symbol | `test_concurrent_decisions` | ✓ |

### Critical Tests (Must Pass)

1. **`test_decision_to_order_pipeline`**
   - Decision → Executor → RiskManager → Connector → Tracker → Engine
   - Verifies: Order state, position tracking, daily stats
   
2. **`test_partial_fill_average_price`**
   - Multiple fills at different prices
   - Verifies: Correct average price, commission accumulation
   
3. **`test_cancel_and_reissue`**
   - Cancel order, reissue new one
   - Verifies: State transitions, no duplicates
   
4. **`test_daily_dd_lock`**
   - Exceed daily DD → order rejected
   - Verifies: RiskManager enforces limits
   
5. **`test_ws_order_update_event`**
   - WebSocket fill event processing
   - Verifies: Position/stats updated correctly

### Success Criteria

- ✅ 0 critical failures
- ✅ Flakiness < 2% (max 1 retry per 50 runs)
- ✅ All negative cases caught by RiskManager/Executor
- ✅ All modes (DRY_RUN, PAPER, LIVE) functional
- ✅ Execution time < 30s total

---

## 2. Backtester (Historical Simulation)

### Location
`yunmin/backtesting/backtester.py`

### Basic Usage

```python
from yunmin.backtesting.backtester import (
    Backtester, BacktestConfig, OrderType, Candle
)

# Config
config = BacktestConfig(
    symbols=["BTCUSDT", "ETHUSDT"],
    start_date="2025-01-01",
    end_date="2025-01-31",
    initial_capital=10000.0,
    timeframe="1m",
    slippage_bps=2.0,
    commission_bps=1.0,
    max_leverage=1.0,
    max_position_pct=0.05
)

# Strategy function
async def my_strategy(prices, positions):
    """
    Returns: Dict[symbol -> Decision]
    """
    decisions = {}
    for symbol, price in prices.items():
        if price > 42000:
            decisions[symbol] = Decision(
                intent="long",
                confidence=0.8,
                size_hint=0.05,
                reason="Price high"
            )
    return decisions

# Load candles (implement your loader)
def load_candles():
    # Return: Dict[symbol -> List[Candle]]
    return {
        "BTCUSDT": [Candle(...), ...],
        "ETHUSDT": [Candle(...), ...]
    }

# Run backtest
backtester = Backtester(config)
result = backtester.run(
    strategy_func=my_strategy,
    candles_loader=load_candles,
    progress_callback=lambda i, max: print(f"{i}/{max}")
)

print(result)
# BacktestResult(
#   capital=10500.00, 
#   pnl=500.00%,
#   dd=8.5%,
#   sharpe=1.45
# )
```

### Backtester Architecture

```
Backtester
  ├─ BacktestConfig (parameters)
  ├─ OrderSimulator (market/limit execution)
  └─ BacktestRunner (simulation engine)
      ├─ execute_decision()
      ├─ update_mark_prices()
      └─ calculate_metrics()
```

### Execution Model

1. **Market Order**
   - Slippage: fixed bps + volatility-based (vol % × 100)
   - Fill within candle [low, high]
   - Fills immediately at current price ± slippage

2. **Limit Order**
   - FIFO matching
   - Fills if limit price within [low, high]
   - No fill if out of range

3. **Position Tracking**
   - Qty, avg entry price
   - Unrealized P&L calculated at close price
   - Realized P&L when position closed

4. **Commissions**
   - Fixed bps per fill: `qty × price × commission_bps / 10000`
   - Subtracted from proceeds

### Key Metrics

| Metric | Definition |
|--------|-----------|
| **Sharpe** | (ret - rf) / σ × √periods (annualized) |
| **Sortino** | (ret - rf) / σ_down × √periods (downside only) |
| **Calmar** | ret / max_dd (% return / % DD) |
| **Win Rate** | (winning trades / total trades) × 100 |
| **Profit Factor** | sum(wins) / abs(sum(losses)) |
| **Max DD** | max drawdown from peak |

### Validation Checklist

- ✅ Single seed reproducible (same output)
- ✅ PAPER vs backtest PnL match ±10-15%
- ✅ Commission calculation correct
- ✅ Position tracking accurate
- ✅ No look-ahead bias (only current/past data)
- ✅ Slippage model realistic

---

## 3. Report Generator

### Location
`yunmin/reporting/report_generator.py`

### Usage

```python
from yunmin.reporting.report_generator import ReportGenerator

generator = ReportGenerator(output_dir="./reports")

# Generate from backtest
report = generator.generate_from_backtest(backtest_result)
# Returns:
# {
#   "json": "reports/metrics_20250126_153045.json",
#   "csv": "reports/trades_20250126_153045.csv",
#   "html": "reports/report_20250126_153045.html",
#   "metrics": {...}
# }

# Export daily summary
generator.generate_daily_summary(daily_stats, timestamp)

# Export risk violations
generator.generate_risk_report(violations, timestamp)
```

### Report Formats

**1. JSON (metrics)**
```json
{
  "timestamp": "20250126_153045",
  "generated_at": "2025-01-26T15:30:45",
  "metrics": {
    "initial_capital": 10000,
    "final_capital": 10500,
    "pnl": 500,
    "pnl_pct": 5.0,
    "max_drawdown_pct": 8.5,
    "sharpe_ratio": 1.45,
    "total_trades": 12,
    "win_rate": 66.7,
    ...
  }
}
```

**2. CSV (trade-by-trade)**
```
symbol,entry_time,entry_price,exit_time,exit_price,qty,side,pnl,pnl_pct,commission
BTCUSDT,2025-01-01T09:30:00,42000.00,2025-01-01T10:15:00,42500.00,0.1,BUY,50.00,0.12%,21.00
```

**3. HTML (summary report)**
- Capital summary (initial, final, P&L)
- Risk metrics (DD, Sharpe, Sortino, Calmar)
- Trade statistics (total, win rate, avg win/loss)
- Visual metric cards

---

## 4. Dry-run Engine (7-Day Monitoring)

### Location
`yunmin/core/dry_run_engine.py`

### Setup

```python
from yunmin.core.dry_run_engine import DryRunEngine, DryRunConfig, AlertLevel

config = DryRunConfig(
    symbols=["BTCUSDT", "ETHUSDT"],
    initial_capital=10000,
    
    # Risk thresholds
    max_daily_dd=0.15,           # 15%
    max_daily_dd_hard=0.20,      # Hard kill-switch at 20%
    max_position_pct=0.05,
    
    # Alerts
    ws_stale_threshold_ms=60000,
    rest_error_threshold=3,
    reconnect_rate_threshold=6,  # Max 6/hour
    latency_warn_ms=2000,
    
    # Telemetry
    telemetry_interval_s=10,
    export_dir="./dry_run_data"
)

engine = DryRunEngine(config)

# Alert handler
def handle_alert(alert):
    print(f"[{alert.level.value.upper()}] {alert.message}")
    if alert.level == AlertLevel.CRIT:
        send_slack(f"🚨 {alert.message}")

engine.on_alert(handle_alert)
```

### Telemetry Collection

Update metrics every N seconds:

```python
# In trading loop
engine.update_metrics(
    balance=account_balance,
    pnl_total=total_pnl,
    daily_pnl=today_pnl,
    max_dd_daily=max_daily_dd,
    current_dd=current_dd,
    open_orders=len(open_orders),
    fill_count=daily_fills,
    exposure_pct=position_value / balance,
    commission_total=total_commission
)

# Log WebSocket events
engine.log_ws_event("update", latency_ms=145)
engine.log_ws_event("reconnect")

# Log REST events
engine.log_rest_event("/api/v3/order", latency_ms=250, success=True)

# Log decisions
engine.log_decision(
    symbol="BTCUSDT",
    decision_id="d_12345",
    decision_type="long",
    confidence=0.85,
    features={...},
    strategy_id="ema_cross_v1",
    accepted=True
)
```

### Metrics Dashboard

| Metric | Threshold (WARN/CRIT) | Description |
|--------|---------------------|-------------|
| **PnL%** | - | Total return vs initial |
| **Daily DD%** | 15% / 20% | Drawdown vs peak |
| **Orders/min** | - | Trading frequency |
| **Fills Rate%** | < 90% (WARN) | Market order fill rate |
| **WS Latency** | > 2s (WARN) | Update latency |
| **WS Stale** | > 60s (CRIT) | No updates for 60s |
| **REST Errors** | 3+/min (CRIT) | Error threshold |
| **WS Reconnects** | > 6/hour (WARN) | Connection stability |
| **Fee Impact** | - | Commissions as bps of capital |

### Alert Rules

**CRITICAL Alerts**
- DD > max_dd_hard (20%) → Kill-switch
- WS stale > 60s → Kill-switch
- REST errors ≥ 3 in 1 min → Kill-switch
- Any unhandled exception in decision/execution

**WARNING Alerts**
- DD > max_dd (15%)
- WS latency > 2s
- REST latency > 2s
- WS reconnects > 6/hour
- Order rejected by RiskManager
- Position size capped

### Export & Analysis

```python
# Export after 7 days
engine.export_metrics("./dry_run_data/metrics_final.json")

# Get status
status = engine.get_status_summary()
print(f"""
Running: {status['is_running']}
Kill-switch: {status['kill_switch_active']}
Alerts: {status['alerts_count']}
Telemetry:
  PnL: {status['telemetry']['pnl_total']:.2f}
  DD: {status['telemetry']['max_dd_daily']*100:.1f}%
  Fills: {status['telemetry']['fills_rate']:.1f}%
  WS Reconnects: {status['telemetry']['ws_reconnects']}
  REST Errors: {status['telemetry']['rest_errors']}
""")
```

### 7-Day Go/No-Go Criteria

**GO ✅**
- No CRITICAL alerts (except info-level events)
- Max DD < max_dd (15%)
- Fill rate > 90% for market orders
- WS reconnects < 20 total
- REST errors < 5 total
- All metrics stable and repeatable
- RiskManager correctly blocked violations
- Kill-switch tested and functional

**NO-GO ❌**
- 1+ CRITICAL alert unresolved
- DD > max_dd_hard (20%)
- WS loses events (OrderTracker out of sync)
- Flapping alerts (> 3 in short timeframe)
- Stuck orders (not filled or cancelled)
- Decision logging gaps
- Commission/PnL drift from expected

---

## Validation Checklist (Pre-Phase 3)

### E2E Tests
- [ ] All 12+ tests pass (no flakiness)
- [ ] DRY_RUN mode: order created, not filled
- [ ] PAPER mode: immediate fill, position tracked
- [ ] LIVE mode: REST called, order in tracker
- [ ] Partial fills: avg price correct
- [ ] Cancel & reissue: states correct
- [ ] Position size limit enforced
- [ ] Daily DD lock blocks orders
- [ ] WebSocket events processed
- [ ] Concurrent orders handled

### Backtester
- [ ] Same seed → same metrics
- [ ] PAPER vs backtest ±10-15%
- [ ] Commission deducted correctly
- [ ] No look-ahead (only current/past)
- [ ] Slippage model applied
- [ ] Position tracking accurate
- [ ] Metrics calculated correctly
- [ ] Edge cases (0 trades, DD, etc.)

### Report Generator
- [ ] JSON export readable
- [ ] CSV trade list complete
- [ ] HTML renders correctly
- [ ] Metrics match backtest results
- [ ] Charts/summaries clear

### Dry-run Engine
- [ ] Metrics updated every N seconds
- [ ] Alerts triggered on thresholds
- [ ] Kill-switch tested
- [ ] Decision logging working
- [ ] 7-day run stability
- [ ] Export complete and consistent
- [ ] Dashboard readable
- [ ] Notification delivery (Slack/Email)

---

## Troubleshooting

### E2E Tests Failing

**Issue:** `test_decision_to_order_pipeline` fails
```
AssertionError: status != FILLED
```
**Solution:**
- Check Executor.execute_decision() return status
- Verify RiskManager not rejecting (mock max_position_pct too low)
- Check OrderTracker.add_fill() called

**Issue:** Partial fill test incorrect average
```
AssertionError: abs(avg - expected) > 1.0
```
**Solution:**
- Verify OrderTracker.avg_fill_price calculation
- Check fill qty and price passed correctly
- Debug with print(order.fills) to see all fills

### Backtester Issues

**Issue:** `BacktestResult` shows 0 trades
```
total_trades: 0
```
**Solution:**
- Check strategy function returns decisions
- Verify OrderSimulator.execute_market_order() fills qty > 0
- Debug: print(runner.positions) after each iteration

**Issue:** Sharpe ratio = 0 or inf
```
sharpe_ratio: 0 (or inf/-inf)
```
**Solution:**
- Ensure >1 return sample
- Check std_dev > 0 (not flat curve)
- If all winning/losing, use best available ratio

### Dry-run Stuck

**Issue:** Kill-switch triggered but trading continues
**Solution:**
- Verify `is_running = False` stops decision loop
- Check TradingEngine respects kill-switch flag
- Ensure Executor checks `mode != ExecutionMode.LIVE`

**Issue:** Metrics not updating
**Solution:**
- Verify update_metrics() called every N seconds
- Check telemetry_history list growing
- Ensure datetime imports correct

---

## Next Steps (Phase 3)

1. Run full 7-day dry-run on testnet
2. Validate Go/No-Go criteria met
3. Deploy to live trading (with kill-switch active)
4. Monitor first 24 hours continuously
5. Scale capital based on actual performance

---

**Last Updated:** 2025-01-26
**Status:** Week 3 Implementation Complete

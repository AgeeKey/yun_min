# Live Launch Plan (Phase 3)

**Objective:** Safe, controlled transition to mainnet trading with automated safeguards.

**Timeline:** 48 hours (Day 1-2)
**Capital at Risk:** $100-$300 (micro-budget for validation)
**Scale-up:** After 48h success → gradually increase

---

## 1. Pre-Launch (T-24h)

### Infrastructure Validation
- [ ] Binance API keys created (no withdrawal permissions)
- [ ] Network connectivity to api.binance.com verified
- [ ] WebSocket connectivity confirmed
- [ ] Firewall/security rules allow trading
- [ ] Monitoring dashboard accessible

### Code Deployment
- [ ] Merge GO/NO-GO approval commit to main
- [ ] Tag release: `v3.0.0-live-phase3`
- [ ] Docker image built (if containerized)
- [ ] Config locked: `config.prod.yaml`
- [ ] All secrets in `.env` (NOT in git)

### Team Mobilization
- [ ] On-call schedule confirmed (24×2h coverage)
- [ ] Alert recipients verified (Slack, Email, SMS)
- [ ] Runbook briefing completed
- [ ] Kill-switch procedure walkthrough done
- [ ] Escalation contacts confirmed

**Pre-Launch Checklist Sign-off:**
- [ ] Infrastructure: ___________________
- [ ] Code: ___________________
- [ ] Team: ___________________

---

## 2. Configuration (Locked)

### Execution Parameters

```yaml
execution:
  mode: LIVE              # NO PAPER/DRY_RUN
  exchange: binance
  testnet: false          # MAINNET
  
executor:
  max_retries: 3
  timeout_ms: 5000
  
risk_manager:
  initial_capital: 300.0  # $300 (micro)
  max_position_pct: 0.02  # 2% per position (not 5%)
  max_daily_dd: 0.02      # 2% daily stop (not 15%)
  max_daily_dd_hard: 0.05 # 5% hard kill-switch (not 20%)
  max_daily_trades: 20    # Conservative
  max_open_orders: 3
  leverage: 1.0           # NO MARGIN
  
trading_engine:
  symbols:
    - BTCUSDT             # Stable, high liquidity
    - ETHUSDT             # (optional, add later)
  decision_interval_s: 5
  
dry_run_engine:
  telemetry_interval_s: 10
  ws_stale_threshold_ms: 60000
  rest_error_threshold: 2  # STRICT (not 3)
  reconnect_rate_threshold: 4  # STRICT (not 6)
  latency_warn_ms: 1500   # STRICT (not 2000)
```

### Order Constraints

```
Order Type:      MARKET (only, for fill certainty)
Position Size:   Max $6 per symbol ($2 × 1% → $0.02 position cap)
Slippage Model:  Fixed 2bps + vol-based
Commission:      0.1% (Binance standard)
No OCO Orders:   Disabled
No Post-only:    Disabled
```

### Approval Gate

```
Config hash: __________________
Frozen at:   2025-01-27 08:00 UTC
Signed by:   __________________
```

---

## 3. Launch Sequence (Day 1, 06:00 UTC)

### T-60 minutes

```bash
# Final pre-flight checks
$ python -c "
from yunmin.connectors.binance_connector import BinanceConnector
from yunmin.core.executor import ExecutionMode

conn = BinanceConnector(testnet=False)
account = conn.get_account()
print(f'Balance: ${account[\"totalWalletBalance\"]}')
print('✅ API connected')
"

# Verify no leftover orders
$ curl -X GET https://api.binance.com/api/v3/openOrders \
  -H "X-MBX-APIKEY: <KEY>"
# Should return []
```

### T-30 minutes

```bash
# Start monitoring dashboard
$ tail -f ./logs/trading.log | grep -E "CRIT|WARN|ORDER"

# Start metrics exporter
$ python -c "
from yunmin.core.dry_run_engine import DryRunEngine, DryRunConfig
config = DryRunConfig(symbols=['BTCUSDT', 'ETHUSDT'], initial_capital=300)
engine = DryRunEngine(config)
# Metrics will be exported to ./dry_run_data/
"
```

### T-5 minutes

```python
# Final system check
from yunmin.core.executor import Executor, ExecutionMode

print("Executor mode:", executor.mode)
assert executor.mode == ExecutionMode.LIVE, "Mode not set to LIVE!"

print("Capital:", risk_manager.account_balance)
assert risk_manager.account_balance == 300.0, "Capital mismatch!"

print("Max DD:", risk_manager.max_daily_dd)
assert risk_manager.max_daily_dd == 0.02, "DD limit not strict!"

print("✅ All checks passed. Ready for launch.")
```

### T+0 (Launch)

```python
# Start trading engine
await trading_engine.start()

# Log launch event
logger.critical("🚀 LIVE TRADING LAUNCHED - 48h micro-budget phase")
logger.critical(f"Capital: $300, DD stop: 2%, Max position: 2%")
logger.critical("Kill-switch armed. Monitoring active.")

# Send launch notification
send_alert(
    level="INFO",
    message="🚀 Live trading started. 48h micro-budget phase activated.",
    details={"capital": 300, "dd_stop": "2%", "mode": "LIVE"}
)
```

---

## 4. Continuous Monitoring (48 hours)

### Every 5 Minutes

- [ ] Account balance stable
- [ ] No unexpected orders
- [ ] WebSocket connected
- [ ] Alert log clean (no CRIT)

### Every 1 Hour

- [ ] Review all trades (if any)
- [ ] Check daily P&L
- [ ] Verify positions match Binance
- [ ] Check latency metrics (p95)
- [ ] Confirm no stuck orders

### Every 6 Hours

- [ ] Export metrics snapshot
- [ ] Generate HTML report
- [ ] Verify cumulative metrics
- [ ] Review decision log
- [ ] Test kill-switch readiness

### Daily (06:00 UTC)

- [ ] Daily P&L summary
- [ ] Reset daily stats
- [ ] Review 24h incidents
- [ ] Assess DD utilization
- [ ] Plan Day 2 adjustments (if needed)

---

## 5. Alert Rules (Strict Mode)

### 🔴 CRITICAL (Immediate Action)

| Alert | Threshold | Action |
|-------|-----------|--------|
| Daily DD exceeded | > 2% | KILL-SWITCH: Close all positions |
| REST errors | ≥ 2 in 1 min | KILL-SWITCH: Pause orders, investigate |
| WS stale | > 60s no updates | KILL-SWITCH: Reconnect forced |
| Stuck order | > 5 min unfilled | Manual cancel + logs |

**Auto-response:**
```python
if alert.level == AlertLevel.CRIT:
    executor.mode = ExecutionMode.DRY_RUN  # Stop new orders
    await close_all_positions()              # Exit gracefully
    logger.critical(f"KILL-SWITCH: {alert.message}")
    send_alert(level="CRIT", message=f"Live trading halted: {alert.message}")
```

### 🟡 WARNING (Monitor + Report)

| Alert | Threshold | Action |
|-------|-----------|--------|
| Latency high | p95 > 1.5s | Log, monitor trend |
| WS reconnects | > 4/day | Log, check network |
| Order rejected | > 2%/hour | Log, check risk rules |
| Fill rate low | < 85% | Log, possible liquidity issue |

**Auto-response:**
```python
if alert.level == AlertLevel.WARN:
    logger.warning(f"Alert: {alert.message}")
    send_alert(level="WARN", message=alert.message)
```

---

## 6. Success Criteria (48h Gate)

### Must-Pass Metrics

| Metric | Target | Pass Criteria |
|--------|--------|---------------|
| **CRITICAL Alerts** | 0 | No kill-switch triggers |
| **Fill Rate** | ≥ 90% | Market orders filling consistently |
| **Latency p95** | ≤ 2s | Both WS and REST |
| **WS Reconnects** | ≤ 4 | Stable connection |
| **REST Errors** | = 0 | No API failures |
| **Stuck Orders** | 0 | All orders resolve within 5 min |
| **Daily DD** | < 2% | Risk controls working |
| **No Data Loss** | ✅ | OrderTracker synced with Binance |

### Success Scenario

```
Day 1: 3 market orders, all filled, +$12 P&L
Day 2: 2 market orders, both filled, +$8 P&L
Total: 5 fills, +$20 P&L (+6.7%), 0 CRIT alerts ✅

→ PROCEED TO SCALE-UP
```

### Failure Scenario

```
Day 1: 1 CRIT alert (WS stale), kill-switch triggered
→ Investigate root cause
→ Do NOT proceed to scale-up until fixed
→ Plan retry on Day 3-4
```

---

## 7. Scale-up Decision (Post 48h Success)

### If Success ✅

**Gradual Scale:**
1. **Phase 3.1 (48-72h):** $300 → $600 (2×)
2. **Phase 3.2 (1 week):** $600 → $1,500 (2.5×)
3. **Phase 3.3 (2 weeks):** $1,500 → $5,000 (3.3×)

**Each phase requires:**
- [ ] Review metrics from previous phase
- [ ] No CRIT alerts or drift
- [ ] Risk parameters stay locked
- [ ] Fill rate stable

**Adding new symbols (after 72h):**
```yaml
symbols:
  - BTCUSDT  # Stable base
  - ETHUSDT  # Add after validation
  # Later: BNBUSDT, ADAUSDT (low-vol safe pairs)
```

### If Failure ❌

**Immediate Actions:**
1. Kill-switch activation (automatic or manual)
2. Close all positions
3. Post-mortem review
4. Root cause analysis
5. Code/config fixes
6. Retry after fixes verified

**Retry Timeline:**
- [ ] Fix implementation & testing: 24h
- [ ] Dry-run re-validation: 24h
- [ ] Launch attempt 2: Day 4-5

---

## 8. Operational Procedures

### Daily Standup (06:00 UTC)

**Attendees:** Trading lead, engineer, risk officer

**Agenda:**
1. 24h summary (trades, P&L, alerts)
2. Metric review (latency, reconnects, fill rate)
3. Decision logs (any rejections?)
4. Scale-up assessment (proceed or hold)
5. Risks & adjustments

**Decision:**
- [ ] Continue as-is
- [ ] Pause (investigate)
- [ ] Scale up (if criteria met)

### Incident Response

**Severity 🔴 CRIT:**
- [ ] Pause trading (mode = DRY_RUN)
- [ ] Close positions (manual if needed)
- [ ] Investigate (check logs, API, network)
- [ ] Fix or wait
- [ ] Resume (after fix + re-test)

**Severity 🟡 WARN:**
- [ ] Log and monitor
- [ ] Determine root cause (next 1h)
- [ ] Plan mitigation (if needed)
- [ ] Continue trading

### Kill-switch Activation (Manual)

```python
# If something feels wrong (gut check)
await trading_engine.stop()
executor.mode = ExecutionMode.DRY_RUN

# Or automatic (DD > 2%)
# System triggers automatically
```

---

## 9. Launch Checklist

### Pre-Launch (T-24h)

- [ ] Infrastructure: API, WS, network verified
- [ ] Code: Deployed, config locked, secrets set
- [ ] Team: On-call, briefing done, runbook reviewed
- [ ] Monitoring: Dashboard live, alerts routed
- [ ] Capital: $300 transferred to API account
- [ ] Risk params: All locked and verified
- [ ] Dry-run: 7-day completed with CRIT=0

### Launch Day (T+0)

- [ ] Final system check (5 min)
- [ ] Launch command executed
- [ ] Launch notification sent
- [ ] Dashboard monitored (live)
- [ ] Alerts enabled
- [ ] Team notified

### End of Day 1 (18:00 UTC)

- [ ] Review trades
- [ ] Check P&L
- [ ] Verify positions
- [ ] Export metrics
- [ ] Standup meeting
- [ ] Document decision (continue / pause)

### End of Day 2 (18:00 UTC)

- [ ] Final review
- [ ] Success/failure assessment
- [ ] Scale-up decision
- [ ] Sign-off from risk officer
- [ ] Update GO_NO_GO_DECISION.md

---

## 10. Communication Template

### Launch Notification
```
🚀 LIVE TRADING LAUNCHED

Mode:     LIVE (mainnet)
Capital:  $300 (micro-budget)
Duration: 48 hours
DD Stop:  2%
Symbols:  BTCUSDT, ETHUSDT

Kill-switch armed. Monitoring active.
Standup at 06:00 UTC daily.
```

### Daily Status (06:00 UTC)
```
📊 24h Summary

P&L:      +$XX (+XX%)
Trades:   N fills
Max DD:   X.X%
Alerts:   0 CRIT, X WARN

Status:   ✅ NOMINAL / ⚠️ CAUTION / 🛑 HALTED
Decision: CONTINUE / PAUSE / SCALE-UP
```

### Scale-up Approval
```
✅ 48h SUCCESS

All KPIs met:
- CRIT alerts: 0
- Fill rate: 92%
- Latency stable
- No data loss

Decision: APPROVED FOR SCALE-UP
New capital: $600 (2×)
Effective: 2025-01-29 06:00 UTC
```

---

**Document Control**
- **Created:** 2025-01-26
- **Version:** 1.0
- **Status:** Ready for Launch (pending GO approval)
- **Next Update:** Post-Launch Review (2025-01-28)


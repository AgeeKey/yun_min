# RUNBOOK: Live Trading Safety & Operations

## Overview

This runbook covers operational procedures for live trading:
- Pre-launch checks (Go/No-Go gate)
- Failure response playbooks
- Kill-switch procedures
- Escalation paths
- Rollback procedures

**Severity Levels**
- 🟢 **INFO**: Informational, no action needed
- 🟡 **WARN**: Warning, monitor closely, may need intervention
- 🔴 **CRIT**: Critical, immediate action required

---

## 1. Pre-Launch Checklist (Go/No-Go Gate)

**Must complete before switching from dry-run to live trading:**

### System Validation (1-2 hours)

- [ ] **API Connectivity**
  ```bash
  # Test Binance API endpoints
  curl -X GET https://api.binance.com/api/v3/ping
  curl -X GET https://api.binance.com/api/v3/time
  ```
  ✅ Response: HTTP 200 with valid timestamp

- [ ] **WebSocket Connectivity**
  ```python
  # Test user stream
  from yunmin.core.websocket_layer import WebSocketLayer
  ws = WebSocketLayer(api_key=KEY, api_secret=SECRET, testnet=False)
  await ws.subscribe_user_data()
  # Monitor for 30 seconds, expect order/fill events
  ```
  ✅ Receives events without disconnects

- [ ] **RiskManager Enforcement**
  ```python
  # Verify kill-switch works
  risk_mgr = RiskManager(max_daily_dd=0.15)
  # Manually set position to exceed DD
  result = risk_mgr.validate_order(...)
  assert not result.success  # Must be rejected
  ```
  ✅ Rejects orders when thresholds breached

- [ ] **Executor Mode Verification**
  ```python
  # Ensure Executor in correct mode
  from yunmin.core.executor import ExecutionMode
  assert executor.mode == ExecutionMode.PAPER  # For testnet
  assert executor.max_retries == 3
  ```
  ✅ Mode is PAPER (testnet) or LIVE (mainnet)

### Testnet Trading (2-3 hours)

- [ ] **Place Market Order**
  - Symbol: BTCUSDT (testnet)
  - Qty: 0.001 BTC
  - Expected: Order appears in tracker within 5s

- [ ] **Verify Fill Event**
  - WebSocket receives execution report
  - OrderTracker state = FILLED
  - Position correctly updated

- [ ] **Monitor Metrics**
  ```python
  stats = risk_manager.get_daily_stats()
  assert stats['trades_count'] == 1
  assert stats['net_pnl'] >= 0  # Testnet may be noisy
  ```
  ✅ Stats correctly calculated

- [ ] **Test Cancel Order**
  - Place LIMIT order (unlikely to fill)
  - Cancel immediately
  - Verify state = CANCELLED

### Dry-Run Stability (24 hours minimum before live)

- [ ] **Run dry-run for ≥24 hours**
  - No CRITICAL alerts
  - Fill rate > 90%
  - WS reconnects < 5
  - REST errors = 0

- [ ] **Verify Daily Reset**
  ```python
  # Check metrics reset at UTC midnight
  stats_before = risk_manager.get_daily_stats()
  # Wait for UTC midnight...
  stats_after = risk_manager.get_daily_stats()
  assert stats_after['trades_count'] == 0
  ```
  ✅ Daily metrics reset correctly

- [ ] **Monitor Capital**
  ```
  Initial: $10,000
  After 24h: $9,900 - $10,100 (±1% acceptable)
  ```
  ✅ P&L stable, no unexpected drift

### Final Go/No-Go Decision

**GO ✅ if:**
- ✅ All system validation passed
- ✅ Testnet trades successful
- ✅ 24h dry-run without CRITICAL alerts
- ✅ Metrics repeatable and stable
- ✅ Team sign-off on risk parameters

**NO-GO ❌ if:**
- ❌ Any API connectivity issue
- ❌ RiskManager not enforcing limits
- ❌ >1 CRITICAL alert in dry-run
- ❌ Fill rate < 90%
- ❌ Unexplained P&L drift

---

## 2. Live Trading (Phase 3+)

### Launch Procedure

**1. Activate Live Mode** (5 min before market)
```python
executor.mode = ExecutionMode.LIVE  # Switch from PAPER
connector.testnet = False           # Use mainnet
logger.info("LIVE MODE ACTIVATED - Proceeding with caution")
```

**2. Start Monitoring Dashboard**
```bash
# Terminal 1: Live metrics
watch -n 5 'tail -20 ./dry_run_data/metrics_live.json | jq'

# Terminal 2: Alert log
tail -f ./logs/trading.log | grep -i "CRIT\|WARN"

# Terminal 3: Error tracking
tail -f ./logs/errors.log
```

**3. Initial Capital Verification**
```python
# Before any orders
account = connector.get_account()
balance = account['totalWalletBalance']
logger.info(f"Account Balance: ${balance:.2f}")
assert balance > 0, "No balance available!"
```

### Monitoring (First 24 hours critical)

**Every 5 minutes:**
- [ ] Check live account balance
- [ ] Verify no unexpected orders
- [ ] Confirm WebSocket connected
- [ ] Check alert log (should be clean)

**Every 1 hour:**
- [ ] Review trade log (if any trades)
- [ ] Check daily P&L
- [ ] Verify position tracking matches Binance
- [ ] Check metrics (DD, fees, latency)

**Every 6 hours:**
- [ ] Export metrics snapshot
- [ ] Verify no stuck orders
- [ ] Check cumulative P&L drift
- [ ] Validate decision logging

---

## 3. Failure Scenarios & Response

### 🟡 WARNING: High Latency (> 2s)

**Symptoms:**
- REST API responses slow (> 2000ms)
- WebSocket updates delayed

**Response:**
1. Check network connectivity
   ```bash
   ping api.binance.com
   curl -I https://api.binance.com/api/v3/ping
   ```

2. Check system resources
   ```bash
   top -b | head -20  # CPU/Memory
   netstat -s         # Network stats
   ```

3. If persistent:
   - Increase REST timeout (e.g., 5s → 10s)
   - Reduce order frequency
   - Consider temporary pause

**Auto-remediation:** None (alert only)

---

### 🟡 WARNING: WS Reconnects (>6/hour)

**Symptoms:**
```
WARN: High WS reconnect rate: 8/hour
Alert triggers after 6 reconnects in 60 min
```

**Response:**
1. Check WebSocket health
   ```python
   ws_health = engine.websocket.get_health()
   print(f"Connected: {ws_health['connected']}")
   print(f"Last update: {ws_health['last_update_ms']}ms ago")
   ```

2. If reconnecting rapidly (< 5s intervals):
   - Kill-switch may be imminent
   - Check for network issues
   - Consider graceful pause (stop new orders)

3. Monitor listen key refresh
   ```python
   # Should refresh every 30 min automatically
   # If failing, manually trigger:
   new_key = connector.get_listen_key()
   ws.listen_key = new_key
   ```

**Recovery:**
```python
# If WS dies completely:
await engine.websocket.close()
await engine.websocket.subscribe_user_data()
logger.info("WebSocket reconnected")
```

---

### 🟡 WARNING: REST Errors (2+ in 1 minute)

**Symptoms:**
```
WARN: REST errors exceed threshold: 3/min
order placement failed: {...}
```

**Response:**
1. Check Binance status
   - https://status.binance.com
   - Twitter @binanceops

2. Check specific errors
   ```python
   # Review error log
   tail -50 ./logs/errors.log | grep REST
   ```

3. If connection errors (HTTP 5xx):
   - Wait 30 seconds, retry
   - Do NOT increase frequency

4. If validation errors (HTTP 4xx):
   - Check order parameters
   - Verify balance sufficient
   - Check position limits

**Auto-remediation:** Exponential backoff (1s, 2s, 4s, 8s)

---

### 🔴 CRITICAL: Kill-Switch Activated

**Symptoms:**
```
CRIT: Kill-switch activated: max_dd_exceeded
CRIT: Kill-switch activated: excessive_rest_errors
CRIT: Kill-switch activated: ws_stale_60s
```

**Immediate Actions (within 2 minutes):**
1. **Stop new orders**
   ```python
   executor.mode = ExecutionMode.DRY_RUN
   logger.error("KILL-SWITCH: Stopping new orders")
   ```

2. **Cancel pending orders**
   ```python
   for order_id in tracker.get_open_orders():
       executor.cancel_order(symbol, order_id)
       logger.info(f"Cancelled order: {order_id}")
   ```

3. **Close positions** (if critical)
   ```python
   # For max_dd_exceeded: may want to hold
   # For ws_stale: MUST close (no updates)
   # For rest_errors: assess market conditions
   ```

4. **Alert team immediately**
   ```python
   send_slack("🚨 KILL-SWITCH: {reason}\n"
              f"Current DD: {dd*100:.1f}%\n"
              f"Action: Stopping new orders")
   ```

5. **Log full state**
   ```python
   engine.export_metrics("./dry_run_data/kill_switch_snapshot.json")
   ```

**Investigation (next 30 minutes):**
- [ ] Root cause identification
- [ ] Review last 50 events
- [ ] Check market conditions
- [ ] Verify no stuck orders
- [ ] Assess trading vs holding

**Recovery (if safe):**
```python
# After root cause fixed
if reason == "excessive_rest_errors":
    # Verify API connectivity restored
    # Gradually re-enable orders
    executor.mode = ExecutionMode.PAPER
    await asyncio.sleep(5)
    executor.mode = ExecutionMode.LIVE
    logger.info("Kill-switch cleared, resuming trading")
```

---

### 🔴 CRITICAL: WebSocket Stale (>60s no updates)

**Symptoms:**
```
CRIT: WebSocket stale for 65000ms
No updates from user data stream
Orders not being tracked
```

**Immediate Response:**
1. **Do NOT place orders** (can't track fills)
2. **Pause trading loop**
   ```python
   executor.mode = ExecutionMode.DRY_RUN
   ```

3. **Force WebSocket reconnect**
   ```python
   await engine.websocket.close()
   await engine.websocket.subscribe_user_data()
   logger.info("WebSocket forced reconnect")
   ```

4. **Sync OrderTracker with REST API**
   ```python
   # Get all open orders from Binance
   for symbol in config.symbols:
       orders = connector.get_open_orders(symbol)
       for order in orders:
           # Update tracker if not present
           if not tracker.get_order(order['clientOrderId']):
               logger.warn(f"Syncing missing order: {order['clientOrderId']}")
   ```

5. **Verify position sync**
   ```python
   # Get balances from Binance
   balances = connector.get_balances()
   # Compare with tracker positions
   # Log any discrepancies
   ```

**Do NOT resume until:**
- ✅ WebSocket reconnected
- ✅ Receiving live updates
- ✅ Order position sync verified
- ✅ Risk parameters still intact

---

### 🔴 CRITICAL: Daily DD Exceeded (> 20% hard limit)

**Symptoms:**
```
CRIT: Drawdown 21.5% exceeds hard limit 20%
All orders blocked
```

**Response:**
1. **No new orders allowed** (executor rejects)
2. **Close losing positions** (optional, depends on recovery plan)
3. **Hold cash until reset** (next UTC midnight)
4. **Full trade review**
   - All trades that day
   - Why were they losers?
   - Any execution issues?

5. **Post-mortem**
   ```python
   stats = risk_manager.get_daily_stats()
   print(f"Trades today: {stats['trades_count']}")
   print(f"Winning: {stats['winning_trades']}")
   print(f"Losing: {stats['losing_trades']}")
   print(f"Net PnL: {stats['net_pnl']:.2f}")
   ```

**Recovery:**
- System automatically resets at UTC midnight
- Verify trading works next day
- Consider reducing position size

---

### 🔴 CRITICAL: Stuck Orders (not filled or cancelled)

**Symptoms:**
```
Order placed 30+ min ago
Status: SUBMITTED (not filled)
Cancellation failed
```

**Response:**
1. **Get latest order status**
   ```python
   order = connector.get_order(symbol, order_id)
   print(f"Status: {order['status']}")
   print(f"Filled: {order['executedQty']}")
   print(f"Timestamp: {order['time']}")
   ```

2. **If can be cancelled:**
   ```python
   result = connector.cancel_order(symbol, order_id)
   tracker.cancel_order(order_id)
   logger.info(f"Cancelled stuck order: {order_id}")
   ```

3. **If stuck in FILLED state:**
   ```python
   # Manually update tracker
   tracker.set_exchange_id(order_id, binance_oid)
   tracker.add_fill(
       client_order_id=order_id,
       qty=order['executedQty'],
       price=order['price'],
       fee=order['fills'][0]['commission'],
       fee_asset='USDT'
   )
   ```

4. **If no resolution:**
   - Pause trading
   - Contact Binance support
   - Manually track position offline

---

## 4. Escalation & Communication

### Alert Routing

| Severity | Who | Method | Timeout |
|----------|-----|--------|---------|
| INFO | Monitoring | Log | - |
| WARN | On-duty trader | Slack | 15 min |
| CRIT | On-duty + backup | Slack + SMS | 5 min |
| CRIT (persistent) | Manager | Call + SMS | 2 min |

### Communication Template

**WARN Alert:**
```
🟡 WARNING: High WS reconnects (8/hour)
Impact: Orders may be slow to confirm
Action: Monitor closely, possible pause if continues
Status: Auto-monitoring, no action needed
```

**CRIT Alert:**
```
🚨 CRITICAL: Kill-switch activated (max DD exceeded)
Impact: NEW ORDERS STOPPED
Reason: Daily drawdown 21.5% > 20% hard limit
Action: IMMEDIATE investigation required
Status: Holding cash, no fill tracking
```

---

## 5. Rollback Procedures

### Scenario: Bugs in live trading

**If discovered mid-day:**
1. Activate kill-switch immediately
   ```python
   engine.websocket.close()
   executor.mode = ExecutionMode.DRY_RUN
   logger.critical("ROLLBACK: Switching to dry-run mode")
   ```

2. Do NOT place new orders

3. Close positions gradually
   - For bugs affecting execution: exit immediately
   - For bugs affecting monitoring: hold and fix

4. Deploy fix in parallel
   - Do NOT restart trading until deployed

5. Verify fix in dry-run for ≥30 min

6. Resume with caution
   - Smaller position sizes
   - Increased monitoring

### Scenario: Market conditions deteriorating

**If volatility spikes or crash imminent:**
1. Reduce position size 50%
2. Increase order cancellation timeouts
3. Hold more cash (reduce exposure)
4. Increase alert thresholds temporarily

**If market halted/circuit breaker triggered:**
1. Stop all trading immediately
2. Wait for market to reopen
3. Reassess all positions
4. Resume carefully

---

## 6. Runbook Maintenance

**Update this runbook:**
- [ ] After each incident (add new failure scenario)
- [ ] Monthly (review for accuracy)
- [ ] When risk parameters change
- [ ] When infrastructure changes

**Review checklist:**
- [ ] All commands still valid?
- [ ] Contact info current?
- [ ] Procedures tested?
- [ ] Team trained?

---

## Emergency Contacts

**On-duty Trader:** [Phone/Slack]
**Backup Operator:** [Phone/Slack]
**Engineering Lead:** [Phone/Slack]
**Binance Support:** [Email/Ticket System]

**Escalation Time:** 
- INFO → WARN: 15 min
- WARN → CRIT: 5 min  
- CRIT → Rollback: 2 min

---

**Last Updated:** 2025-01-26
**Version:** 1.0
**Status:** Ready for Live Trading

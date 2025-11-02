# Alert Rules (Phase 3 - Live Trading)

**Purpose:** Define alert triggers, severity levels, and automated responses for live trading monitoring.

**Alert Levels:** INFO (informational) | WARN (monitor, may require adjustment) | CRIT (immediate action required)

---

## 1. Critical Alert Rules (🔴 CRIT)

### Daily Drawdown Exceeded

**Rule ID:** `CRIT_DAILY_DD`

| Parameter | Value |
|-----------|-------|
| **Metric** | Daily Drawdown |
| **Threshold** | > 2.0% |
| **Check Interval** | Every 1s (real-time) |
| **Auto-Action** | KILL_SWITCH → Close all positions |
| **Manual Override** | No (forced) |

**Logic:**
```python
if (current_balance - peak_daily_balance) / peak_daily_balance > 0.02:
    trigger_kill_switch()
    close_all_positions()
    log_critical("Daily DD exceeded 2% - kill switch triggered")
```

**Notification:**
```
🔴 CRITICAL: Daily Drawdown Exceeded
Current DD: 2.3%
Peak Balance: $300.00
Current Balance: $293.10
Action: KILL_SWITCH - Closing all positions
```

---

### WebSocket Stale (No Updates)

**Rule ID:** `CRIT_WS_STALE`

| Parameter | Value |
|-----------|-------|
| **Metric** | Time since last WS update |
| **Threshold** | > 60 seconds |
| **Check Interval** | Every 5s |
| **Auto-Action** | Force reconnect, then KILL_SWITCH if fails |
| **Manual Override** | No (forced) |

**Logic:**
```python
time_since_last_ws_update = time.time() - last_ws_message_time
if time_since_last_ws_update > 60:
    log_critical(f"WS stale for {time_since_last_ws_update}s - reconnecting")
    await ws_layer.reconnect()
    if not await ws_layer.is_connected():
        trigger_kill_switch()
        log_critical("WS reconnection failed - kill switch triggered")
```

**Notification:**
```
🔴 CRITICAL: WebSocket Stale
Last Update: 2025-01-26 12:15:30 UTC (75s ago)
Action: Force reconnect
Fallback: Kill-switch if reconnect fails
```

---

### REST API Error Rate High

**Rule ID:** `CRIT_REST_ERRORS`

| Parameter | Value |
|-----------|-------|
| **Metric** | REST errors in 1-min window |
| **Threshold** | ≥ 2 consecutive errors |
| **Check Interval** | Every 10s |
| **Auto-Action** | Pause orders, escalate |
| **Manual Override** | May retry after 60s |

**Logic:**
```python
rest_errors_last_minute = [e for e in error_log if time.time() - e['timestamp'] < 60]
if len(rest_errors_last_minute) >= 2:
    log_critical(f"REST errors: {len(rest_errors_last_minute)} in 1 min")
    executor.pause_orders()
    send_alert(level="CRIT", message=f"REST API errors: {errors}")
    # Can retry after manual inspection
```

**Notification:**
```
🔴 CRITICAL: REST API Errors
Count (1m): 2 errors
Errors:
  - 14:25:10: 429 Too Many Requests
  - 14:25:22: 503 Service Unavailable
Action: Order placement PAUSED - await engineer review
```

---

### Stuck Order (Unfilled > 5 minutes)

**Rule ID:** `CRIT_STUCK_ORDER`

| Parameter | Value |
|-----------|-------|
| **Metric** | Time in "NEW" state (unfilled) |
| **Threshold** | > 5 minutes |
| **Check Interval** | Every 30s |
| **Auto-Action** | Cancel order + log |
| **Manual Override** | No (automatic cancel) |

**Logic:**
```python
for order_id, order in open_orders.items():
    time_open = time.time() - order['created_time']
    if time_open > 300:  # 5 minutes
        log_critical(f"Stuck order {order_id} for {time_open}s - canceling")
        await cancel_order(order_id)
        send_alert(level="CRIT", message=f"Stuck order canceled: {order_id}")
```

**Notification:**
```
🔴 CRITICAL: Stuck Order
Order ID: 2147483648
Symbol: BTCUSDT
Type: LIMIT
Created: 2025-01-26 14:20:00 UTC (7m 42s ago)
Status: NEW (unfilled)
Action: Order CANCELED - manual investigation required
```

---

### Hard Drawdown Limit (Emergency Stop)

**Rule ID:** `CRIT_HARD_DD`

| Parameter | Value |
|-----------|-------|
| **Metric** | Daily Drawdown |
| **Threshold** | > 5.0% (hard limit) |
| **Check Interval** | Every 1s |
| **Auto-Action** | EMERGENCY_STOP → Close all + disable trading |
| **Manual Override** | No |

**Logic:**
```python
if daily_dd > 0.05:
    log_critical("EMERGENCY: Hard DD limit (5%) exceeded - disabling trading")
    await close_all_positions(market_order=True)
    executor.disable_trading()
    trigger_emergency_alert("HARD_DD_LIMIT_EXCEEDED")
```

**Notification:**
```
🔴 EMERGENCY: Hard Drawdown Limit Exceeded
Current DD: 5.8%
Limit: 5.0%
Action: EMERGENCY_STOP
  - All positions closed at market
  - Trading DISABLED
  - Engineer notification sent
  - Post-mortem review required
```

---

## 2. Warning Alert Rules (🟡 WARN)

### High Latency

**Rule ID:** `WARN_HIGH_LATENCY`

| Parameter | Value |
|-----------|-------|
| **Metric** | REST/WS latency p95 |
| **Threshold** | > 1,500 ms |
| **Check Interval** | Every 60s |
| **Auto-Action** | Log + report |
| **Manual Override** | Monitor, may adjust strategy |

**Logic:**
```python
latency_p95 = percentile(latency_samples, 0.95)
if latency_p95 > 1500:
    log_warning(f"High latency: {latency_p95}ms")
    send_alert(level="WARN", message=f"REST latency p95: {latency_p95}ms - above target")
```

**Notification:**
```
🟡 WARNING: High Latency
REST p95: 1,850 ms (target: ≤ 1,500 ms)
WS p95: 125 ms (nominal)
Assessment: REST API slower than normal
Action: Monitor next 10 minutes; consider reducing order frequency
```

---

### WebSocket Reconnects High

**Rule ID:** `WARN_WS_RECONNECTS`

| Parameter | Value |
|-----------|-------|
| **Metric** | WS reconnect count |
| **Threshold** | > 4 per day |
| **Check Interval** | Daily (06:00 UTC) |
| **Auto-Action** | Log + report |
| **Manual Override** | Investigate network |

**Logic:**
```python
daily_reconnects = sum(1 for r in reconnect_log if is_today(r['timestamp']))
if daily_reconnects > 4:
    log_warning(f"WS reconnects today: {daily_reconnects}")
    send_alert(level="WARN", message=f"WS reconnected {daily_reconnects}x today - network may be unstable")
```

**Notification:**
```
🟡 WARNING: WebSocket Reconnects High
Count (24h): 5 reconnects
Log:
  - 06:15: Connection timeout (recovered in 3s)
  - 08:42: Unexpected disconnect (recovered in 2s)
  - 10:30: Network latency spike (recovered in 5s)
  - 14:20: Binance API restart (recovered in 1s)
  - 16:55: Connection reset (recovered in 4s)
Action: Check ISP/network stability; consider VPN
```

---

### Order Rejection Rate High

**Rule ID:** `WARN_REJECT_RATE`

| Parameter | Value |
|-----------|-------|
| **Metric** | Rejected orders / total orders |
| **Threshold** | > 2% in 1-hour window |
| **Check Interval** | Every 10 min |
| **Auto-Action** | Log + investigate |
| **Manual Override** | Adjust order params |

**Logic:**
```python
hour_window = [o for o in order_log if time.time() - o['timestamp'] < 3600]
rejects = sum(1 for o in hour_window if o['status'] == 'REJECTED')
total = len(hour_window)
reject_rate = rejects / total if total > 0 else 0

if reject_rate > 0.02:
    log_warning(f"Reject rate: {reject_rate*100:.1f}% (threshold: 2%)")
    send_alert(level="WARN", message=f"Order rejection rate: {reject_rate*100:.1f}%")
```

**Notification:**
```
🟡 WARNING: Order Rejection Rate High
Rate (1h): 3.2% (target: ≤ 2%)
Details:
  - Total orders: 125
  - Rejected: 4
  - Common reason: Insufficient balance (2), Invalid price (1), Duplicate (1)
Action: Review risk parameters; ensure balance adequate
```

---

### Fill Rate Low

**Rule ID:** `WARN_FILL_RATE`

| Parameter | Value |
|-----------|-------|
| **Metric** | Market fills / total market orders |
| **Threshold** | < 85% |
| **Check Interval** | Every 6 hours |
| **Auto-Action** | Log + report |
| **Manual Override** | Adjust order sizing |

**Logic:**
```python
market_orders = [o for o in order_log if o['type'] == 'MARKET' and time.time() - o['timestamp'] < 3600*6]
fills = sum(1 for o in market_orders if o['status'] == 'FILLED')
fill_rate = fills / len(market_orders) if market_orders else 1.0

if fill_rate < 0.85:
    log_warning(f"Fill rate: {fill_rate*100:.1f}%")
    send_alert(level="WARN", message=f"Market fill rate: {fill_rate*100:.1f}% (target: ≥ 85%)")
```

**Notification:**
```
🟡 WARNING: Market Fill Rate Low
Rate (6h): 78% (target: ≥ 85%)
Details:
  - Market orders: 23
  - Filled: 18
  - Partial: 3
  - Unfilled: 2
Action: Check bid-ask spreads; may indicate low liquidity
```

---

### Daily Trade Count High

**Rule ID:** `WARN_HIGH_TRADE_COUNT`

| Parameter | Value |
|-----------|-------|
| **Metric** | Trades per day |
| **Threshold** | > 50% of daily limit |
| **Check Interval** | Every 4 hours |
| **Auto-Action** | Log + report |
| **Manual Override** | Monitor strategy |

**Logic:**
```python
daily_trade_count = sum(1 for t in trade_log if is_today(t['timestamp']))
daily_limit = risk_manager.max_daily_trades
utilization = daily_trade_count / daily_limit

if utilization > 0.50:
    log_warning(f"Daily trades: {daily_trade_count}/{daily_limit} ({utilization*100:.0f}% utilized)")
    send_alert(level="WARN", message=f"Daily trade count: {daily_trade_count} (limit: {daily_limit})")
```

**Notification:**
```
🟡 WARNING: High Daily Trade Count
Count: 12 / 20 (60% of limit)
Remaining today: 8 trades
Assessment: Good pace; monitor for overactivity
Action: None (nominal); continue trading if signals present
```

---

### Commission/Fee Impact High

**Rule ID:** `WARN_HIGH_FEES`

| Parameter | Value |
|-----------|-------|
| **Metric** | Total fees / total P&L |
| **Threshold** | > 25% |
| **Check Interval** | Daily |
| **Auto-Action** | Log + report |
| **Manual Override** | Optimize order params |

**Logic:**
```python
total_fees = sum(f['amount'] for f in fee_log if is_today(f['timestamp']))
total_pnl = calculate_daily_pnl()
fee_impact = total_fees / total_pnl if total_pnl > 0 else 0

if fee_impact > 0.25:
    log_warning(f"Fee impact: {fee_impact*100:.1f}% of P&L")
    send_alert(level="WARN", message=f"Fees are {fee_impact*100:.0f}% of P&L")
```

**Notification:**
```
🟡 WARNING: High Fee Impact
Daily fees: $2.50
Daily P&L: +$8.00
Impact: 31.25% of profit
Assessment: Trading too frequently relative to returns
Action: Consider reducing trade frequency or using limit orders
```

---

## 3. Informational Alert Rules (ℹ️ INFO)

### Order Executed Successfully

**Rule ID:** `INFO_ORDER_FILL`

| Parameter | Value |
|-----------|-------|
| **Trigger** | Order status = FILLED |
| **Check Interval** | Real-time |
| **Action** | Log + optional notification |

**Notification:**
```
ℹ️ Order Executed
Symbol: BTCUSDT
Side: BUY
Quantity: 0.001 BTC
Price: $45,250
Fill: Market
Commission: 0.1%
P&L: N/A (position entry)
```

---

### Position Opened

**Rule ID:** `INFO_POSITION_OPEN`

| Parameter | Value |
|-----------|-------|
| **Trigger** | Position created |
| **Check Interval** | Real-time |
| **Action** | Log + notification |

**Notification:**
```
ℹ️ Position Opened
Symbol: BTCUSDT
Side: LONG
Size: 0.001 BTC
Entry Price: $45,250
Notional: $45.25
Leverage: 1.0×
Risk per symbol: 0.15%
```

---

### Position Closed

**Rule ID:** `INFO_POSITION_CLOSE`

| Parameter | Value |
|-----------|-------|
| **Trigger** | Position size = 0 |
| **Check Interval** | Real-time |
| **Action** | Log + notification |

**Notification:**
```
ℹ️ Position Closed
Symbol: BTCUSDT
Side: LONG
Size: 0.001 BTC
Exit Price: $45,500
P&L: +$0.25 (+0.55%)
Exit Type: Market
Duration: 4m 30s
```

---

### Daily Summary

**Rule ID:** `INFO_DAILY_SUMMARY`

| Parameter | Value |
|-----------|-------|
| **Trigger** | Daily at 06:00 UTC |
| **Action** | Log + report |

**Notification:**
```
ℹ️ Daily Summary (2025-01-26)
Trades: 5 fills
P&L: +$12.50 (+4.17%)
Max DD: 1.2%
Fill Rate: 100%
Alerts: 0 CRIT, 0 WARN
Status: ✅ NOMINAL
Next check: 2025-01-27 06:00 UTC
```

---

## 4. Alert Routing & Escalation

### Alert Channels by Severity

| Severity | Channels | Escalation | Delay |
|----------|----------|------------|-------|
| **INFO** | Logs only | None | N/A |
| **WARN** | Logs + Slack | On-call engineer | 2 min |
| **CRIT** | Logs + Slack + Email + SMS | Trading lead + CTO | Immediate |

### Escalation Procedure

**CRIT Alert Path:**
1. Instant: Log event + Slack notification
2. T+30s: Email to trading lead
3. T+60s: SMS to on-call engineer (if no Slack ACK)
4. T+3min: Phone call to CTO

**WARN Alert Path:**
1. Instant: Log event
2. T+2min: Slack summary
3. T+30min: Email summary (if unresolved)

---

## 5. Alert Configuration Template

```yaml
# alerts.yaml - Live trading alert configuration

alerts:
  crit:
    daily_dd:
      threshold: 0.02
      check_interval_s: 1
      action: "kill_switch"
    
    ws_stale:
      threshold_s: 60
      check_interval_s: 5
      action: "reconnect"
      fallback: "kill_switch"
    
    rest_errors:
      threshold: 2
      window_s: 60
      check_interval_s: 10
      action: "pause_orders"
    
    stuck_order:
      threshold_s: 300
      check_interval_s: 30
      action: "cancel_and_log"
  
  warn:
    high_latency:
      threshold_ms: 1500
      percentile: 95
      check_interval_s: 60
    
    ws_reconnects:
      threshold: 4
      window_hours: 24
      check_interval_s: 60
    
    reject_rate:
      threshold: 0.02
      window_hours: 1
      check_interval_s: 600

# Channels
channels:
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
    enabled: true
  
  email:
    recipients:
      - "trading-lead@company.com"
      - "engineer@company.com"
    enabled: true
  
  sms:
    recipients:
      - "+1234567890"
    enabled: true
    crit_only: true

# Notification templates
templates:
  crit:
    header: "🔴 CRITICAL ALERT"
    include: ["metric", "threshold", "value", "action", "timestamp"]
  
  warn:
    header: "🟡 WARNING"
    include: ["metric", "threshold", "value", "timestamp"]
  
  info:
    header: "ℹ️ INFO"
    include: ["message", "timestamp"]
```

---

**Document Control**
- **Created:** 2025-01-26
- **Version:** 1.0
- **Status:** Ready for deployment
- **Review:** Pre-launch testing


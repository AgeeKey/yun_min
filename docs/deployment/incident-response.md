# Phase 4: Incident Response Playbook

**Purpose:** Detailed step-by-step procedures for responding to various production issues during live trading.

**Severity Levels:** 
- 🟢 **INFO** (log only)
- 🟡 **WARN** (monitor, may need action)
- 🔴 **CRIT** (immediate action required)

---

## 1. WebSocket Disconnection

### Symptom
- WebSocket connection drops
- Last update > 10s old
- Orders may not fill

### Severity: 🔴 CRITICAL (if > 60s)

### Response Flowchart

```
WS disconnected?
    ↓
Check: time_since_last_update > 60s?
    ├─ NO  (< 60s) → Automatic reconnect + monitor
    └─ YES (> 60s) → KILL_SWITCH + Manual intervention
```

### Step-by-step Response

**Step 1: Detect (automatic)**
```python
# System logs
2025-01-27 14:25:30 | CRIT | WebSocket stale: 75s
2025-01-27 14:25:30 | CRIT | Triggering kill-switch
```

**Step 2: Kill-switch activates (automatic)**
```
- Mode: LIVE → DRY_RUN
- Close all open positions at market
- Pause order placement
- Alert: Trading Lead + CTO
```

**Step 3: Investigate (engineer, < 5 min)**
```bash
# Check network connectivity
ping -c 5 stream.binance.com

# Check DNS
nslookup stream.binance.com

# Check firewall
sudo iptables -L | grep stream.binance.com

# Check local logs for errors
tail -50 ./logs/trading.log | grep -i "ws\|websocket\|error"
```

**Step 4: Recovery options**

**Option A: ISP/Network issue**
```bash
# Restart connection
ip link set eth0 down
sleep 5
ip link set eth0 up

# Verify
ping -c 3 api.binance.com
curl -s https://api.binance.com/api/v3/time | jq .
```

**Option B: Binance API issue**
```bash
# Check Binance status
curl -s https://api.binance.com/api/v3/ping

# Check status page
# Visit: https://www.binancestatus.com/

# If Binance is down:
# - Wait for recovery
# - Do NOT attempt to restart
# - Monitor status page
# - Resume after confirmed up
```

**Option C: Local application issue**
```bash
# Force reconnect
python -c "
from yunmin.core.websocket_layer import WebSocketLayer
ws = WebSocketLayer('BTCUSDT')
await ws.reconnect(force=True)
print('✅ Reconnected')
"

# Verify connection
curl -s http://localhost:8000/health | jq .ws_connected
# Should show: true
```

**Step 5: Restart (if recovered)**
```bash
# Restart trading engine
pkill -f "trading_engine"
sleep 2

python -m yunmin.core.trading_engine \
  --mode LIVE \
  --config config.prod.yaml
```

**Step 6: Verify (before resuming)**
```bash
# Check positions
python -c "
from yunmin.connectors.binance_connector import BinanceConnector
conn = BinanceConnector()
positions = conn.get_positions()
print(f'Open positions: {len(positions)}')
"

# Check account balance
python -c "
from yunmin.connectors.binance_connector import BinanceConnector
conn = BinanceConnector()
account = conn.get_account()
print(f'Balance: {account[\"totalWalletBalance\"]} USDT')
"
```

### Post-Incident Review

- [ ] Root cause identified: ________________________
- [ ] Time to detect: __ minutes
- [ ] Time to recover: __ minutes
- [ ] Impact: ________________________
- [ ] Prevention: ________________________

---

## 2. REST API Errors (4xx/5xx)

### Symptom
- 429 (Too Many Requests)
- 503 (Service Unavailable)
- 504 (Gateway Timeout)
- Repeated API failures

### Severity: 🔴 CRITICAL (≥ 2 errors in 1 min)

### Response

**Step 1: Assess**
```bash
# Check error rate (last 1 minute)
tail -200 ./logs/trading.log | \
  grep -E "429|503|504" | \
  wc -l

# If ≥ 2 errors:
# → PAUSE ORDERS (automatic)
# → Alert team
```

**Step 2: Identify Error Type**

**429 - Rate Limited:**
```bash
# Check request frequency
tail -100 ./logs/trading.log | grep "429"

# Solution: Reduce order frequency
# - Decrease decision_interval_s (increase)
# - Batch orders (if supported)
# - Wait for recovery (30-60s)
```

**Step 3: Check Binance Status**
```bash
# Query Binance API status
curl -s https://api.binance.com/api/v3/ping

# If responds: Binance is up
# If timeout: Binance may be down

# Check status page
# https://www.binancestatus.com/
```

**Step 4: Recovery**

**If rate limited (429):**
```python
# Automatic retry logic already in executor
# Wait 30s, then resume
# If still failing after 3 retries:
# → Manual pause + investigate
```

**If service unavailable (503):**
```bash
# DO NOT retry immediately
# Wait 60-120s for Binance recovery
# Monitor: curl -s https://api.binance.com/api/v3/ping

# Once recovered:
# Kill-switch may have closed positions
# Verify account state
# Resume if desired
```

### Post-Incident Review

- [ ] Error type: ________________________
- [ ] Frequency: __ errors / min
- [ ] Root cause: ________________________
- [ ] Resolution: ________________________

---

## 3. High Latency (> 2s)

### Symptom
- REST p95 latency > 2s
- WebSocket p95 latency > 500ms
- Order fills delayed
- System monitoring alerts

### Severity: 🟡 WARNING

### Response

**Step 1: Measure**
```bash
# Check current latency
python -c "
from yunmin.core.monitoring.latency_tracker import LatencyTracker
tracker = LatencyTracker()
print(f'REST p95: {tracker.rest_latency_p95}ms')
print(f'WS p95: {tracker.ws_latency_p95}ms')
"
```

**Step 2: Diagnose**

**If REST latency high:**
```bash
# Measure from your location
time curl -o /dev/null -s https://api.binance.com/api/v3/time
# Should be < 500ms

# Check route
traceroute api.binance.com
# Look for timeouts or long hops

# Check ISP
speedtest-cli
# Download/upload speeds OK?
```

**If WebSocket latency high:**
```bash
# Check connection quality
curl -s http://localhost:8000/ws_health | jq .

# Measure RTT
ping stream.binance.com
# Should be < 100ms
```

**If both high:**
```bash
# Likely ISP/network issue
# Check:
# - Router status
# - ISP status page
# - VPN (if used) - try disabling
```

**Step 3: Mitigation**

**Option A: Increase order timeouts**
```yaml
# config.prod.yaml
executor:
  timeout_ms: 7000  # Increase from 5000
```

**Option B: Reduce order frequency**
```yaml
# config.prod.yaml
trading_engine:
  decision_interval_s: 10  # Increase from 5
```

**Option C: Switch endpoint (if available)**
```bash
# Use different API endpoint
# - api1.binance.com
# - api2.binance.com
# - api3.binance.com
```

### Monitor Recovery
```bash
# Check latency every 5 min for 30 min
for i in {1..6}; do
  python -c "
  from yunmin.core.monitoring.latency_tracker import LatencyTracker
  tracker = LatencyTracker()
  print(f'{i*5}m: REST p95={tracker.rest_latency_p95}ms, WS p95={tracker.ws_latency_p95}ms')
  "
  sleep 300
done
```

---

## 4. Stuck Orders (Unfilled > 5 min)

### Symptom
- Order stuck in "NEW" state
- Not filling despite time passing
- Order value in limbo

### Severity: 🔴 CRITICAL (> 5 min)

### Response

**Step 1: Identify Stuck Orders**
```bash
# Find orders > 5 min old
python -c "
from yunmin.connectors.binance_connector import BinanceConnector
import time

conn = BinanceConnector()
orders = conn.get_open_orders()

now = time.time()
for order in orders:
    age_s = now - order['create_time']/1000
    if age_s > 300:  # 5 minutes
        print(f'STUCK: {order[\"symbol\"]} {order[\"side\"]} {order[\"qty\"]} at {order[\"price\"]} (age: {age_s/60:.1f}m)')
"
```

**Step 2: Cancel Stuck Orders**
```bash
# Cancel manually
python -c "
from yunmin.connectors.binance_connector import BinanceConnector

conn = BinanceConnector()
# Get stuck order ID (from above)
stuck_order_id = 2147483648

try:
    result = conn.cancel_order('BTCUSDT', stuck_order_id)
    print(f'✅ Canceled: {result}')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

**Step 3: Close Position (if needed)**
```bash
# If order was for opening position:
# Close at market to prevent hold-up

python -c "
from yunmin.core.executor import Executor

executor = Executor()
result = executor.close_position(
    symbol='BTCUSDT',
    order_type='MARKET'
)
print(f'Position closed: {result}')
"
```

**Step 4: Root Cause**
- [ ] Network issue? → Verify connectivity
- [ ] Order price? → Check bid-ask spread
- [ ] Liquidity? → Check volume on symbol
- [ ] API issue? → Check Binance status

### Prevention
```yaml
# config.prod.yaml
executor:
  max_order_age_s: 300  # Cancel if > 5 min
  cancel_and_reissue: true  # Auto retry
```

---

## 5. Daily Drawdown Limit Hit (DD > 2%)

### Symptom
- Cumulative loss > 2% of starting capital
- Kill-switch activates
- Trading halted

### Severity: 🔴 CRITICAL (automatic stop)

### Response

**Step 1: Automatic Actions**
```
- Kill-switch triggers
- All positions closed at market
- Mode: LIVE → DRY_RUN
- Alerts sent to team
```

**Step 2: Immediate Review (< 5 min)**
```bash
# What happened?
tail -50 ./logs/trading.log | grep "DD\|CRITICAL"

# Example:
# 2025-01-27 14:45:00 | CRIT | Daily DD: 2.1%
# 2025-01-27 14:45:00 | CRIT | Positions: 0
# 2025-01-27 14:45:00 | CRIT | KILL_SWITCH activated
```

**Step 3: Post-mortem (within 1 hour)**
```
Questions to answer:
1. What trades caused the loss?
2. Were risk limits enforced?
3. Was there a systematic issue?
4. Is the strategy fundamentally broken?

Example analysis:
- Trade 1: BTCUSDT, -$5.50 (fill issue, latency spike)
- Trade 2: BTCUSDT, -$3.20 (bad timing)
- Trade 3: ETHUSDT, -$4.80 (slippage)
- Total: -$13.50 / $300 = -4.5% DD ✅ Kill-switch worked

Root cause: Strategy made bad decisions in volatile market
```

**Step 4: Recovery Plan**

**Option A: Adjust risk parameters**
```yaml
# Tighten limits for next attempt
executor:
  max_position_pct: 0.01  # Reduce from 2%
  
risk_manager:
  max_daily_dd: 0.015  # Reduce from 2% to 1.5%
```

**Option B: Fix strategy logic**
```python
# Example: Add momentum check
if strategy.momentum > -2.0:  # Don't trade if very bearish
    decision = None
else:
    decision = strategy.decide()
```

**Option C: Increase capital buffer**
```yaml
# More capital = same % DD = more buffer
risk_manager:
  initial_capital: 500  # Increase from $300
  max_daily_dd: 0.02  # Keep at 2%, but higher absolute value
```

**Step 5: Approval for Retry**
- [ ] Root cause identified
- [ ] Fix tested in backtest
- [ ] Fix tested in paper/dry-run
- [ ] CTO approval
- [ ] Team briefing

**Step 6: Restart**
```bash
# Restart with new config
pkill -f "trading_engine"
sleep 2

python -m yunmin.core.trading_engine \
  --mode LIVE \
  --config config.prod.yaml
```

---

## 6. Position/Balance Sync Mismatch

### Symptom
- Local position != Binance position
- Balance mismatch
- Accounting error detected

### Severity: 🟡 WARNING → 🔴 CRITICAL (if large mismatch)

### Response

**Step 1: Detect Mismatch**
```bash
python -c "
from yunmin.core.order_tracker import OrderTracker
from yunmin.connectors.binance_connector import BinanceConnector

tracker = OrderTracker()
conn = BinanceConnector()

local_position = tracker.get_position('BTCUSDT')
binance_position = conn.get_position('BTCUSDT')

if local_position != binance_position:
    print(f'❌ MISMATCH:')
    print(f'  Local:   {local_position}')
    print(f'  Binance: {binance_position}')
    print(f'  Diff:    {abs(local_position - binance_position)}')
"
```

**Step 2: Assess Severity**

**Small mismatch (< 0.1% of position):**
- Likely rounding error
- Update local tracker to match Binance
- Log but don't stop trading

**Large mismatch (> 1% of position):**
- Potential lost order or double-fill
- Stop trading
- Investigate thoroughly
- Manual intervention may needed

**Step 3: Investigate**
```bash
# Check trade history
python -c "
from yunmin.connectors.binance_connector import BinanceConnector

conn = BinanceConnector()
trades = conn.get_my_trades('BTCUSDT')

# Show last 20 trades
for trade in trades[-20:]:
    print(f'{trade[\"time\"]}: {trade[\"side\"]} {trade[\"qty\"]} @ {trade[\"price\"]}')
"
```

**Step 4: Reconcile**

**If local is behind:**
```python
# Update local tracker from Binance
tracker.sync_with_exchange()
print('✅ Local tracker synced')
```

**If local is ahead:**
```python
# This suggests missing cancel or fill
# Check Binance for the missing event

# Manual fix:
tracker.reset_position()
tracker.load_from_binance()
print('✅ Position reset from Binance')
```

**Step 5: Prevention**
```python
# Increase sync frequency
sync_interval_s = 5  # Check every 5s

# Run continuous sync check
while True:
    tracker.sync_with_exchange()
    await asyncio.sleep(sync_interval_s)
```

---

## 7. Market Flash Crash (> 10% move in 1 min)

### Symptom
- Extreme price volatility
- Kill-switch may trigger
- Potential for severe loss

### Severity: 🔴 CRITICAL

### Response

**Step 1: Kill-switch activates (automatic)**
- If DD > 2%: Close all positions
- Pause trading
- Alert team

**Step 2: Team Decision (< 1 min)**
- [ ] Is this a real crash or data error?
- [ ] Check Binance order book
- [ ] Check multiple symbols
- [ ] If real crash: HALT trading
- [ ] If data error: Resume

**Step 3: Resume Criteria**
```
Only resume if ALL true:
- Price stabilized (< 1% move in 1 min)
- Order book looks normal
- Binance confirmed up
- 5 minutes have passed
- CTO approval
```

**Step 4: Post-crash Review**
- [ ] What caused the crash?
- [ ] How was it handled?
- [ ] Any losses?
- [ ] System worked as expected?

---

## 8. Kill-switch Stuck (Won't Turn Off)

### Symptom
- Kill-switch activated but won't stop
- Can't place new orders
- Mode stuck in DRY_RUN

### Severity: 🔴 CRITICAL

### Response

**Step 1: Emergency Stop**
```bash
# Kill the process
pkill -9 -f "trading_engine"
```

**Step 2: Manual Position Check**
```bash
# Verify all positions actually closed
python -c "
from yunmin.connectors.binance_connector import BinanceConnector
conn = BinanceConnector()
positions = conn.get_positions()
print(f'Open positions: {len(positions)}')
for p in positions:
    print(f'  {p[\"symbol\"]}: {p[\"positionAmt\"]}')
"

# If positions exist:
# - Close manually at market
# - Contact Binance support
```

**Step 3: Reset State**
```bash
# Clear local state
rm -f ./state/order_tracker.db
rm -f ./state/risk_manager.state

# Restart from clean state
python -m yunmin.core.trading_engine \
  --mode LIVE \
  --config config.prod.yaml \
  --reset-state
```

**Step 4: Verify**
```bash
# Check health endpoint
curl -s http://localhost:8000/health | jq .

# Should show:
# {
#   "status": "healthy",
#   "mode": "LIVE",
#   "positions": 0,
#   "kill_switch": false
# }
```

---

## 9. Emergency Contact Procedures

### Immediate (< 5 min)

**Level 1: Slack**
- Post in #trading-live
- Mention @trading-lead
- Include: incident name + action taken

**Level 2: Phone (if no Slack response)**
- Call trading-lead
- Message: "[INCIDENT] {name} — {status}"

### Within 5 min

**Level 2: CTO**
- Email: cto@company.com
- Subject: "[URGENT] {incident name}"
- Include: steps taken, current status

### Within 30 min

**Post-incident**
- Schedule review meeting
- Document root cause
- Plan prevention

---

## 10. Escalation Matrix

| Scenario | Response Time | Who to contact | Action |
|----------|---------------|----------------|----|
| WS stale > 60s | Immediate | Engineer + CTO | Kill-switch, investigate |
| REST errors ≥ 2 | Immediate | Engineer + CTO | Pause orders, diagnose |
| DD > 2% | Immediate | Trading Lead + CTO | Kill-switch auto |
| High latency | 10 min | Engineer | Monitor, adjust params |
| Stuck order > 5m | 5 min | Engineer | Cancel, close position |
| Mismatch > 1% | 5 min | Engineer + CTO | Stop, reconcile |

---

**Document Control**
- **Created:** 2025-01-26
- **Version:** 1.0
- **Status:** Ready for production
- **Last Updated:** 2025-01-26
- **Owner:** Trading Team Lead

**Print this document and keep near your desk during live trading.**


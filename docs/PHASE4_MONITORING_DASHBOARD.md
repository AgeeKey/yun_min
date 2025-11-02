# Phase 4: Monitoring Dashboard Guide

**Purpose:** Real-time visibility into system health, trading metrics, and alerts during live trading.

---

## 1. Dashboard Overview

### Main Metrics Display

```
╔════════════════════════════════════════════════════════════════════╗
║                    YUNMIN LIVE TRADING DASHBOARD                   ║
║                      2025-01-27 14:30:00 UTC                       ║
╚════════════════════════════════════════════════════════════════════╝

┌─ ACCOUNT STATUS ────────────────────────────────────────────────────┐
│                                                                      │
│  Balance: $300.00                  P&L: +$12.50 (+4.17%)           │
│  Available: $299.50                Daily DD: 0.8%                  │
│  Max Position: 2% = $6.00          Max DD: 2.0% (2.5x buffer) ✅   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌─ OPEN POSITIONS ────────────────────────────────────────────────────┐
│                                                                      │
│  Symbol         Side    Qty      Entry        Current      P&L      │
│  ──────────────────────────────────────────────────────────────────  │
│  BTCUSDT        LONG    0.001    $45,250      $45,320     +$0.70    │
│  ETHUSDT        SHORT   0.010    $2,800       $2,795      +$0.50    │
│                                                                      │
│  Total Exposure: 0.15% of capital                                  │
│  Avg Leverage: 1.0×                                                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌─ SYSTEM HEALTH ─────────────────────────────────────────────────────┐
│                                                                      │
│  WebSocket:     ✅ CONNECTED (15s ago)                             │
│  REST API:      ✅ OK (last: 200ms)                                │
│  Latency:       p50=45ms, p95=180ms, p99=280ms                     │
│  Reconnects:    0 (today)                                           │
│  Mode:          LIVE                                                │
│  Kill-switch:   ✅ ARMED                                            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌─ ALERTS (Last 24h) ─────────────────────────────────────────────────┐
│                                                                      │
│  🔴 CRIT:   0 (target: 0)  ✅ GOOD                                 │
│  🟡 WARN:   1 (target: ≤5) ✅ GOOD                                 │
│  ℹ️  INFO:   12 (trades, fills, etc)                               │
│                                                                      │
│  Recent: [14:25] High latency p95: 340ms (recovered)              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌─ TRADES (Last 5) ───────────────────────────────────────────────────┐
│                                                                      │
│  Time       Symbol    Side  Qty    Type    Price      Status  P&L   │
│  14:30:15   ETHUSDT   BUY   0.01   MARKET  $2,795    ✅FILL +$0.25 │
│  14:25:42   BTCUSDT   SELL  0.001  MARKET  $45,320   ✅FILL -$0.15 │
│  14:20:08   BTCUSDT   BUY   0.001  MARKET  $45,250   ✅FILL +$0.15 │
│  14:15:33   ETHUSDT   SELL  0.010  MARKET  $2,790    ✅FILL -$0.25 │
│  14:10:12   BTCUSDT   SELL  0.002  MARKET  $45,200   ✅FILL +$0.40 │
│                                                                      │
│  Fill rate: 5/5 = 100% ✅ (target: ≥90%)                          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌─ RISK METRICS ──────────────────────────────────────────────────────┐
│                                                                      │
│  Orders/min:   2.1 (target: ≤10)                ✅ Nominal         │
│  Daily trades: 5 (limit: 20)                    ✅ Nominal         │
│  Open orders:  0 (limit: 3)                     ✅ Nominal         │
│  Margin ratio: 0.0% (limit: 100%)               ✅ Nominal         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌─ CHARTS (Last 6h) ──────────────────────────────────────────────────┐
│                                                                      │
│  Cumulative P&L:                 Drawdown (Daily):                  │
│  $15  ┌─────────────────          ┌─────────────────                │
│       │    ╱╲      ╱╲    ╱        │                                 │
│  $10  │   ╱  ╲    ╱  ╲  ╱         │  0.8%                          │
│       │  ╱    ╲  ╱    ╲╱          │                                 │
│   $5  │ ╱      ╲╱                 │  0.4%                          │
│       └                           │                                 │
│   $0  08:00 10:00 12:00 14:00     │  0.0%                          │
│       └─────────────────          │  08:00 10:00 12:00 14:00       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Metrics Explained

### Account Metrics

**Balance:**
- Total USDT available in account
- Include open position P&L

**Available:**
- Free balance (not in positions)
- Available for new orders

**P&L (Total):**
- Total profit/loss since launch
- Percentage relative to starting capital

**Daily DD (Drawdown):**
- Cumulative loss so far today
- Resets at 00:00 UTC

**Max DD (Hard limit):**
- 5% hard stop (emergency)
- If exceeded, all trading stops

### Position Metrics

**Entry Price:**
- Price at which position opened
- Average price if multiple fills

**Current Price:**
- Last known market price
- From WebSocket

**P&L (Position):**
- Unrealized profit/loss
- Marked to market

**Avg Leverage:**
- For margin trading (always 1.0× for spot)

### System Health

**WebSocket:**
- GREEN ✅: Connected, receiving updates
- YELLOW ⚠️: Connected but slow (> 5s no update)
- RED ❌: Disconnected (will trigger kill-switch at 60s)

**REST API:**
- GREEN ✅: Last request OK (< 2s)
- YELLOW ⚠️: Slow (2-5s)
- RED ❌: Errors (429, 503, 504)

**Latency Percentiles:**
- **p50:** Median latency (50% of requests faster)
- **p95:** 95th percentile (95% faster, 5% slower)
- **p99:** 99th percentile (slower outliers)

**Reconnects:**
- Count of WebSocket reconnection events today
- Target: ≤ 3 per day

---

## 3. Alert System

### Alert Levels

```
🟢 GREEN (Nominal):
   - All metrics within targets
   - No alerts
   - Continue trading

🟡 YELLOW (Warning):
   - One or two metrics slightly elevated
   - Action recommended but not urgent
   - Continue trading with caution

🔴 RED (Critical):
   - Kill-switch triggered
   - Immediate action required
   - Trading halted automatically
```

### Common Alerts

| Alert | Threshold | Action | Recovery |
|-------|-----------|--------|----------|
| DD > 2% | > 2.0% | KILL_SWITCH | Manual review + restart |
| WS stale | > 60s | Force reconnect | Check network |
| REST errors | ≥ 2 in 1m | Pause orders | Wait 30s + retry |
| High latency | p95 > 2s | Log + monitor | Check ISP |
| Stuck order | > 5 min | Cancel order | Reissue or skip |
| No trades | > 6h | Alert | Check strategy |

### Alert History Panel

```
Recent Alerts (Last 24h):

14:25  🟡 WARN   High latency (p95: 340ms)
14:20  ℹ️  INFO   Trade: ETHUSDT BUY @2795
14:15  ℹ️  INFO   Trade: BTCUSDT SELL @45320
13:50  🟡 WARN   Reject rate: 3.5% (recoverd)
13:40  ℹ️  INFO   Daily standup: P&L +$8.50
```

---

## 4. Access & Login

### Web Dashboard

**URL:** `http://localhost:8000`

**Default Credentials:**
- Username: `trading`
- Password: (in `.env` as `DASHBOARD_PASSWORD`)

### Command-line Access

```bash
# Check health
curl -s http://localhost:8000/health | jq .

# Get current metrics
curl -s http://localhost:8000/metrics | jq .

# Get alerts
curl -s http://localhost:8000/alerts | jq .

# Get trades
curl -s http://localhost:8000/trades | jq .
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | System health check |
| `/metrics` | GET | Current metrics snapshot |
| `/alerts` | GET | Alert history (24h) |
| `/trades` | GET | Trade history (24h) |
| `/positions` | GET | Current positions |
| `/account` | GET | Account info |
| `/candles/{symbol}` | GET | Price charts |

---

## 5. Interpreting the Dashboard

### ✅ Normal State

```
- Balance stable (small fluctuations)
- P&L slightly positive or negative
- WebSocket: GREEN ✅
- REST API: GREEN ✅
- Latency p95 < 2s
- CRIT alerts: 0
- WARN alerts: 0-2
- Recent trades: Mostly fills
```

**Action:** Continue trading, monitor hourly.

### ⚠️ Caution State

```
- Balance declining (> 1% per hour)
- P&L negative
- WebSocket: Connected but slow
- REST API: Occasional errors
- Latency p95 > 2s
- CRIT alerts: 0 (just barely)
- WARN alerts: 3-5
- Trades: Some rejects
```

**Action:** Monitor closely, be ready to pause. Check for systematic issues.

### 🔴 Critical State

```
- WebSocket: DISCONNECTED or RED
- REST errors: 3+ in succession
- Latency p95 > 5s
- CRIT alert: DD > 2% (kill-switch triggered)
- All positions closed
- Mode: DRY_RUN
```

**Action:** Manual intervention required. See INCIDENT_RESPONSE.md

---

## 6. Daily Monitoring Checklist

### 06:00 UTC (Start of day)

- [ ] Dashboard loads without errors
- [ ] WebSocket connected (GREEN)
- [ ] REST API healthy (GREEN)
- [ ] No overnight alerts
- [ ] Balance correct ($300 + prior P&L)
- [ ] Positions empty (ready for trading)

### Every 1 hour (Hourly spot check)

- [ ] Review last 10 trades
- [ ] Check P&L trajectory
- [ ] Verify latency still good
- [ ] Scan alert history (no CRIT)
- [ ] Count current positions (should be ≤ 3)

### 12:00 UTC (Midday review)

- [ ] 6-hour P&L summary
- [ ] Any issues encountered?
- [ ] Metrics on track?
- [ ] Decision: Continue as-is / Pause / Adjust

### 18:00 UTC (End of day)

- [ ] Export daily metrics
- [ ] Generate HTML report
- [ ] Review all trades (win rate, P&L)
- [ ] Log any issues
- [ ] Decision: Resume tomorrow / Investigate issue

---

## 7. Performance Dashboard (Advanced)

### Win Rate Analysis

```
Win Rate: 60% (6 wins, 4 losses)

Trade Distribution:
- Winning trades avg: +$2.50
- Losing trades avg:  -$2.00
- Profit factor: 1.5 (good)
- Avg duration: 15 min
```

**Good signs:**
- Win rate > 50%
- Profit factor > 1.0
- Average win > average loss

### Risk Metrics

```
Max Single Loss: -$4.80 (1.6% of capital)
Max Single Win:  +$3.50 (1.2% of capital)
Recovery factor: 4.2× (good)

Daily DD curve:
↗ ↙ ↗ ↙ ↗ ↗ ↙   (should trend up, not down)
```

### Latency Distribution

```
REST Latency (ms):        WebSocket Latency (ms):
p50:  45 ms ✅            p50:  12 ms ✅
p95: 180 ms ✅            p95:  85 ms ✅
p99: 280 ms ✅            p99: 150 ms ✅
max: 512 ms ⚠️            max: 280 ms ✅

Trend: Stable ✅
```

---

## 8. Export & Reporting

### Export Metrics (Manual)

```bash
# Export as JSON
curl -s http://localhost:8000/metrics > metrics-$(date +%Y%m%d-%H%M%S).json

# Export trades as CSV
curl -s http://localhost:8000/trades?format=csv > trades-$(date +%Y%m%d).csv

# Generate HTML report
python -c "
from yunmin.reporting.report_generator import ReportGenerator
gen = ReportGenerator()
gen.generate_html_report('./reports/daily-snapshot.html')
"
```

### Scheduled Exports

```bash
# Daily at 06:00 UTC
0 6 * * * /usr/local/bin/export-daily-metrics.sh

# Weekly at 00:00 UTC (Sunday)
0 0 * * 0 /usr/local/bin/export-weekly-metrics.sh
```

---

## 9. Troubleshooting Dashboard

### Dashboard won't load

```bash
# Check if service running
ps aux | grep trading_engine

# Restart
pkill -f "trading_engine"
sleep 2
python -m yunmin.core.trading_engine --mode LIVE &
```

### Metrics are stale (not updating)

```bash
# Check WebSocket
curl -s http://localhost:8000/health | jq .ws_connected
# Should be: true

# Restart monitoring
systemctl restart yunmin-monitoring
```

### Alerts not showing

```bash
# Check alert log
tail -50 ./logs/alerts.log

# Verify Slack/Email configured
grep -E "SLACK_WEBHOOK|ALERT_EMAIL" .env
```

---

**Document Control**
- **Created:** 2025-01-26
- **Version:** 1.0
- **Status:** Ready for production
- **Owner:** Trading Team Lead

**Print this guide and keep near your monitor during live trading.**


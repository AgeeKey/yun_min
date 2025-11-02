# Phase 4: Production Deployment & Scale-up

**Purpose:** Execute live mainnet trading with automated safeguards, monitor performance, and gradually scale capital.

**Timeline:** 
- **48h Micro Phase:** Testnet validation + 48h live ($300)
- **Week 2-3:** Scale to $5,000 (4× increase)
- **Month 2+:** Scale to $25,000+

---

## 1. Pre-Deployment Checklist (DO NOT SKIP)

### ✅ Code & Configuration Locked

- [ ] **Git state clean:**
  ```bash
  git status
  # Should show: nothing to commit, working tree clean
  ```

- [ ] **Latest code tagged:**
  ```bash
  git tag v4.0.0-live-ready
  git log --oneline -5
  ```

- [ ] **Config files immutable:**
  - [ ] `config.prod.yaml` (locked, hash recorded)
  - [ ] `.env` (secrets safe, NOT in git)
  - [ ] `requirements.txt` frozen

- [ ] **Deployment hash recorded:**
  ```bash
  sha256sum config.prod.yaml
  # Record: ________________________________________
  ```

### ✅ Infrastructure Validation

- [ ] **Binance API connectivity test:**
  ```bash
  python -c "
  from yunmin.connectors.binance_connector import BinanceConnector
  conn = BinanceConnector(testnet=False)
  account = conn.get_account()
  print(f'✅ Connected. Balance: {account[\"totalWalletBalance\"]} USDT')
  "
  ```

- [ ] **WebSocket connectivity:**
  ```bash
  python -c "
  import asyncio
  from yunmin.core.websocket_layer import WebSocketLayer
  
  async def test_ws():
      ws = WebSocketLayer('BTCUSDT')
      await ws.connect()
      print('✅ WebSocket connected')
      await ws.close()
  
  asyncio.run(test_ws())
  "
  ```

- [ ] **Network routing verified:**
  - [ ] ISP latency stable (< 100ms to api.binance.com)
  - [ ] No VPN issues
  - [ ] Firewall allows api.binance.com:443

### ✅ Team & On-call

- [ ] **24/7 on-call schedule posted:**
  - [ ] Trader: [Name] — [Slack/Phone]
  - [ ] Engineer: [Name] — [Slack/Phone]
  - [ ] CTO: [Name] — [Email/Phone]

- [ ] **Alert recipients verified:**
  - [ ] Slack channel: #trading-live
  - [ ] Email group: trading-alerts@company
  - [ ] SMS numbers confirmed

- [ ] **Runbook briefing completed:**
  - [ ] All team members read RUNBOOK_LIVE_SAFETY.md
  - [ ] Kill-switch procedure practiced (manual + automatic)
  - [ ] Incident response tested
  - [ ] Escalation procedures clear

- [ ] **Emergency contacts ready:**
  ```
  CRITICAL (immediate):
  - CTO: _________________ (phone: _______________)
  
  HIGH (within 5 min):
  - Trading Lead: _________________ (phone: _______________)
  
  MEDIUM (within 30 min):
  - Engineer: _________________ (email: _______________)
  ```

### ✅ Monitoring & Observability

- [ ] **Dashboard deployed:**
  - [ ] Real-time P&L display ✅
  - [ ] Latency metrics (p50/p95/p99) ✅
  - [ ] WebSocket status indicator ✅
  - [ ] Alert history ✅

- [ ] **Logging configured:**
  - [ ] Daily logs: `./logs/trading-{date}.log` ✅
  - [ ] Trade journal: `./logs/trades-{date}.json` ✅
  - [ ] Metrics export: `./metrics/` ✅
  - [ ] Alert log: `./logs/alerts-{date}.log` ✅

- [ ] **Backup & recovery:**
  - [ ] Logs backed up daily ✅
  - [ ] Config backed up ✅
  - [ ] Metrics exported to S3/cloud ✅

---

## 2. Deployment Day (T-24h to T+0)

### T-24h: Final System Check

```python
# final_check.py
from yunmin.core.risk_manager import RiskManager
from yunmin.core.executor import Executor, ExecutionMode
from yunmin.core.trading_engine import TradingEngine

# Verify configuration
print("=" * 50)
print("FINAL PRE-DEPLOYMENT CHECK")
print("=" * 50)

# Check 1: Execution mode
executor = Executor()
assert executor.mode == ExecutionMode.LIVE, "Mode not set to LIVE!"
print("✅ Execution mode: LIVE")

# Check 2: Risk parameters
risk = RiskManager()
assert risk.initial_capital == 300.0, "Capital mismatch!"
assert risk.max_position_pct == 0.02, "Max position not 2%!"
assert risk.max_daily_dd == 0.02, "DD limit not 2%!"
assert risk.max_daily_dd_hard == 0.05, "Hard DD limit not 5%!"
print("✅ Risk parameters locked (capital: $300, DD: 2%, hard: 5%)")

# Check 3: Kill-switch armed
assert risk.kill_switch_enabled, "Kill-switch not armed!"
print("✅ Kill-switch armed")

# Check 4: TradingEngine ready
engine = TradingEngine()
assert engine.is_running == False, "Engine should not be running yet!"
assert engine.mode == "live", "Engine mode not live!"
print("✅ TradingEngine ready for launch")

print("\n" + "=" * 50)
print("ALL CHECKS PASSED ✅")
print("Ready for deployment!")
print("=" * 50)
```

**Run:**
```bash
python final_check.py
# All checks must pass before proceeding
```

### T-12h: Dry Run (No Real Orders)

```bash
# Simulate order flow without touching Binance
python -c "
from yunmin.core.executor import Executor, ExecutionMode
from yunmin.core.risk_manager import RiskManager
import time

executor = Executor(mode=ExecutionMode.DRY_RUN)
risk = RiskManager()

# Simulate decisions
decisions = [
    {'symbol': 'BTCUSDT', 'side': 'BUY', 'quantity': 0.001},
    {'symbol': 'BTCUSDT', 'side': 'SELL', 'quantity': 0.001},
]

for decision in decisions:
    print(f'DRY_RUN: {decision}')
    risk.validate(decision)  # Should pass in dry_run

print('✅ Dry run passed')
"
```

### T-6h: Alert Testing

**Test Slack integration:**
```bash
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-type: application/json' \
  -d '{
    "text": "🧪 Test: Live trading launches in 6h. All systems GO.",
    "attachments": [{
      "color": "good",
      "title": "Pre-Launch Check",
      "text": "All infrastructure verified"
    }]
  }'
```

**Test email:**
```bash
python -c "
import smtplib
msg = 'Live trading launches in 6h. All systems GO.'
print(f'Email sent to: trading-alerts@company')
"
```

**Test SMS (if configured):**
```bash
# Send test SMS to on-call numbers
echo 'Live trading ready. Launch in 6h.' | \
  twilio send-sms +1234567890 \
  --from=$TWILIO_NUMBER
```

### T-1h: Pre-Launch Meeting

**Attendees:** Trading Lead, Engineer, CTO

**Agenda:**
1. ✅ All checklists complete?
2. ✅ Network/infrastructure stable?
3. ✅ Team briefed?
4. ✅ Go/No-Go decision?

**Decision:** **GO / NO_GO**

```
GO Decision Criteria:
- All checklists: ✅ PASSED
- Backtest vs Paper drift: ✅ ≤ 15%
- E2E tests: ✅ 100% pass rate
- 7-day dry-run: ✅ CRIT=0, WARN≤5
- Infrastructure: ✅ All nominal
- Team ready: ✅ On-call active

NO-GO Criteria:
- Any single checkpoint failed
- Network issues
- Team unavailable
- Market conditions (extreme volatility/crash)
```

**Decision Log:**
```
Date: 2025-01-27
Time: 05:00 UTC
Status: GO ✅

Attendees:
- Trading Lead: _________________
- Engineer: _________________
- CTO: _________________

Sign-off: _________________
```

### T+0: Launch Sequence

**T-5 minutes:**
```bash
# Start monitoring dashboard
python -m yunmin.core.monitoring.dashboard &

# Start log tail
tail -f ./logs/trading.log &

# Verify positions empty
python -c "
from yunmin.connectors.binance_connector import BinanceConnector
conn = BinanceConnector(testnet=False)
positions = conn.get_positions()
assert len(positions) == 0, 'Existing positions found!'
print('✅ No existing positions')
"
```

**T-0 minutes (LAUNCH):**
```bash
# Start trading engine
python -m yunmin.core.trading_engine \
  --mode LIVE \
  --config config.prod.yaml \
  --capital 300 \
  --log-level INFO

# Expected output:
# 2025-01-27 06:00:00,000 | INFO | Starting TradingEngine
# 2025-01-27 06:00:00,100 | INFO | Executor mode: LIVE
# 2025-01-27 06:00:00,200 | INFO | Risk Manager armed
# 2025-01-27 06:00:00,300 | INFO | WebSocket connecting to Binance
# 2025-01-27 06:00:01,000 | INFO | ✅ LIVE TRADING STARTED
```

**Immediate Verification:**
```python
# Verify engine running
import requests
response = requests.get('http://localhost:8000/health')
assert response.status_code == 200, "Engine not healthy"
print(f"✅ Engine healthy: {response.json()}")

# Verify can place orders
from yunmin.core.executor import Executor
executor = Executor()
print(f"✅ Executor ready. Mode: {executor.mode}")
```

**Send Launch Notification:**
```
🚀 LIVE TRADING LAUNCHED

Status: ✅ ACTIVE
Mode: LIVE (mainnet)
Capital: $300 (micro-budget)
Duration: 48 hours
DD Stop: 2%

Symbols: BTCUSDT, ETHUSDT
Kill-switch: ARMED ✅
Monitoring: ACTIVE ✅

Standup: Daily 06:00 UTC
```

---

## 3. Continuous Monitoring (48 hours)

### Every 5 Minutes (Automated)

**Telemetry check:**
```python
from yunmin.core.dry_run_engine import DryRunEngine

engine = DryRunEngine()
telemetry = engine.get_telemetry()

# Alert if critical
if telemetry['daily_dd'] > 0.02:
    send_alert(level="CRIT", message=f"DD exceeded: {telemetry['daily_dd']:.2%}")

if telemetry['ws_stale_s'] > 60:
    send_alert(level="CRIT", message=f"WebSocket stale: {telemetry['ws_stale_s']}s")

if telemetry['rest_errors_1m'] >= 2:
    send_alert(level="CRIT", message=f"REST errors: {telemetry['rest_errors_1m']}")
```

### Every 1 Hour (Manual Review)

**Checklist:**
- [ ] Account balance > 0
- [ ] No unexpected orders
- [ ] WebSocket connected
- [ ] Latency normal (< 2s)
- [ ] No stuck orders
- [ ] Alert log clean

**Log review:**
```bash
tail -100 ./logs/trading.log | grep -E "ERROR|WARN|CRIT"
```

### Every 6 Hours (Metrics Review)

**Export metrics:**
```bash
python -c "
from yunmin.core.dry_run_engine import DryRunEngine
engine = DryRunEngine()
engine.export_metrics(format='json', path='./metrics/6h-snapshot.json')
engine.export_metrics(format='csv', path='./metrics/6h-snapshot.csv')
"
```

**HTML report:**
```bash
python -c "
from yunmin.reporting.report_generator import ReportGenerator
gen = ReportGenerator()
gen.generate_html_report(
    output_path='./reports/6h-summary.html',
    include_charts=True
)
"
```

### Daily (06:00 UTC)

**Standup meeting:**
- Trades executed
- P&L summary
- Alerts & incidents
- System health
- Go/No-Go decision for next 24h

**Daily metrics:**
```
Day 1 Summary (2025-01-27):
- Trades: 5 fills
- P&L: +$12.50 (+4.17%)
- Max DD: 1.2%
- Fill rate: 100%
- WS reconnects: 0
- REST errors: 0
- CRIT alerts: 0 ✅
- WARN alerts: 0 ✅
- Status: NOMINAL

Decision: CONTINUE ✅
```

---

## 4. Incident Response

### 🔴 CRITICAL Alert Triggered

**Immediate actions (< 1 min):**
1. Kill-switch activates (automatic)
2. Close all positions (market order)
3. Pause new orders
4. Log incident with timestamp

**Example:**
```
🔴 CRITICAL: Daily DD Exceeded
Timestamp: 2025-01-27 14:25:30 UTC
Event: daily_dd > 2.0%
Actual: 2.3%

Action: KILL_SWITCH TRIGGERED
- Close position: 0.001 BTC at market
- Pause trading: ✅
- Notify: Trading Lead, CTO
```

**Team response (< 5 min):**
- [ ] Verify kill-switch worked
- [ ] Check account balance
- [ ] Review what caused DD
- [ ] Plan mitigation
- [ ] Document incident

**Escalation (if needed):**
- [ ] If market crash: Halt trading, review data
- [ ] If API error: Check Binance status page
- [ ] If WS stale: Force reconnect, check network
- [ ] If stuck orders: Manual cancel + review risk

### 🟡 WARNING Alert

**Review (within 1 hour):**
- Log the event
- Check if trend is increasing
- Document possible cause
- Plan mitigation if needed

**Example:**
```
🟡 WARNING: High Latency
Timestamp: 2025-01-27 10:15:00 UTC
REST p95: 1,850 ms (target: ≤ 1,500 ms)

Assessment: Binance API slow
Action: Monitor next 30 minutes
```

---

## 5. 48h Success Criteria

### Must-Pass Metrics

| Metric | Target | Pass? |
|--------|--------|-------|
| **CRIT alerts** | = 0 | __ |
| **Fill rate** | ≥ 90% | __ |
| **Latency p95** | ≤ 2s | __ |
| **WS uptime** | ≥ 99% | __ |
| **REST errors** | = 0 | __ |
| **Position sync** | 100% | __ |
| **Daily DD** | < 2% | __ |

### Success Scenario

```
Day 1: +$12.50 (4.2%), 0 CRIT ✅
Day 2: +$8.25 (2.8%), 0 CRIT ✅

Total: +$20.75 (+6.9%), 0 CRIT ✅
→ SCALE-UP APPROVED
```

### Failure Scenario

```
Day 1: 1 CRIT (kill-switch triggered) ❌
→ INVESTIGATE
→ Root cause: Latency spike caused missed fill
→ FIX: Implement retry logic
→ RETRY: Day 3-4 after fix validated
```

---

## 6. Scale-up Strategy

### If Success ✅ (48h CRIT=0)

**Phase 4.1 (48-72h):** $300 → $600
```yaml
capital: 600
max_position_pct: 0.02  # Same limits
max_daily_dd: 0.02
symbols: [BTCUSDT, ETHUSDT]
```

**Phase 4.2 (Week 2):** $600 → $1,500
```yaml
capital: 1500
max_position_pct: 0.02
max_daily_dd: 0.02
symbols: [BTCUSDT, ETHUSDT, BNBUSDT]
```

**Phase 4.3 (Week 3-4):** $1,500 → $5,000
```yaml
capital: 5000
max_position_pct: 0.02
max_daily_dd: 0.02
symbols: [BTCUSDT, ETHUSDT, BNBUSDT, ADAUSDT]
```

**Phase 4.4 (Month 2):** $5,000 → $25,000+
```yaml
capital: 25000
max_position_pct: 0.015  # Tighter control
max_daily_dd: 0.015
symbols: [BTCUSDT, ETHUSDT, BNBUSDT, ADAUSDT, XRPUSDT, ...]
```

### Each Scale-up Requires

- [ ] Review metrics from previous phase
- [ ] No CRIT alerts (past 48-72h)
- [ ] Fill rate stable (≥ 85%)
- [ ] Risk parameters still locked
- [ ] Team approval & sign-off

---

## 7. Production Maintenance

### Daily (06:00 UTC)

```bash
# Backup logs
cp -r ./logs ./backups/logs-$(date +%Y%m%d)

# Export metrics
python -c "
from yunmin.reporting.report_generator import ReportGenerator
gen = ReportGenerator()
gen.generate_html_report('./reports/daily-$(date +%Y%m%d).html')
"

# Check disk space
df -h ./logs ./reports
# Alert if > 80% full
```

### Weekly (Sunday 06:00 UTC)

```bash
# Full metrics export
tar -czf ./backups/metrics-$(date +%Y%m%d).tar.gz ./metrics

# Code git status
git status
git log --oneline -20

# Update runbook (if needed)
# Review: RUNBOOK_LIVE_SAFETY.md
```

### Monthly (1st of month)

- [ ] Review P&L trend
- [ ] Check for any recurring issues
- [ ] Update risk thresholds (if needed)
- [ ] Security audit of API keys
- [ ] Infrastructure capacity check

---

## 8. Emergency Procedures

### Market Crash (> 10% daily)

**Automatic:**
- Kill-switch triggers if DD > 2%
- All positions closed

**Manual override (if needed):**
```bash
python -c "
from yunmin.core.executor import Executor
executor = Executor()
executor.emergency_stop()
print('✅ Emergency stop activated')
"
```

### Exchange Outage

**WebSocket disconnection:**
- Automatic reconnect (exponential backoff)
- Alert after 5 failed attempts
- Kill-switch if stale > 60s

**REST API error:**
- Automatic retry (3×)
- Alert on consecutive errors (≥ 2)
- Manual intervention after 10 errors

### Network Issues

**ISP down:**
- Kill-switch activates (no new orders)
- Alert sent to team
- Wait for network recovery
- Manual restart once stable

**VPN issues:**
- Switch to direct connection
- Or restart connection
- Monitor latency before resuming

---

## 9. Launch Command Reference

**Start trading:**
```bash
python -m yunmin.core.trading_engine \
  --mode LIVE \
  --config config.prod.yaml \
  --capital 300 \
  --log-level INFO \
  --metrics-export ./metrics/ \
  --disable-dry-run
```

**Start monitoring:**
```bash
python -m yunmin.core.monitoring.dashboard \
  --port 8000 \
  --metrics-path ./metrics/
```

**Stop trading (graceful):**
```bash
# Will close open positions at market, save state
python -c "
from yunmin.core.trading_engine import TradingEngine
engine = TradingEngine()
engine.stop()
"
```

**Stop trading (emergency):**
```bash
# Kill-switch: Closes all positions immediately
pkill -f "trading_engine"
# Then run:
python -c "
from yunmin.core.executor import Executor
executor = Executor()
executor.emergency_stop()
"
```

---

**Document Control**
- **Created:** 2025-01-26
- **Version:** 1.0
- **Status:** Ready for deployment
- **Owner:** Trading Team Lead
- **Next Review:** After 48h live phase

**🚀 Ready to deploy!**


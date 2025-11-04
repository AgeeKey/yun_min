# YunMin V3: 48-Hour Testnet Validation Plan

**Version:** 1.0  
**Date:** 2025-11-04  
**Status:** Ready for Execution

---

## 🎯 Objectives

Validate YunMin V3 strategy performance on Binance Testnet with real market data before mainnet deployment.

**Success Criteria:**
1. System stability (no crashes for 48h)
2. Win Rate ≥ 50%
3. Positive net P&L
4. Max Drawdown < 10%
5. Risk manager functioning correctly
6. No emergency shutdowns

---

## 📅 Timeline

### Pre-Launch (T-1h)
- [ ] Complete testnet setup (API keys, funds)
- [ ] Run `check_testnet_ready.py` - all checks PASS
- [ ] Run dry-run for 10 minutes
- [ ] Verify logs are being saved correctly

### Launch (T=0)
```bash
python run_testnet.py --duration 48 --symbol BTCUSDT --capital 10000
```

### Monitoring Schedule

| Time | Action | Checklist |
|------|--------|-----------|
| T+1h | Initial Check | ✅ Bot running<br>✅ Trades being placed<br>✅ Risk manager approving/rejecting |
| T+6h | Review #1 | ✅ Log file readable<br>✅ Stats update correctly<br>✅ No errors in logs |
| T+12h | Mid-Day 1 Review | 📊 Calculate interim metrics<br>📈 Check win rate trend<br>💰 Review P&L |
| T+24h | Day 1 Complete | 📄 Generate Day 1 report<br>🔍 Analyze trade distribution<br>⚖️ LONG vs SHORT balance |
| T+36h | Mid-Day 2 Review | 📊 Compare Day 1 vs Day 2<br>🔁 Check for degradation<br>⚠️ Monitor drawdown |
| T+48h | Final Review | 🛑 Graceful shutdown<br>📊 Full analysis<br>✅ Go/No-Go decision |

---

## 📊 Metrics to Monitor

### Real-Time (Every Check)
- **Runtime:** Hours since start
- **Total Trades:** Count
- **Win Rate:** % winning trades
- **P&L:** Net profit/loss in USD and %
- **Current Capital:** Real-time balance
- **Max Drawdown:** Peak-to-trough decline
- **Consecutive Losses:** Streak counter

### Aggregated (12h/24h Reviews)
- **Hourly Trade Rate:** Trades per hour
- **Average Win:** Mean profit per winning trade
- **Average Loss:** Mean loss per losing trade
- **Profit Factor:** Gross profit / Gross loss
- **Sharpe Ratio:** Risk-adjusted return
- **LONG Performance:** Win rate, P&L
- **SHORT Performance:** Win rate, P&L
- **Risk Manager Stats:** Approved vs Rejected orders

---

## 🚨 Emergency Stop Conditions

Bot will auto-shutdown if:

1. **Max Drawdown > 10%**
   - Trigger: Capital drops 10% from peak
   - Action: Cancel all orders, log emergency, exit

2. **5 Consecutive Losses**
   - Trigger: 5 trades in a row lose money
   - Action: Cancel all orders, log warning, exit

3. **System Errors**
   - Trigger: API errors, connectivity loss
   - Action: Retry 3 times, then graceful shutdown

4. **Manual Override**
   - Trigger: User sends SIGINT (Ctrl+C) or SIGTERM
   - Action: Cancel all orders, save logs, exit

---

## 📈 Success Criteria Detail

### ✅ Tier 1: PASS (Ready for Mainnet)
- [ ] Win Rate ≥ 60%
- [ ] Total Return ≥ +5%
- [ ] Profit Factor ≥ 2.0
- [ ] Max Drawdown ≤ 5%
- [ ] No emergency stops
- [ ] LONG WR ≥ 50%
- [ ] SHORT WR ≥ 50%

### ⚠️ Tier 2: CONDITIONAL PASS (Needs Optimization)
- [ ] Win Rate ≥ 50%
- [ ] Total Return ≥ 0% (breakeven)
- [ ] Profit Factor ≥ 1.5
- [ ] Max Drawdown ≤ 10%
- [ ] ≤ 1 emergency stop
- [ ] Either LONG or SHORT performing well

### ❌ Tier 3: FAIL (Back to Drawing Board)
- Win Rate < 50%
- OR Total Return < 0%
- OR Profit Factor < 1.0
- OR Max Drawdown > 10%
- OR Multiple emergency stops
- OR Both LONG and SHORT underperforming

---

## 📝 Data Collection

### Automatic Logs
- **Trade Log:** `testnet_trades_YYYYMMDD_HHMMSS.json`
  - Every trade: timestamp, symbol, side, price, quantity, P&L
  - Session metadata: start/end time, initial/final capital
  - Aggregated stats

- **Console Log:** stdout/stderr
  - Real-time bot status
  - Risk manager decisions
  - API call logs
  - Error messages

### Manual Recordings (Optional)
- Screenshots of Binance testnet account balance
- Market conditions during test (trending/ranging/volatile)
- Notable events (large moves, connection issues)

---

## 🔍 Post-Run Analysis

### Step 1: Load Trade Data
```python
import json

with open('testnet_trades_20251104_120000.json') as f:
    data = json.load(f)

trades = data['trades']
stats = data['stats']
```

### Step 2: Calculate Metrics
```python
# Win Rate
win_rate = stats['win_rate']

# P&L
total_pnl = stats['total_pnl']
return_pct = stats['return_pct']

# Drawdown
max_dd = stats['max_drawdown']

# LONG vs SHORT
long_trades = [t for t in trades if t['side'] == 'BUY']
short_trades = [t for t in trades if t['side'] == 'SELL']

long_wr = sum(1 for t in long_trades if t['pnl'] > 0) / len(long_trades) * 100
short_wr = sum(1 for t in short_trades if t['pnl'] > 0) / len(short_trades) * 100
```

### Step 3: Generate Report
Create markdown report with:
- Summary stats
- V3 Backtest vs Testnet comparison
- LONG/SHORT analysis
- Risk manager effectiveness
- Recommendations

Template: `TESTNET_48H_REPORT_TEMPLATE.md`

---

## ✅ Go/No-Go Decision Matrix

| Metric | Target | Weight | Pass Threshold |
|--------|--------|--------|----------------|
| Win Rate | ≥60% | High | ≥50% |
| Total Return | ≥+5% | High | ≥0% |
| Max Drawdown | ≤5% | Critical | ≤10% |
| Profit Factor | ≥2.0 | Medium | ≥1.0 |
| Emergency Stops | 0 | Critical | ≤1 |
| LONG WR | ≥50% | Medium | ≥40% |
| SHORT WR | ≥50% | Medium | ≥40% |

**Weighted Score Formula:**
```
Score = (0.25 × WR_pass) + (0.25 × Return_pass) + 
        (0.20 × DD_pass) + (0.15 × PF_pass) + 
        (0.10 × EmergencyStop_pass) + (0.05 × LONG_pass + SHORT_pass)
```

- **Score ≥ 0.85:** ✅ GO for Mainnet
- **Score 0.60-0.84:** ⚠️ CONDITIONAL - Optimize first
- **Score < 0.60:** ❌ NO GO - Major rework needed

---

## 🛠 Troubleshooting Guide

### Issue: Bot Stops After Few Minutes
**Symptoms:** Early exit, minimal trades
**Causes:**
- Emergency stop triggered (check logs)
- API authentication failure
- Insufficient testnet funds

**Fix:**
1. Check `testnet_trades_*.json` for error messages
2. Verify API keys are correct
3. Request more testnet USDT
4. Lower `--capital` parameter

### Issue: No Trades Generated
**Symptoms:** Bot runs but 0 trades
**Causes:**
- Strategy not generating signals
- Risk manager rejecting all orders
- Market too stable (no crossovers)

**Fix:**
1. Check strategy logs for signal generation
2. Review risk manager rejection reasons
3. Wait for more volatile market conditions
4. Consider lowering RSI thresholds temporarily

### Issue: High Loss Rate
**Symptoms:** Win rate < 30%, negative P&L
**Causes:**
- Market conditions unfavorable (strong trend against signals)
- Stop losses too tight
- Take profits too far

**Fix:**
1. Analyze market trend during test period
2. Review backtest assumptions vs reality
3. Consider V4 optimizations (asymmetric SL/TP)
4. Test on different market conditions

### Issue: Connection Errors
**Symptoms:** API timeouts, WebSocket drops
**Causes:**
- Binance testnet downtime
- Network issues
- Rate limiting

**Fix:**
1. Check Binance testnet status page
2. Increase request timeout in connector
3. Add retry logic with exponential backoff
4. Use VPN if geographic restrictions

---

## 📋 Review Checklist (Post-48h)

### Technical Review
- [ ] All trades logged correctly
- [ ] No data corruption in JSON
- [ ] Risk manager approved/rejected as expected
- [ ] No unhandled exceptions in logs
- [ ] Graceful shutdown executed
- [ ] Balance reconciliation: expected vs actual

### Performance Review
- [ ] Win rate calculated
- [ ] P&L matches testnet account
- [ ] Drawdown peak identified
- [ ] Trade distribution analyzed (hourly, daily)
- [ ] LONG vs SHORT balance acceptable
- [ ] Comparison with V3 backtest documented

### Risk Review
- [ ] No emergency stops triggered (or justified if triggered)
- [ ] Max position sizes respected
- [ ] No excessive losses on single trades
- [ ] Drawdown stayed within limits
- [ ] Risk manager logs reviewed for patterns

### Business Review
- [ ] Strategy viability confirmed or questioned
- [ ] Optimization opportunities identified
- [ ] Mainnet deployment plan updated
- [ ] Budget estimate for real capital
- [ ] Timeline for next phase approved

---

## 🚀 Next Actions (Based on Results)

### If Tier 1 PASS:
1. **Prepare Mainnet Deployment**
   - Get real Binance API keys (mainnet)
   - Start with small capital ($100-500)
   - Run for 1 week before scaling up
   - Monitor daily with same rigor

2. **Documentation**
   - Archive testnet results
   - Create mainnet runbook
   - Update risk limits for real money

### If Tier 2 CONDITIONAL:
1. **Implement V4 Optimizations**
   - Add asymmetric SL/TP
   - Test trend filters on testnet data
   - Run another 48h testnet cycle

2. **Fine-Tune Parameters**
   - Adjust RSI thresholds
   - Modify EMA periods
   - Backtest with new params first

### If Tier 3 FAIL:
1. **Root Cause Analysis**
   - Deep dive into losing trades
   - Identify systematic issues
   - Challenge strategy assumptions

2. **Strategy Redesign**
   - Consider simpler approaches
   - Test alternative indicators
   - Validate on historical data before testnet

---

## 📞 Support & Escalation

**During 48h Test:**
- Monitor logs in real-time
- Set alerts for emergency stops
- Have team available for quick fixes

**Critical Issues:**
- API authentication failures → Regenerate keys immediately
- Consistent losses → Consider early termination
- System crashes → Investigate logs, fix, restart

**Post-Test:**
- Schedule review meeting within 24h
- Document lessons learned
- Update this plan for future tests

---

**Ready to Launch! 🚀**

Last updated: 2025-11-04  
Next review: After 48h testnet run

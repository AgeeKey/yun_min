# Phase 3 Execution Checklist

**Purpose:** Pre-launch verification checklist before transitioning to live mainnet trading.

**Checkpoint:** All items must be completed and signed off before proceeding to next phase.

---

## Phase 3.0: Testnet 24h Validation

### Testnet Execution

- [ ] **Testnet 24h test scheduled** (at least 24 continuous hours)
- [ ] **Config locked** (config.prod.yaml frozen, hash recorded)
- [ ] **Seed set** for reproducible backtester validation (recorded in TESTNET_24H_REPORT.schema.json)
- [ ] **Initial capital** set to $100-300 (micro-budget matching live)
- [ ] **Risk parameters locked:**
  - [ ] Max position size: 2%
  - [ ] Daily DD limit: 2%
  - [ ] Max daily trades: 20
  - [ ] Max open orders: 3
- [ ] **Kill-switch enabled** (auto-trigger on DD > 2%)
- [ ] **Monitoring dashboard active** (real-time P&L, latency, alerts)
- [ ] **Alert routing configured** (Slack, Email, SMS)

### Testnet Success Criteria

- [ ] **No CRITICAL alerts** during 24h
- [ ] **Fill rate ≥ 90%** (market orders filling consistently)
- [ ] **WS uptime ≥ 99%** (max 1 reconnect)
- [ ] **REST error rate = 0%** (no API failures)
- [ ] **Latency p95 ≤ 2s** (both WS and REST)
- [ ] **Position sync 100%** (no data mismatches vs Binance)
- [ ] **No stuck orders** (all orders resolve within 5 min)
- [ ] **Daily DD < 2%** (risk controls working)

### Testnet Artifacts Collected

- [ ] **Trading logs** saved to `./logs/testnet-24h-{date}/`
- [ ] **HTML report** generated (summary + metrics cards)
- [ ] **Metrics exported:**
  - [ ] JSON metrics file
  - [ ] CSV trade-by-trade file
- [ ] **TESTNET_24H_REPORT.schema.json** filled with all metrics
- [ ] **Report signed off** by reviewing engineer
- [ ] **Git commit** created: `feat: testnet-24h-pass-{date}`
- [ ] **Git tag** created: `v3.0.0-testnet-validated`

**Testnet Sign-off:**
- [ ] **Reviewer:** ___________________
- [ ] **Review Date:** ___________________
- [ ] **Status:** ✅ PASSED / ❌ FAILED

---

## Phase 3.1: Paper/Dry-run 7-day Validation

### Paper Mode Setup

- [ ] **Paper mode enabled** (simulated orders, no real capital at risk)
- [ ] **Strategy deployed** (identical to testnet config)
- [ ] **Initial balance set** to $1,000 (equivalent for 1-week simulation)
- [ ] **Risk parameters identical to live:**
  - [ ] Max position size: 2%
  - [ ] Daily DD limit: 2%
  - [ ] Max daily trades: 20
- [ ] **Dry-run engine active** (telemetry collection)
- [ ] **Alert system active** (WARN/CRIT routing)

### Paper Mode Execution (7 days)

| Day | Date | Status | Summary | Sign-off |
|-----|------|--------|---------|----------|
| 1 | _____ | [ ] | Trades: ___ | _______ |
| 2 | _____ | [ ] | Trades: ___ | _______ |
| 3 | _____ | [ ] | Trades: ___ | _______ |
| 4 | _____ | [ ] | Trades: ___ | _______ |
| 5 | _____ | [ ] | Trades: ___ | _______ |
| 6 | _____ | [ ] | Trades: ___ | _______ |
| 7 | _____ | [ ] | Trades: ___ | _______ |

### Paper Mode Success Criteria

- [ ] **CRITICAL alerts = 0** (no kill-switch triggers)
- [ ] **WARN alerts ≤ 5 total** (system stable, minor issues only)
- [ ] **Fill rate ≥ 85%** (consistent market execution)
- [ ] **Daily average P&L consistent** (positive or stable)
- [ ] **Max daily DD < 1.5%** (well below limit)
- [ ] **WS reconnects ≤ 3/day** (stable connection)
- [ ] **REST errors = 0** (API connectivity solid)
- [ ] **Position sync 100%** (no accounting drift)
- [ ] **Latency p95 ≤ 2s** (acceptable for live)
- [ ] **No anomalies** in strategy logic (decisions sane, no infinite loops)

### Paper Mode Metrics Summary

```
7-Day Summary:
- Total trades: _____
- Winning trades: _____ (___%)
- P&L: $_____ (+___%)
- Max DD: ____%
- Sharpe ratio: _____
- Avg latency: _____ ms
- Fill rate: ____%
- WS reconnects: _____ (avg: __/day)
- CRIT alerts: _____ (0 required ✅)
- WARN alerts: _____ (≤5 required ✅)
```

### Paper Mode Artifacts

- [ ] **7-day logs** archived to `./logs/paper-7d-{date}/`
- [ ] **Final report** generated (HTML + CSV)
- [ ] **Metrics export** saved
- [ ] **Incident log** reviewed (all WARN/CRIT documented)
- [ ] **Decision log** exported (all strategy decisions recorded)

**Paper Mode Sign-off:**
- [ ] **Reviewer:** ___________________
- [ ] **Review Date:** ___________________
- [ ] **Status:** ✅ PASSED / ❌ FAILED

---

## Phase 3.2: Risk & Kill-switch Verification

### Risk Manager Manual Tests

- [ ] **Position size limit test:**
  - [ ] Attempt position > 2% of capital
  - [ ] Verify rejection
  - [ ] Log result: _______________

- [ ] **Daily DD limit test:**
  - [ ] Simulate loss approaching 2%
  - [ ] Verify kill-switch trigger
  - [ ] Log result: _______________

- [ ] **Max open orders test:**
  - [ ] Attempt 4+ concurrent orders
  - [ ] Verify only 3 accepted
  - [ ] Log result: _______________

- [ ] **Daily trade limit test:**
  - [ ] Execute 20 trades
  - [ ] Verify trade 21 rejected
  - [ ] Log result: _______________

### Kill-switch Functionality Tests

- [ ] **Manual kill-switch:**
  - [ ] Trigger via command: `executor.kill_switch()`
  - [ ] Verify all positions close
  - [ ] Verify mode → DRY_RUN
  - [ ] Log result: _______________

- [ ] **Automatic kill-switch (DD):**
  - [ ] Simulate daily DD > 2%
  - [ ] Verify auto-trigger
  - [ ] Verify positions closed
  - [ ] Log result: _______________

- [ ] **Automatic kill-switch (WS stale):**
  - [ ] Simulate WS > 60s no updates
  - [ ] Verify reconnect attempt
  - [ ] Verify kill-switch if reconnect fails
  - [ ] Log result: _______________

### Risk Tests Sign-off

- [ ] **Tester:** ___________________
- [ ] **Test Date:** ___________________
- [ ] **All tests passed:** ✅ / ❌

---

## Phase 3.3: Backtest vs Paper Drift Check

### Strategy Performance Comparison

| Metric | Backtest | Paper (7d) | Drift | Accept? |
|--------|----------|-----------|-------|---------|
| **Win rate** | ____% | ____% | ±____% | ✅/❌ |
| **Profit factor** | ____ | ____ | ±____ | ✅/❌ |
| **Sharpe ratio** | ____ | ____ | ±____ | ✅/❌ |
| **Max DD** | ____% | ____% | ±____% | ✅/❌ |
| **Avg trade P&L** | $____ | $____ | ±$____ | ✅/❌ |

**Drift Tolerance:** ≤ 15% (expected due to live market conditions vs simulation)

### Root Cause Analysis (if drift > 15%)

- [ ] **Liquidity difference:**
  - [ ] Check paper fill rates vs backtest
  - [ ] Assess slippage model vs reality
  - [ ] Recommendation: _________________

- [ ] **Latency impact:**
  - [ ] Check order execution latency in paper
  - [ ] Assess if fills delayed vs expected
  - [ ] Recommendation: _________________

- [ ] **Strategy logic drift:**
  - [ ] Review decision logs (backtest vs paper)
  - [ ] Check for logic errors or edge cases
  - [ ] Recommendation: _________________

### Drift Assessment Sign-off

- [ ] **All metrics within 15% tolerance:** ✅ / ❌
- [ ] **Root causes (if any) identified:** ✅ / ❌
- [ ] **Corrective actions (if needed) completed:** ✅ / ❌
- [ ] **Reviewer:** ___________________
- [ ] **Date:** ___________________
- [ ] **Status:** ✅ PASSED / ❌ FAILED (with mitigation)

---

## Phase 3.4: Decision Document Review

### GO_NO_GO_DECISION.md Completion

- [ ] **Section 1 - Scope:**
  - [ ] Trading pairs confirmed: _______________
  - [ ] Mode confirmed: LIVE
  - [ ] Versions locked: _______________

- [ ] **Section 2 - KPI Validation:**
  - [ ] E2E tests pass rate: ____% (target: 100%) ✅/❌
  - [ ] Market fill rate: ____% (target: ≥90%) ✅/❌
  - [ ] CRITICAL alerts: ____ (target: 0) ✅/❌
  - [ ] Latency p95: ____ ms (target: ≤2s) ✅/❌
  - [ ] WS uptime: ____% (target: ≥99%) ✅/❌

- [ ] **Section 3 - Risk Review:**
  - [ ] RiskManager enforcement validated: ✅ / ❌
  - [ ] Kill-switch tested: ✅ / ❌
  - [ ] Order execution verified: ✅ / ❌
  - [ ] Position accuracy checked: ✅ / ❌

- [ ] **Section 4 - Infrastructure:**
  - [ ] API connectivity confirmed: ✅ / ❌
  - [ ] Monitoring dashboard live: ✅ / ❌
  - [ ] Alert routing verified: ✅ / ❌
  - [ ] Runbook reviewed by team: ✅ / ❌

- [ ] **Section 5 - Sign-off Checklist:**
  - [ ] All KPIs met (or accepted risks documented): ✅ / ❌
  - [ ] All manual tests passed: ✅ / ❌
  - [ ] Risk assessment complete: ✅ / ❌
  - [ ] Team briefed: ✅ / ❌

- [ ] **Section 6 - Approvals:**
  - [ ] Trading Lead signature: ___________________
  - [ ] Risk Officer signature: ___________________
  - [ ] CTO signature: ___________________

- [ ] **Section 7 - Archive:**
  - [ ] Git commit created: `feat: go-no-go-approval-{date}`
  - [ ] Git tag created: `v3.0.0-approved-for-live`

### Decision Document Sign-off

- [ ] **GO/NO-GO Decision:** GO ✅ / NO_GO ❌
- [ ] **Final approval by CTO:** ___________________
- [ ] **Approval date:** ___________________

---

## Phase 3.5: Live Launch Readiness

### Pre-Launch Infrastructure (T-24h)

- [ ] **LIVE_LAUNCH_PLAN.md reviewed:**
  - [ ] 48h timeline understood: ✅ / ❌
  - [ ] Capital allocation confirmed ($300): ✅ / ❌
  - [ ] Risk controls locked: ✅ / ❌

- [ ] **Binance API & Mainnet:**
  - [ ] API keys created (mainnet, no withdrawal): ✅ / ❌
  - [ ] Test connection successful: ✅ / ❌
  - [ ] Initial capital ($300) transferred: ✅ / ❌

- [ ] **Operations Team:**
  - [ ] On-call schedule posted: ✅ / ❌
  - [ ] Alert recipients confirmed: ✅ / ❌
  - [ ] Runbook LIVE_SAFETY walkthrough done: ✅ / ❌
  - [ ] Kill-switch procedure practiced: ✅ / ❌

- [ ] **Monitoring & Observability:**
  - [ ] Dashboard deployed and tested: ✅ / ❌
  - [ ] Log aggregation live: ✅ / ❌
  - [ ] Metrics export configured: ✅ / ❌
  - [ ] Alert routing confirmed: ✅ / ❌

- [ ] **Code & Configuration:**
  - [ ] Latest code on main branch: ✅ / ❌
  - [ ] Config locked (config.prod.yaml): ✅ / ❌
  - [ ] Secrets in .env (not in git): ✅ / ❌
  - [ ] Docker image built (if used): ✅ / ❌

### Launch Day (T+0)

- [ ] **Final System Check (5 min before launch):**
  ```python
  # Run final sanity checks
  executor_mode = "LIVE"  ✅
  risk_manager.max_position = 0.02  ✅
  risk_manager.daily_dd = 0.02  ✅
  initial_balance = 300.0  ✅
  kill_switch_enabled = True  ✅
  ```

- [ ] **Launch Command Executed:**
  ```bash
  # At agreed time
  $ python -m yunmin.core.trading_engine --mode LIVE --config config.prod.yaml
  ```

- [ ] **Launch Confirmation:**
  - [ ] TradingEngine started: ✅ / ❌
  - [ ] Orders can be placed: ✅ / ❌
  - [ ] Telemetry flowing: ✅ / ❌
  - [ ] Launch notification sent: ✅ / ❌

### 48h Live Trading

**Day 1 (Standup 06:00 UTC):**
- [ ] Trades: ____ fills
- [ ] P&L: $____ (+____%)
- [ ] Max DD: ____%
- [ ] Alerts: 0 CRIT ✅, ____ WARN
- [ ] Status: ✅ NOMINAL
- [ ] Decision: CONTINUE / PAUSE / ABORT
- [ ] Sign-off: ___________________

**Day 2 (Standup 06:00 UTC):**
- [ ] Trades: ____ fills
- [ ] P&L: $____ (+____%)
- [ ] Max DD: ____%
- [ ] Alerts: 0 CRIT ✅, ____ WARN
- [ ] Status: ✅ NOMINAL
- [ ] Decision: CONTINUE / SCALE / ABORT
- [ ] Sign-off: ___________________

### 48h Success Assessment

- [ ] **CRITICAL Alerts:** 0 ✅
- [ ] **Fill Rate:** ≥ 90% ✅
- [ ] **Latency stable:** ✅
- [ ] **No stuck orders:** ✅
- [ ] **Position tracking accurate:** ✅
- [ ] **No data loss:** ✅

**Result:** ✅ SUCCESS → Proceed to scale-up

---

## Phase 3.6: Scale-up Decision & Next Phases

### If 48h Success ✅

- [ ] **Scale to $600 (2×):**
  - [ ] Capital transferred: ✅
  - [ ] Config updated: ✅
  - [ ] New risk params locked: ✅
  - [ ] Restart trading engine: ✅

- [ ] **Timeline:**
  - [ ] Phase 3.1 (48-72h): $300 → $600
  - [ ] Phase 3.2 (1 week): $600 → $1,500
  - [ ] Phase 3.3 (2 weeks): $1,500 → $5,000
  - [ ] Phase 4 (Production): $5,000+ → Full scale

### If 48h Failure ❌

- [ ] **Incident Response:**
  - [ ] Kill-switch activated: ✅ / ❌
  - [ ] Positions closed: ✅ / ❌
  - [ ] Root cause analysis: _______________
  - [ ] Code/config fixes: _______________

- [ ] **Retry Plan:**
  - [ ] Fixes tested in paper: ✅ / ❌
  - [ ] Retry launch date: _______________
  - [ ] Approval required before retry: ✅ / ❌

---

## Final Approval

**Phase 3 Complete - Ready for Live Trading ✅**

- [ ] **CTO Sign-off:** ___________________ (Date: _______)
- [ ] **Risk Officer Sign-off:** ___________________ (Date: _______)
- [ ] **Operations Lead Sign-off:** ___________________ (Date: _______)

**Git Tags & Artifacts:**
- [ ] `v3.0.0-phase3-complete` (all tests passed)
- [ ] `v3.0.0-live-launch-ready` (approved for production)
- [ ] Artifacts archived: `./artifacts/phase3-{date}/`

---

**Document Control**
- **Created:** 2025-01-26
- **Version:** 1.0
- **Status:** Ready for Phase 3 execution
- **Owner:** Trading Team Lead

**Next Document:** LIVE_LAUNCH_PLAN.md (48h execution strategy)


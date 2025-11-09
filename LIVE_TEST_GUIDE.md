# Live Test Guide - Extended Testnet Validation

## Overview

This guide explains how to run extended live tests (100+ iterations) on Binance testnet to validate the Yun Min trading strategy under real market conditions.

## What is Live Testing?

Live testing runs the trading bot continuously for hours or days, analyzing real market data and generating signals. It operates in **dry-run mode** (no real trades), tracking performance metrics to validate strategy effectiveness before risking real capital.

## Prerequisites

### 1. Python Environment
```bash
python --version  # Python 3.8+
pip install -r requirements.txt
```

### 2. API Keys

#### Binance Testnet (Optional)
While dry-run mode doesn't execute real trades, connecting to Binance testnet provides real market data:

1. Visit [Binance Testnet](https://testnet.binance.vision/)
2. Create API keys
3. Add to `.env`:
```
BINANCE_API_KEY=your_testnet_api_key
BINANCE_SECRET_KEY=your_testnet_secret_key
```

#### OpenAI API (Required for LLM Strategy)
For AI-powered trading signals:

1. Get API key from [OpenAI Platform](https://platform.openai.com/)
2. Add to `.env`:
```
OPENAI_API_KEY=your_openai_api_key
```

**Alternative**: Use Groq (free):
```
YUNMIN_LLM_PROVIDER=grok
GROK_API_KEY=your_grok_api_key
```

### 3. Verify Setup
```bash
# Quick test (3 iterations)
python examples/basic_bot.py
```

## Quick Start

### Single Session Test
```bash
# Run 100 iterations with 5-minute intervals (~8.3 hours)
python run_live_test.py --session 1 --iterations 100 --interval 300
```

### All Three Sessions
```bash
# Linux/Mac
./run_all_sessions.sh

# Windows
.\run_all_sessions.ps1
```

## Test Scenarios

### Scenario 1: Normal Market Conditions
**Purpose**: Establish baseline performance

```bash
python run_live_test.py \
    --session 1 \
    --iterations 100 \
    --interval 300 \
    --condition normal
```

- **When to run**: Regular US/EU trading hours (9 AM - 5 PM)
- **Duration**: ~8.3 hours
- **Focus**: Balanced market conditions
- **Expected**: Win rate 50-60%, moderate trading activity

### Scenario 2: Volatile Market
**Purpose**: Stress test under pressure

```bash
python run_live_test.py \
    --session 2 \
    --iterations 50 \
    --interval 120 \
    --condition volatile
```

- **When to run**: High volatility periods (market opens, news events)
- **Duration**: ~1.7 hours
- **Focus**: Rapid price movements
- **Expected**: Lower win rate (45-55%), higher trading frequency

### Scenario 3: Overnight/Low Liquidity
**Purpose**: Validate stability in quiet markets

```bash
python run_live_test.py \
    --session 3 \
    --iterations 50 \
    --interval 600 \
    --condition overnight
```

- **When to run**: Low liquidity hours (10 PM - 6 AM)
- **Duration**: ~8.3 hours
- **Focus**: Reduced volatility
- **Expected**: Higher win rate (55-65%), fewer false signals

## Command Line Options

```
--session      Session ID (1, 2, 3, etc.)
--iterations   Number of iterations to run
--interval     Seconds between iterations
--condition    Market condition: normal, volatile, overnight
--symbol       Trading symbol (default: BTC/USDT)
--capital      Initial capital (default: 10000.0)
```

## Monitoring

### Real-time Console Output
The script displays live updates every iteration:
- Current iteration (X/Y)
- Total trades executed
- Win rate percentage
- Total P&L
- Current drawdown
- Signal distribution

### Checkpoints
Results auto-save every 10 iterations to:
- `data/live_test/live_test_log_{session_id}.csv`
- `data/live_test/live_test_results.json`

### Stopping Early
Press `Ctrl+C` to stop gracefully. All progress is saved.

### Long-running Sessions
For tests lasting hours/days, use screen or tmux:

```bash
# Start screen session
screen -S live_test

# Run test
python run_live_test.py --session 1 --iterations 100 --interval 300

# Detach: Ctrl+A then D
# Reattach later: screen -r live_test
```

## Understanding Results

### Key Files Generated

#### 1. CSV Log (`live_test_log_{session_id}.csv`)
Every iteration logged:
```csv
timestamp,iteration,signal,confidence,price,action,pnl,reason
2025-11-09 10:05:00,1,HOLD,0.70,103500,,,RSI neutral
2025-11-09 10:10:00,2,BUY,0.85,103400,OPEN,,Oversold bounce
2025-11-09 10:30:00,6,SELL,0.75,103800,CLOSE,+400,Take profit
```

#### 2. JSON Results (`live_test_results.json`)
Complete statistics:
```json
{
  "test_sessions": [...],
  "aggregated_results": {
    "total_iterations": 200,
    "total_trades": 28,
    "overall_win_rate": 0.57,
    "total_pnl": 512.30
  }
}
```

#### 3. Markdown Report (`LIVE_TEST_REPORT.md`)
Human-readable analysis with:
- Executive summary
- Performance by session
- Signal distribution
- Recommendations
- Next steps

### Performance Metrics

#### Win Rate
- **Target**: > 50%
- **Good**: > 55%
- **Excellent**: > 60%

#### Total P&L
- Must be positive
- Should exceed API costs
- Consistency matters more than magnitude

#### Max Drawdown
- **Target**: < 15%
- **Warning**: > 10%
- **Critical**: > 15%

#### Signal Distribution
- **Expected**: ~25% BUY, ~35% SELL, ~40% HOLD
- Balanced = healthy strategy
- Too many HOLDs = overly cautious
- Too many BUY/SELL = overtrading

## Cost Estimation

### OpenAI API Costs
- **Per iteration**: ~$0.0015 (500 tokens)
- **100 iterations**: ~$0.15
- **200 iterations**: ~$0.30
- **24-hour run**: ~$0.50 - $1.00

### Groq (Free Alternative)
- **Cost**: $0 (free tier)
- **Limit**: 30 requests/minute
- **Good for**: Testing without API costs

## Troubleshooting

### "No exchange connection"
**Solution**: Verify API keys in `.env` or run without exchange (uses simulated data)

### "OpenAI API error"
**Solutions**:
- Verify `OPENAI_API_KEY` is correct
- Check usage limits on OpenAI dashboard
- Consider switching to Groq

### High drawdown (>10%)
**Actions**:
- Review recent trades in CSV log
- Check market volatility
- Consider reducing position size
- Adjust strategy parameters

### Bot crashes/errors
**Recovery**:
- Check logs in `data/live_test/session_*.log`
- Verify all dependencies installed
- Ensure stable internet connection
- Restart with same session ID to continue

## Best Practices

### 1. Start Small
```bash
# Test with 3 iterations first
python run_live_test.py --session 0 --iterations 3 --interval 10
```

### 2. Run During Appropriate Times
- Session 1: Regular trading hours
- Session 2: High volatility periods
- Session 3: Overnight/quiet hours

### 3. Monitor Actively
- First 10 iterations: Watch closely
- After that: Check every hour
- Use alerts for critical drawdown

### 4. Save Results
All results are auto-saved, but consider backing up:
```bash
cp -r data/live_test backup/live_test_$(date +%Y%m%d)
```

### 5. Iterate and Improve
- Review CSV logs for patterns
- Adjust parameters based on results
- Re-run tests to validate changes

## Next Steps After Testing

### If Results Are Good (Win Rate > 50%, Drawdown < 15%)
1. ✅ Run additional sessions to confirm
2. ✅ Test with different symbols
3. ✅ Progress to paper trading with larger capital
4. ✅ Monitor for 1 week minimum
5. ✅ Consider live trading only after extensive validation

### If Results Need Improvement
1. ⚠️ Analyze losing trades
2. ⚠️ Adjust strategy parameters
3. ⚠️ Reduce position size
4. ⚠️ Add filters (volatility, time-of-day)
5. ⚠️ Re-test with adjustments

## Support & Documentation

- **Quick Start**: See `data/live_test/README.md`
- **Integration**: Check `INTEGRATION_GUIDE.md`
- **General Setup**: Review `QUICKSTART.md`
- **Examples**: Browse `examples/` directory

## Example Workflow

### Day 1: Initial Testing
```bash
# Morning: Quick test
python run_live_test.py --session 0 --iterations 3 --interval 10

# If successful, start Session 1
python run_live_test.py --session 1 --iterations 100 --interval 300
```

### Day 2: Review & Continue
```bash
# Review results
cat data/live_test/LIVE_TEST_REPORT.md

# If good, run Session 2 during volatile period
python run_live_test.py --session 2 --iterations 50 --interval 120 --condition volatile
```

### Day 3: Complete Testing
```bash
# Run overnight session
python run_live_test.py --session 3 --iterations 50 --interval 600 --condition overnight

# Next morning: Review all results
cat data/live_test/LIVE_TEST_REPORT.md
```

## Safety Reminders

⚠️ **This is testnet testing with dry-run mode**
- No real money at risk
- No actual trades executed
- Safe environment for validation

⚠️ **Before live trading**
- Complete all test scenarios
- Achieve consistent win rate > 50%
- Maintain drawdown < 15%
- Test for at least 1 week
- Start with minimal capital

⚠️ **Never skip testing**
- Moving directly to live trading is extremely risky
- Testing validates strategy effectiveness
- Identifies weaknesses before real money is involved

---

**Remember**: The goal is not to achieve perfect results, but to understand strategy behavior under different conditions and build confidence before risking real capital.

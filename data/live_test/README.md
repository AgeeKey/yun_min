# Live Test Suite - Extended Testnet Validation

This directory contains tools for running extended live tests on Binance testnet with 100+ iterations.

## Quick Start

### Basic Usage

```bash
# Session 1: Normal market conditions (100 iterations, 5-min intervals)
python run_live_test.py --session 1 --iterations 100 --interval 300

# Session 2: Volatile market (50 iterations, 2-min intervals)
python run_live_test.py --session 2 --iterations 50 --interval 120 --condition volatile

# Session 3: Overnight test (50 iterations, 10-min intervals)  
python run_live_test.py --session 3 --iterations 50 --interval 600 --condition overnight
```

### Command Line Options

- `--session`: Session ID (1, 2, 3, etc.)
- `--iterations`: Number of iterations to run (default: 100)
- `--interval`: Seconds between iterations (default: 300)
- `--condition`: Market condition type - `normal`, `volatile`, or `overnight` (default: normal)
- `--symbol`: Trading symbol (default: BTC/USDT)
- `--capital`: Initial capital (default: 10000.0)

## Test Scenarios

### Session 1: Normal Market (Recommended First)
**Goal**: Validate strategy during regular trading hours

```bash
python run_live_test.py --session 1 --iterations 100 --interval 300
```

- **Iterations**: 100
- **Interval**: 5 minutes (300 seconds)
- **Expected Duration**: ~8.3 hours
- **Best Time**: During regular US/EU trading hours
- **Purpose**: Baseline performance metrics

### Session 2: Volatile Market
**Goal**: Test strategy under pressure with faster trading

```bash
python run_live_test.py --session 2 --iterations 50 --interval 120 --condition volatile
```

- **Iterations**: 50
- **Interval**: 2 minutes (120 seconds)
- **Expected Duration**: ~1.7 hours
- **Best Time**: During high-volatility events (news, market opens)
- **Purpose**: Stress testing and whipsaw resistance

### Session 3: Overnight Market
**Goal**: Validate robustness in quiet markets

```bash
python run_live_test.py --session 3 --iterations 50 --interval 600 --condition overnight
```

- **Iterations**: 50
- **Interval**: 10 minutes (600 seconds)
- **Expected Duration**: ~8.3 hours
- **Best Time**: During low liquidity hours (Asian night, US night)
- **Purpose**: Low-volatility performance validation

## Setup Requirements

### 1. Environment Configuration

Create or update `.env` file:

```bash
# Exchange (Binance Testnet)
BINANCE_API_KEY=your_testnet_api_key
BINANCE_SECRET_KEY=your_testnet_secret_key

# OpenAI (for LLM-powered signals)
OPENAI_API_KEY=your_openai_api_key

# Or use Groq instead
YUNMIN_LLM_PROVIDER=grok
GROK_API_KEY=your_grok_api_key
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Verify Setup

```bash
# Quick test (3 iterations)
python examples/basic_bot.py
```

## Monitoring During Test

### Real-time Progress

The script displays real-time progress including:
- Current iteration (X/Y)
- Total trades executed
- Win rate
- Total P&L
- Current drawdown
- Signal distribution (BUY/SELL/HOLD)

### Checkpoints

Results are automatically saved every 10 iterations to:
- `data/live_test/live_test_log_{session_id}.csv`
- `data/live_test/live_test_results.json`

### Stopping Early

Press `Ctrl+C` to stop the test gracefully. All progress will be saved.

## Understanding Results

### Output Files

After each session, the following files are generated:

#### 1. `live_test_log_{session_id}.csv`
Detailed log of every iteration with columns:
- `timestamp`: When the signal was generated
- `iteration`: Iteration number
- `signal`: BUY, SELL, or HOLD
- `confidence`: Signal confidence (0-1)
- `price`: Market price at that moment
- `action`: OPEN or CLOSE (if trade executed)
- `pnl`: Profit/loss (if position closed)
- `reason`: AI reasoning for the signal

#### 2. `live_test_results.json`
Complete session statistics including:
- Session metadata (ID, start/end time, duration)
- Trade performance (total, winning, losing, win rate)
- P&L metrics (total, max drawdown)
- Signal distribution
- OpenAI API usage and costs
- Aggregated results across all sessions

#### 3. `LIVE_TEST_REPORT.md`
Human-readable analysis report with:
- Executive summary
- Performance by session
- Key findings and recommendations
- Signal distribution analysis
- Risk metrics
- Next steps

### Key Metrics

**Win Rate**: Percentage of profitable trades
- Target: > 50%
- Good: > 55%
- Excellent: > 60%

**Total P&L**: Net profit/loss across all trades
- Positive is good
- Should exceed OpenAI API costs

**Max Drawdown**: Maximum peak-to-trough decline
- Target: < 15%
- Warning: > 10%
- Critical: > 15%

**Signal Distribution**: Balance of signals
- Expected: ~25% BUY, ~35% SELL, ~40% HOLD
- Balanced distribution indicates healthy strategy

## Troubleshooting

### No Exchange Connection
If you see "No exchange connection - using dummy data":
- Verify API keys in `.env` file
- Ensure Binance testnet is accessible
- Check API key permissions

### OpenAI API Errors
If LLM analysis fails:
- Verify `OPENAI_API_KEY` is set correctly
- Check OpenAI dashboard for usage limits
- Consider switching to Groq (free alternative)

### High Drawdown Alert
If drawdown exceeds 10%:
- Review recent trades in CSV log
- Check market conditions (high volatility?)
- Consider reducing position size
- Review strategy parameters

## Best Practices

### Running Multiple Sessions

1. **Complete one session before starting another**
   - Allows proper cooldown between tests
   - Prevents API rate limiting
   - Ensures clean data separation

2. **Run sessions at different times**
   - Session 1: Regular trading hours (9 AM - 5 PM)
   - Session 2: High volatility periods (market open, news events)
   - Session 3: Overnight/quiet hours (10 PM - 6 AM)

3. **Use screen/tmux for long sessions**
   ```bash
   # Start screen session
   screen -S live_test
   
   # Run test
   python run_live_test.py --session 1 --iterations 100 --interval 300
   
   # Detach: Ctrl+A then D
   # Reattach: screen -r live_test
   ```

### Monitoring Tools

**During Test**:
- Monitor logs: `tail -f data/live_test/session_*.log`
- Check progress: Review console output
- Watch system: Ensure stable internet connection

**After Test**:
- Review CSV log for patterns
- Analyze JSON results for statistics
- Read markdown report for insights

## API Costs

### OpenAI (GPT-4o-mini)
- **Per iteration**: ~$0.0015 (~500 tokens)
- **100 iterations**: ~$0.15
- **200 iterations**: ~$0.30
- **Daily (24h)**: ~$0.50 - $1.00

### Groq (Free Alternative)
- **Per iteration**: $0 (free tier)
- **Limit**: 30 requests/minute
- **Best for**: Testing without API costs

## Next Steps After Testing

### If Results Are Good (Win Rate > 50%, Drawdown < 15%)
1. ✅ Run additional sessions to confirm
2. ✅ Test with different symbols (ETH/USDT, etc.)
3. ✅ Progress to paper trading with larger capital
4. ✅ Monitor for 1 week before considering live trading

### If Results Need Improvement
1. ⚠️ Analyze losing trades in CSV logs
2. ⚠️ Adjust strategy parameters
3. ⚠️ Consider reducing position size
4. ⚠️ Add volatility filters
5. ⚠️ Re-run tests with adjustments

## Support

For questions or issues:
1. Check `INTEGRATION_GUIDE.md` for general setup
2. Review `QUICKSTART.md` for basic usage
3. Check logs in `data/live_test/session_*.log`
4. Refer to example files in `data/live_test/*_example.*`

---

**Remember**: This is testnet testing. No real money is at risk. Use these tests to gain confidence before progressing to paper trading and eventually live trading.

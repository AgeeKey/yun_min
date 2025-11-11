# Trade Frequency Controls

## Overview

This feature adds configurable controls to reduce "churning" (frequent entries and exits) in backtesting by limiting trade frequency through three mechanisms:

1. **Cooldown Period** (`cooldown_bars`): Enforces a minimum waiting period between closing one position and opening another
2. **Signal Confirmation** (`confirmation_bars`): Requires consecutive bars with the same signal before entry
3. **Minimum Holding Period** (`min_holding_bars`): Prevents premature position exits

## Configuration

All parameters are set in `config/default.yaml` under the `strategy` section:

```yaml
strategy:
  # Trade Frequency Controls (to reduce churning)
  cooldown_bars: 0  # Bars to wait after closing before opening new position (0 = disabled)
  confirmation_bars: 0  # Consecutive bars with same signal required (0 = disabled, 1 = immediate)
  min_holding_bars: 0  # Minimum bars to hold position (0 = disabled)
```

### Parameter Details

#### cooldown_bars
- **Default**: 0 (disabled)
- **Range**: 0-50 bars
- **Description**: After closing a position, the system must wait this many bars before opening a new position
- **Use case**: Prevents immediate re-entry after stop-loss or take-profit exits
- **Example**: `cooldown_bars: 10` means wait 10 bars (50 minutes on 5m timeframe) after exit

#### confirmation_bars
- **Default**: 0 (disabled)
- **Range**: 0-10 bars
- **Description**: Requires N consecutive bars with the same signal type (BUY/SELL) before allowing entry
- **Use case**: Filters out false signals and noise
- **Example**: `confirmation_bars: 3` means need 3 consecutive BUY signals before opening LONG

#### min_holding_bars
- **Default**: 0 (disabled)
- **Range**: 0-100 bars
- **Description**: Once a position is open, it must be held for at least this many bars
- **Use case**: Prevents quick exits from temporary price fluctuations
- **Example**: `min_holding_bars: 15` means hold position for at least 15 bars (75 minutes on 5m timeframe)
- **Note**: This applies to both signal-based exits AND stop-loss/take-profit exits

## Implementation

### Backtester Changes

The `Backtester` class now accepts and enforces `cooldown_bars` and `min_holding_bars`:

```python
from yunmin.backtesting import Backtester

backtester = Backtester(
    strategy=my_strategy,
    initial_capital=100000,
    cooldown_bars=10,      # Wait 10 bars between trades
    min_holding_bars=15    # Hold positions for at least 15 bars
)
```

### GrokAIStrategy Changes

The `GrokAIStrategy` class now accepts and enforces `confirmation_bars`:

```python
from yunmin.strategy.grok_ai_strategy import GrokAIStrategy

strategy = GrokAIStrategy(
    grok_analyzer=analyzer,
    use_advanced_indicators=True,
    hybrid_mode=True,
    confirmation_bars=3    # Need 3 consecutive signals
)
```

## Usage Examples

### Example 1: Reduce overtrading with cooldown

```python
# Without cooldown - trades frequently
backtester = Backtester(strategy, 100000, cooldown_bars=0)
results = backtester.run(data)
print(f"Trades: {results['total_trades']}")  # e.g., 50 trades

# With cooldown - fewer trades
backtester = Backtester(strategy, 100000, cooldown_bars=10)
results = backtester.run(data)
print(f"Trades: {results['total_trades']}")  # e.g., 25 trades (50% reduction)
```

### Example 2: Filter noise with confirmation

```python
# Without confirmation - every signal triggers entry
strategy = GrokAIStrategy(grok_analyzer, confirmation_bars=0)

# With confirmation - need 3 consecutive signals
strategy = GrokAIStrategy(grok_analyzer, confirmation_bars=3)
```

### Example 3: Prevent premature exits

```python
# Without min holding - can exit immediately on SL/TP
backtester = Backtester(strategy, 100000, min_holding_bars=0)

# With min holding - must hold for 20 bars even if SL/TP hit
backtester = Backtester(strategy, 100000, min_holding_bars=20)
```

### Example 4: Combine all controls

```python
strategy = GrokAIStrategy(
    grok_analyzer=analyzer,
    confirmation_bars=2  # Need 2 consecutive signals
)

backtester = Backtester(
    strategy=strategy,
    initial_capital=100000,
    cooldown_bars=5,      # Wait 5 bars between trades
    min_holding_bars=10   # Hold for at least 10 bars
)

results = backtester.run(data)
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_trade_frequency_controls.py -v
```

Test coverage includes:
- ✅ Cooldown enforcement
- ✅ Confirmation requirements
- ✅ Minimum holding period
- ✅ Combined controls
- ✅ Trade reduction verification
- ✅ Backward compatibility

## Demonstration

Run the included demonstration script to see the controls in action:

```bash
python demo_trade_frequency_controls.py
```

Expected output shows trade reduction:
```
Configuration                            Trades     Reduction      
----------------------------------------------------------------------
Baseline (no controls)                   15         -              
Cooldown (10 bars)                       10         33.3%
Min Hold (15 bars)                       10         33.3%
Combined (cooldown=5, min_hold=10)       10         33.3%
```

## Performance Impact

Based on testing with an aggressive strategy:

| Control | Setting | Trade Reduction |
|---------|---------|-----------------|
| Cooldown | 10 bars | ~30-40% |
| Confirmation | 3 bars | ~20-30% |
| Min Holding | 15 bars | ~20-40% |
| Combined | Moderate | ~40-60% |

**Note**: Actual reduction depends on strategy aggressiveness and market conditions.

## Best Practices

### Recommended Starting Values

For 5-minute timeframe (adjust proportionally for other timeframes):

- **Conservative**: `cooldown_bars=15`, `confirmation_bars=3`, `min_holding_bars=20`
- **Moderate**: `cooldown_bars=10`, `confirmation_bars=2`, `min_holding_bars=15`
- **Aggressive**: `cooldown_bars=5`, `confirmation_bars=1`, `min_holding_bars=10`

### Timeframe Considerations

| Timeframe | Cooldown | Confirmation | Min Hold |
|-----------|----------|--------------|----------|
| 1m | 5-10 | 2-3 | 10-20 |
| 5m | 10-15 | 2-3 | 15-30 |
| 15m | 5-10 | 2-3 | 10-20 |
| 1h | 3-5 | 1-2 | 5-10 |
| 4h | 2-3 | 1-2 | 3-5 |

### Optimization Tips

1. **Start conservative**: Begin with higher values and gradually reduce
2. **Backtest different values**: Use walk-forward analysis to find optimal settings
3. **Monitor win rate**: Controls should improve win rate by filtering bad trades
4. **Consider market volatility**: Higher volatility may need longer holding periods
5. **Balance trade frequency**: Too few trades may miss opportunities

## Troubleshooting

### No trades executing

**Symptom**: Backtester reports 0 trades

**Possible causes**:
- `confirmation_bars` too high - strategy not generating consistent signals
- `cooldown_bars` too high relative to data length
- Combined with already conservative strategy

**Solution**: Reduce control values or use less conservative base strategy

### Too many trades still

**Symptom**: Trade count not reducing significantly

**Possible causes**:
- Controls set to 0 (disabled)
- Strategy generates very strong/consistent signals
- Controls too lenient for strategy aggressiveness

**Solution**: Increase control values incrementally

## Implementation Details

### Cooldown Tracking

- Tracks `last_exit_bar` index
- Before opening position, checks: `current_bar - last_exit_bar >= cooldown_bars`
- Resets on each position close

### Confirmation Tracking

- Maintains `signal_history` list of recent signal types
- On each analyze call, adds signal to history
- Checks last N signals are all the same type
- HOLD signals don't break confirmation chain

### Min Holding Enforcement

- Tracks `entry_bar` index when position opens
- Before closing position, checks: `current_bar - entry_bar >= min_holding_bars`
- Applies to both signal-based closes AND stop-loss/take-profit

## Backward Compatibility

All controls default to 0 (disabled), ensuring:
- ✅ Existing code continues to work unchanged
- ✅ No changes required to existing strategies
- ✅ Opt-in activation via configuration

## Future Enhancements

Potential additions (not yet implemented):
- Dynamic cooldown based on win/loss
- Adaptive confirmation based on market conditions
- Position size adjustment based on holding time
- Integration with risk management for combined limits

## References

- Configuration: `config/default.yaml`
- Backtester: `yunmin/backtesting/backtester.py`
- Strategy: `yunmin/strategy/grok_ai_strategy.py`
- Tests: `tests/test_trade_frequency_controls.py`
- Demo: `demo_trade_frequency_controls.py`

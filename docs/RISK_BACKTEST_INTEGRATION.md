# Risk Manager Integration with Backtester

## Overview

The RiskManager is now fully integrated into the backtesting process to enforce pre-trade risk checks. Trades that violate risk policies are automatically rejected and logged with detailed reasons.

## Features

### 1. Pre-Trade Risk Validation

Every trade attempt (long or short) is validated against the following risk policies before execution:

- **Max Position Size**: Limits position size as a fraction of capital
- **Max Leverage**: Prevents excessive leverage usage
- **Max Daily Drawdown**: Halts trading if daily loss limit is exceeded
- **Stop Loss**: Enforces stop loss on positions
- **Margin Check**: Ensures sufficient margin for leveraged positions
- **Circuit Breaker**: Emergency halt for abnormal market conditions
- **Exchange Margin Level**: Monitors actual margin level to prevent liquidation
- **Funding Rate Limit**: Prevents positions with excessive funding rates

### 2. Rejection Tracking

When a trade is rejected:
- The rejection is logged with `logger.warning` including timestamp and reasons
- A `RejectedTrade` object is created and stored in metrics
- All rejection reasons are preserved for analysis

### 3. Detailed Logging

Rejected trades include:
- **Timestamp**: When the trade was attempted
- **Symbol**: Trading pair (e.g., BTC/USDT)
- **Side**: LONG or SHORT
- **Amount**: Proposed position size
- **Price**: Intended execution price
- **Rejection Reasons**: List of all policy violations

### 4. CSV Export

Rejected trades can be exported to CSV for detailed analysis:

```python
rejected_log = backtester.get_rejected_trades_log()
rejected_log.to_csv('rejected_trades.csv', index=False)
```

### 5. Metrics Integration

Backtest results now include:
- `rejected_trades`: Count of rejected trades
- Approval rate: Percentage of trades that passed risk checks

## Usage Example

### Basic Usage

```python
from yunmin.backtesting import Backtester
from yunmin.strategy.base import BaseStrategy
from yunmin.core.config import RiskConfig
from yunmin.risk.manager import RiskManager

# Setup strategy
strategy = MyStrategy()

# Configure risk limits
risk_config = RiskConfig(
    max_position_size=0.10,      # Max 10% of capital per position
    max_leverage=3.0,            # Max 3x leverage
    max_daily_drawdown=0.05,     # Max 5% daily drawdown
    stop_loss_pct=0.02,          # 2% stop loss
    take_profit_pct=0.03,        # 3% take profit
    enable_circuit_breaker=True  # Enable emergency halt
)

# Create backtester with risk manager
backtester = Backtester(
    strategy=strategy,
    initial_capital=10000,
    use_risk_manager=True  # Enabled by default
)
backtester.risk_manager = RiskManager(risk_config)

# Run backtest
results = backtester.run(data, symbol="BTC/USDT", position_size_pct=0.10)

# Check results
print(f"Executed Trades: {results['total_trades']}")
print(f"Rejected Trades: {results['rejected_trades']}")
```

### Accessing Rejected Trades

```python
# Get rejected trades as DataFrame
rejected_log = backtester.get_rejected_trades_log()

# Display first few rejections
print(rejected_log.head())

# Export to CSV
rejected_log.to_csv('rejected_trades.csv', index=False)

# Analyze rejection reasons
for idx, row in rejected_log.iterrows():
    print(f"Trade #{idx + 1} rejected at {row['timestamp']}")
    print(f"  Reasons: {row['rejection_reasons']}")
```

### Generating Reports

```python
from yunmin.backtesting import ReportGenerator

# Generate text report
report = ReportGenerator.generate_text_report(
    results, 
    strategy_name="MyStrategy"
)
print(report)

# Save to file
ReportGenerator.save_report(report, "backtest_report.txt")
```

## Report Output

Reports now include a Risk Management section:

```
RISK MANAGEMENT
--------------------------------------------------------------------------------
Rejected Trades:               15
Approval Rate:              62.50%
```

This shows:
- How many trades were rejected by risk policies
- What percentage of trade signals passed risk checks

## Demo Script

Run the included demo to see the integration in action:

```bash
python examples/risk_backtest_demo.py
```

This demonstrates:
- Risk manager rejecting oversized positions
- Detailed logging of rejection reasons
- CSV export of rejected trades
- Comparison with/without risk management

## Testing

Comprehensive test suite validates:

1. **Max Position Size Rejection** - Trades exceeding position size limits are rejected
2. **Max Daily Drawdown** - Trading halts after daily loss limit
3. **Circuit Breaker** - Emergency halt prevents all trading
4. **Rejection Logging** - All rejections are properly logged
5. **CSV Export** - Rejected trades can be exported
6. **Normal Operation** - Valid trades execute correctly

Run tests:

```bash
pytest tests/test_risk_backtest_integration.py -v
```

## Benefits

### Capital Protection
- Prevents overleveraged positions
- Limits daily losses
- Enforces stop losses automatically

### Audit Trail
- Complete record of all rejected trades
- Detailed reasons for each rejection
- Exportable for compliance/analysis

### Risk Awareness
- Visibility into how often trades violate policies
- Approval rate metrics
- Easy identification of problematic strategies

## Configuration Options

### Strict Risk Management (Conservative)
```python
RiskConfig(
    max_position_size=0.05,      # Only 5% per position
    max_leverage=2.0,            # Low leverage
    max_daily_drawdown=0.03,     # 3% daily limit
    enable_circuit_breaker=True
)
```

### Balanced Risk Management (Moderate)
```python
RiskConfig(
    max_position_size=0.10,      # 10% per position
    max_leverage=3.0,            # Moderate leverage
    max_daily_drawdown=0.05,     # 5% daily limit
    enable_circuit_breaker=True
)
```

### Aggressive Risk Management (Higher Risk)
```python
RiskConfig(
    max_position_size=0.15,      # 15% per position
    max_leverage=5.0,            # Higher leverage
    max_daily_drawdown=0.08,     # 8% daily limit
    enable_circuit_breaker=True
)
```

## Notes

- Risk manager is **enabled by default** in backtester
- All rejections are logged via `loguru.logger`
- Rejected trades do NOT affect capital or equity curve
- Circuit breaker can be manually triggered for emergency situations
- Custom risk policies can be added via `risk_manager.add_policy()`

## See Also

- `yunmin/risk/manager.py` - RiskManager implementation
- `yunmin/risk/policies.py` - Risk policy definitions
- `examples/risk_demo.py` - Basic risk manager demo
- `examples/risk_backtest_demo.py` - Backtest integration demo

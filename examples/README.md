# YunMin Examples

This directory contains example scripts demonstrating various features of the YunMin trading bot.

## Available Examples

### 🌐 WebSocket Streaming (NEW!)

**File**: `websocket_demo.py`

Demonstrates real-time market data streaming with WebSocket:
- Real-time trade updates (every trade)
- Kline/candle updates (5-minute intervals)
- 24hr ticker statistics
- Sub-second latency (300x faster than REST polling)

**Usage**:
```bash
python examples/websocket_demo.py
```

**What it shows**:
- ⚡ Live BTC price updates
- 🕯️ Candle closes with OHLCV data
- 📈 24hr volume and price changes
- ✅ Auto-reconnection on disconnect

**Duration**: Runs for 30 seconds by default

### 🤖 AI Agent Integration

**File**: `ai_agent_demo.py`

Shows how to use AI-powered trading agents for decision making.

### 🧠 Advanced AI Framework

**File**: `advanced_ai_framework_example.py`

Demonstrates advanced AI strategies with multiple models.

### 🎯 Basic Bot

**File**: `basic_bot.py`

Simple example of setting up a basic trading bot with EMA crossover strategy.

### 🤖 ML Integration

**File**: `ml_integration_demo.py`

Shows how to integrate machine learning models for predictions.

### ⚠️ Risk Management

**File**: `risk_demo.py`

Demonstrates risk management features including:
- Position sizing
- Stop-loss/take-profit
- Portfolio limits

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run an example**:
   ```bash
   python examples/websocket_demo.py
   ```

3. **Customize**:
   Edit the example files to experiment with different parameters.

## WebSocket Example Output

When running `websocket_demo.py`, you'll see:

```
======================================================================
WebSocket Demo - Monitoring BTCUSDT
Mode: Mainnet
Duration: 30 seconds
======================================================================
✅ Subscribed to all streams, starting...
💰 Trade #5 | BTCUSDT | Price: $103,550.25 | Qty: 0.050000 | Change: +0.15%
💰 Trade #10 | BTCUSDT | Price: $103,551.10 | Qty: 0.025000 | Change: +0.08%
🕯️  Candle CLOSED | BTCUSDT 5m | O: 103500.00 H: 103600.00 L: 103400.00 C: 103550.00 | Vol: 150.50
📈 Ticker #1 | BTCUSDT | Price: $103,550.00 | 24h Change: +500.00 (+0.48%) | 24h Volume: 10,000.50
...
======================================================================
Demo Statistics:
  • Kline updates: 12
  • Trade updates: 50
  • Ticker updates: 3
  • Last price: $103,550.25
======================================================================
```

## Integration with Your Bot

See `docs/WEBSOCKET_INTEGRATION.md` for detailed guide on integrating WebSocket streaming into your trading bot.

## Need Help?

- 📖 Check the [main documentation](../docs/)
- 💬 Ask questions in GitHub Issues
- 🐛 Report bugs with example code

## Contributing

Feel free to add more examples! Submit a PR with:
- Clear documentation in the file
- Usage instructions
- Expected output

---

**Note**: All examples use paper trading by default. Configure API keys in `.env` for live trading (use at your own risk).

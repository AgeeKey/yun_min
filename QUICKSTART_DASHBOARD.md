# 🚀 Quick Start: Web Dashboard

Get the YunMin Trading Dashboard up and running in 2 minutes!

## Prerequisites

```bash
# Python 3.8 or higher
python --version

# Install dependencies
pip install fastapi uvicorn jinja2 python-multipart loguru
```

## Start the Dashboard

### Option 1: Using the Example Script (Recommended)

```bash
cd examples
python run_dashboard.py
```

### Option 2: Direct Uvicorn Command

```bash
# From project root
python -m uvicorn yunmin.web.api:app --host 0.0.0.0 --port 5000

# With auto-reload for development
python -m uvicorn yunmin.web.api:app --host 0.0.0.0 --port 5000 --reload
```

### Option 3: Python Script

```python
import uvicorn
from yunmin.web.api import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
```

## Access the Dashboard

Open your browser to: **http://localhost:5000**

You should see:
- 📈 TradingView candlestick chart
- 💰 Portfolio metrics
- 📊 Equity curve
- 💹 Open positions
- 📜 Trade history

## What You'll See

### Main Chart (TradingView-style)
- Green/red candlesticks (like Binance)
- Volume histogram below
- EMA indicator lines (blue & orange)
- BUY/SELL trade markers
- Zoom and pan controls

### Portfolio Stats (Right Sidebar)
- Current capital
- Total P&L
- Win rate
- Number of trades

### Bottom Section
- Equity curve chart (portfolio value over time)
- Recent trades list with timestamps

## Testing the API

```bash
# Health check
curl http://localhost:5000/health

# Get portfolio metrics
curl http://localhost:5000/api/portfolio

# Get candlestick data
curl http://localhost:5000/api/candles?symbol=BTC/USDT&interval=5m&limit=100

# Get equity curve
curl http://localhost:5000/api/equity-curve?days=7
```

## Connecting Your Trading Bot

To display live data from your bot:

```python
from yunmin.web.api import create_app, broadcast_trade

# Initialize with your bot components
app = create_app(
    portfolio_manager=my_portfolio,
    position_monitor=my_positions,
    pnl_tracker=my_pnl,
    alert_manager=my_alerts
)

# Broadcast events
await broadcast_trade({
    "symbol": "BTC/USDT",
    "side": "BUY",
    "price": 50000,
    "amount": 0.01
})
```

## Customization

### Change Port

```bash
python examples/run_dashboard.py --port 8080
```

### Enable Auto-Reload (Development)

```bash
python examples/run_dashboard.py --reload
```

### Change Theme Colors

Edit `yunmin/web/static/css/dashboard.css`:

```css
/* Change chart colors */
.chart-container {
    --bullish-color: #26a69a;  /* Green */
    --bearish-color: #ef5350;  /* Red */
}
```

## Troubleshooting

### Server won't start?

```bash
# Check if port is in use
lsof -i :5000

# Use different port
python examples/run_dashboard.py --port 8080
```

### Charts not loading?

1. Check browser console (F12)
2. Verify internet connection (uses CDN for libraries)
3. Try hard refresh: Ctrl+F5

### Can't access from another device?

Make sure you're using `--host 0.0.0.0`:

```bash
python examples/run_dashboard.py --host 0.0.0.0
```

Then access from other device: `http://YOUR_IP:5000`

## Next Steps

- 📖 Read the full documentation: `yunmin/web/README.md`
- 🔧 Customize the dashboard for your needs
- 🔌 Connect your trading bot data
- 📱 Access from mobile devices
- 🔐 Add authentication for production use

## Support

- **Documentation**: See `yunmin/web/README.md`
- **Issues**: GitHub Issues
- **Examples**: See `examples/` directory

---

**Happy Trading! 🎉📈**

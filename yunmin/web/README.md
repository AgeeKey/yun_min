# YunMin Trading Dashboard 📊

Professional TradingView-style web dashboard for monitoring your YunMin trading bot in real-time. Features Binance-style candlestick charts, live portfolio metrics, and trade history.

![Dashboard Preview](https://img.shields.io/badge/Status-Live-green)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)

## Features

### 📈 Professional Charts
- **TradingView Lightweight Charts** - Same library used by Binance
- Real-time candlestick display (green/red candles)
- Volume histogram below main chart
- EMA indicator lines (9 & 21 period)
- Trade markers (BUY/SELL arrows on chart)
- Zoom & pan functionality
- Crosshair with price/time display

### 💹 Live Portfolio Monitoring
- Current equity tracking
- Real-time P&L (profit & loss)
- Win rate statistics
- Open positions display
- Trade history

### 🔄 Real-time Updates
- WebSocket connection for live data
- Automatic reconnection on disconnect
- Live price ticking
- Instant trade notifications

### 🎨 Professional UI
- Dark theme (Binance-style)
- Responsive design (mobile-friendly)
- Clean, modern interface
- No build step required

## Quick Start

### Installation

```bash
# Install required dependencies
pip install fastapi uvicorn jinja2 python-multipart loguru

# Or from project root
pip install -r requirements.txt
```

### Running the Dashboard

```bash
# Option 1: From web directory
cd yunmin/web
uvicorn api:app --reload --port 5000

# Option 2: From project root
python -m uvicorn yunmin.web.api:app --host 0.0.0.0 --port 5000

# Option 3: Direct execution
python yunmin/web/api.py
```

Then open your browser to: **http://localhost:5000**

## Architecture

### File Structure

```
yunmin/web/
├── api.py                          # FastAPI backend with REST & WebSocket
├── templates/
│   └── index.html                  # Main dashboard page
└── static/
    ├── css/
    │   └── dashboard.css           # Custom dark theme styles
    └── js/
        ├── chart-tradingview.js    # Candlestick chart module
        ├── chart-equity.js         # Equity curve chart module
        ├── websocket-client.js     # WebSocket client handler
        └── dashboard.js            # Main application logic
```

### Technology Stack

**Frontend:**
- HTML5 + Vanilla JavaScript (ES6 modules)
- [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) - Professional candlestick charts
- [Chart.js](https://www.chartjs.org/) - Equity curve & secondary charts
- [Tailwind CSS](https://tailwindcss.com/) (CDN) - Responsive styling

**Backend:**
- FastAPI - Modern Python web framework
- Uvicorn - ASGI server
- Jinja2 - Template engine
- WebSocket - Real-time communication

## API Endpoints

### REST Endpoints

```
GET  /                      # Main dashboard page
GET  /health                # Health check
GET  /api/portfolio         # Portfolio metrics
GET  /api/positions         # Open positions
GET  /api/trades            # Recent trades
GET  /api/candles           # Candlestick data
GET  /api/equity-curve      # Equity curve data
GET  /api/performance       # Performance metrics
GET  /api/alerts            # Recent alerts
```

### WebSocket

```
WS   /ws                    # Real-time updates
```

### Example API Calls

```bash
# Get portfolio metrics
curl http://localhost:5000/api/portfolio

# Get candlestick data
curl http://localhost:5000/api/candles?symbol=BTC/USDT&interval=5m&limit=200

# Get equity curve
curl http://localhost:5000/api/equity-curve?days=7
```

## Customization

### Chart Configuration

Edit `static/js/chart-tradingview.js` to customize the chart appearance:

```javascript
this.chart = LightweightCharts.createChart(container, {
    layout: {
        background: { color: '#1e222d' },  // Background color
        textColor: '#d1d4dc',              // Text color
    },
    // ... more options
});
```

### Colors

Colors follow Binance theme:
- **Bullish (Up)**: `#26a69a` (Green)
- **Bearish (Down)**: `#ef5350` (Red)
- **EMA Fast**: `#2196F3` (Blue)
- **EMA Slow**: `#FF9800` (Orange)

Customize in `static/css/dashboard.css` or chart configuration files.

### Intervals

Supported timeframes:
- `1m` - 1 minute
- `5m` - 5 minutes (default)
- `15m` - 15 minutes
- `1h` - 1 hour
- `4h` - 4 hours
- `1d` - 1 day

## WebSocket Events

The dashboard listens for these WebSocket events:

```javascript
// Price update
{
    "type": "price_update",
    "payload": {
        "time": 1699564800,
        "open": 50000,
        "high": 50100,
        "low": 49900,
        "close": 50050,
        "volume": 123.45
    }
}

// Trade executed
{
    "type": "trade_executed",
    "payload": {
        "symbol": "BTC/USDT",
        "side": "BUY",
        "price": 50000,
        "amount": 0.01,
        "time": 1699564800
    }
}

// Portfolio update
{
    "type": "update",
    "payload": {
        "portfolio": { ... },
        "positions": [ ... ]
    }
}
```

## Integration with Trading Bot

To connect the dashboard to your trading bot:

```python
from yunmin.web.api import create_app, broadcast_trade, broadcast_position_update

# Initialize dashboard with your bot components
app = create_app(
    portfolio_manager=your_portfolio_manager,
    position_monitor=your_position_monitor,
    pnl_tracker=your_pnl_tracker,
    alert_manager=your_alert_manager
)

# Broadcast trade to dashboard
await broadcast_trade({
    "symbol": "BTC/USDT",
    "side": "BUY",
    "price": 50000,
    "amount": 0.01,
    "time": int(time.time())
})
```

## Troubleshooting

### Dashboard not loading?

1. Check server is running: `curl http://localhost:5000/health`
2. Check browser console for errors
3. Verify port 5000 is not in use: `lsof -i :5000`

### Charts not showing?

1. Check browser console for JavaScript errors
2. Verify CDN resources are loading (check Network tab)
3. Try refreshing the page with Ctrl+F5

### WebSocket not connecting?

1. Check WebSocket endpoint: Browser DevTools → Network → WS
2. Verify no firewall blocking WebSocket connections
3. Check server logs for WebSocket errors

### API returning empty data?

The dashboard shows mock data by default. Connect your actual trading bot components via `create_app()` to display real data.

## Performance

- **Lightweight**: Minimal dependencies, no build step
- **Efficient**: Only updates changed data
- **Scalable**: Supports multiple concurrent WebSocket connections
- **Responsive**: Works on desktop, tablet, and mobile

## Browser Support

- Chrome/Edge (recommended) - Full support
- Firefox - Full support
- Safari - Full support
- Mobile browsers - Full support (responsive design)

## Development

### Running in Development Mode

```bash
uvicorn yunmin.web.api:app --reload --port 5000 --log-level debug
```

### Adding New Features

1. Add API endpoint in `api.py`
2. Update frontend JavaScript in `static/js/`
3. Test endpoints with curl or Postman
4. Update documentation

### Code Structure

```javascript
// dashboard.js - Main application
class Dashboard {
    init()           // Initialize dashboard
    loadData()       // Load initial data
    connectWebSocket() // Setup WebSocket
    updateDisplay()  // Update UI elements
}

// chart-tradingview.js - Candlestick chart
class TradingChart {
    setData()        // Set historical data
    updateRealtime() // Update last candle
    addTradeMarker() // Add trade arrow
}

// websocket-client.js - WebSocket handler
class DashboardWebSocket {
    connect()        // Establish connection
    on()             // Register event handler
    send()           // Send message
}
```

## Security

**Important:** This dashboard is intended for local use or private networks.

For production deployment:
1. Enable HTTPS/WSS
2. Add authentication (JWT, OAuth, etc.)
3. Configure CORS properly
4. Use environment variables for secrets
5. Add rate limiting

## Contributing

To contribute to the dashboard:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

Part of the YunMin Trading Bot project. See main LICENSE file.

## Support

- **Issues**: GitHub Issues
- **Documentation**: See `docs/` folder
- **Examples**: See `examples/` folder

## Credits

- **TradingView Lightweight Charts** - Professional charting library
- **Chart.js** - Beautiful charts
- **FastAPI** - Modern Python web framework
- **Tailwind CSS** - Utility-first CSS framework

---

**Built with ❤️ for the YunMin Trading Bot**

Happy Trading! 🚀📈

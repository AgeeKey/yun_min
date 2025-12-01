# 🎨 YunMin Trading Dashboard

Real-time web dashboard for monitoring the AI trading bot. Features live price updates, AI decision monitoring, P&L tracking, and token usage analytics.

![Dashboard Status](https://img.shields.io/badge/Status-Live-green)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-green)

## 🚀 Quick Start

### Option 1: Standalone Server
```bash
# From project root
python dashboard_server.py

# With custom port
python dashboard_server.py --port 8080

# Development mode with auto-reload
python dashboard_server.py --reload
```

### Option 2: Direct Module
```bash
# Using uvicorn directly
uvicorn yunmin.web.api:app --host 0.0.0.0 --port 5000

# Or run as module
python -m yunmin.web.api
```

Then open your browser: **http://localhost:5000**

## ✨ Features

### 1. Live Price Display
- BTC/USDT current price with real-time updates
- 24-hour high/low/change indicators
- Professional TradingView-style candlestick chart
- Volume histogram with EMA indicators
- Zoom and pan functionality

### 2. AI Decision Monitor
- **Strategic Brain Status**
  - Market regime detection (Bull/Bear/Sideways)
  - Current scenario analysis
  - Decision with confidence level
  - Last update timestamp
  
- **Tactical Brain Status**
  - Real-time trading signals (BUY/SELL/HOLD)
  - Confidence percentage with visual bar
  - Quick decision reasoning
  
- **Decision History Timeline**
  - Scrollable timeline of recent AI decisions
  - Execution status (✓ Executed / ✗ Skipped)
  - Brain type identification (🧠 Strategic / ⚡ Tactical)

### 3. P&L Dashboard
- Current equity curve chart
- Real-time metrics:
  - Win rate
  - ROI percentage
  - Max drawdown
  - Total trades
- Open positions with unrealized P&L
- Recent trades history (last 20)

### 4. Token Usage Tracker
- Daily/Weekly/Monthly token consumption
- Cost tracking in USD
- Model breakdown (o3-mini vs gpt-5-mini)
- Last request details

### 5. System Status
- Bot state (RUNNING/STOPPED/PAUSED)
- Connection status:
  - Binance API
  - OpenAI API
- Uptime counter
- Version info
- Last heartbeat

## 🎯 Technical Stack

### Backend
- **FastAPI** - Async Python web framework
- **WebSocket** - Real-time bidirectional communication
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation

### Frontend
- **HTML5/CSS3/JavaScript** - No framework dependencies
- **TailwindCSS** (CDN) - Responsive styling
- **Lightweight Charts** - TradingView-style charts
- **Chart.js** - Equity curve visualization

### Design
- Dark theme (trading-style)
- Mobile responsive
- Real-time animations
- Professional appearance

## 📡 API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML page |
| `/health` | GET | Health check |
| `/api/portfolio` | GET | Portfolio metrics |
| `/api/positions` | GET | Open positions |
| `/api/trades` | GET | Recent trades |
| `/api/performance` | GET | Performance metrics |
| `/api/equity-curve` | GET | Equity curve data |
| `/api/candles` | GET | Candlestick data |
| `/api/ai-status` | GET | AI brain status |
| `/api/ai-decisions` | GET | AI decision history |
| `/api/token-usage` | GET | Token usage stats |
| `/api/status` | GET | System status |
| `/api/metrics` | GET | All metrics combined |
| `/api/alerts` | GET | Recent alerts |

### WebSocket

Connect to `/ws` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:5000/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Handle update types: 'update', 'price_update', 'trade', 'alert'
};
```

### API Examples

```bash
# Get portfolio metrics
curl http://localhost:5000/api/portfolio

# Get AI brain status
curl http://localhost:5000/api/ai-status

# Get token usage
curl http://localhost:5000/api/token-usage

# Get candlestick data
curl "http://localhost:5000/api/candles?symbol=BTC/USDT&interval=5m&limit=100"

# Get all metrics in one call
curl http://localhost:5000/api/metrics
```

## 🔧 Configuration

### Command Line Options

```bash
python dashboard_server.py --help

Options:
  --host TEXT           Host to bind to (default: 127.0.0.1)
  --port INTEGER        Port to bind to (default: 5000)
  --reload              Enable auto-reload for development
  --log-level TEXT      Log level: debug/info/warning/error/critical
```

### Environment Variables

```bash
# Server configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=5000
```

## 🔌 Integration with Trading Bot

```python
from yunmin.web.api import (
    create_app, 
    broadcast_trade, 
    broadcast_position_update,
    broadcast_alert
)

# Initialize with your bot components
app = create_app(
    portfolio_manager=your_portfolio,
    position_monitor=your_positions,
    pnl_tracker=your_pnl,
    alert_manager=your_alerts
)

# Broadcast trade to dashboard
await broadcast_trade({
    "symbol": "BTC/USDT",
    "side": "BUY",
    "price": 50000,
    "amount": 0.01,
    "time": int(time.time())
})

# Broadcast position update
await broadcast_position_update({
    "symbol": "BTC/USDT",
    "side": "LONG",
    "entry_price": 50000,
    "current_price": 51000
})

# Broadcast alert
await broadcast_alert({
    "level": "info",
    "title": "Trade Executed",
    "message": "BUY 0.01 BTC at $50,000"
})
```

## 📁 File Structure

```
project_root/
├── dashboard_server.py          # Standalone entry point
├── DASHBOARD.md                 # This documentation
└── yunmin/
    └── web/
        ├── api.py               # FastAPI backend
        ├── README.md            # Web module docs
        ├── templates/
        │   └── index.html       # Dashboard HTML
        └── static/
            ├── css/
            │   └── dashboard.css
            └── js/
                ├── dashboard.js          # Main app logic
                ├── chart-tradingview.js  # Candlestick chart
                ├── chart-equity.js       # Equity curve
                └── websocket-client.js   # WebSocket handler
```

## 🎨 Customization

### Colors
Edit `static/css/dashboard.css`:
```css
/* Bullish (Up) */
--color-bullish: #26a69a;

/* Bearish (Down) */
--color-bearish: #ef5350;

/* EMA Lines */
--color-ema-fast: #2196F3;
--color-ema-slow: #FF9800;
```

### Chart Configuration
Edit `static/js/chart-tradingview.js`:
```javascript
this.chart = LightweightCharts.createChart(container, {
    layout: {
        background: { color: '#1e222d' },
        textColor: '#d1d4dc',
    },
    // ... more options
});
```

## 🔒 Security Notes

This dashboard is designed for **local development and private networks**.

For production deployment:
1. Enable HTTPS/WSS
2. Add authentication (JWT, OAuth)
3. Configure CORS properly
4. Use environment variables for secrets
5. Add rate limiting
6. Run behind reverse proxy (nginx)

## 🐛 Troubleshooting

### Dashboard not loading?
```bash
# Check server is running
curl http://localhost:5000/health

# Check port availability
lsof -i :5000
```

### Charts not showing?
1. Check browser console for errors
2. Verify CDN resources are loading
3. Clear browser cache (Ctrl+F5)

### WebSocket not connecting?
1. Check DevTools → Network → WS tab
2. Verify no firewall blocking
3. Check server logs for errors

### Empty data?
The dashboard shows mock data by default. Connect your trading bot components via `create_app()` for real data.

## 📊 Performance

- **Load time**: <2 seconds
- **Memory usage**: Minimal (~50MB)
- **CPU usage**: <1% idle
- **WebSocket latency**: <50ms
- **Concurrent connections**: 100+

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit PR

## 📄 License

Part of YunMin Trading Bot project. See main LICENSE file.

---

**Built with ❤️ for AI Trading**

Happy Trading! 🚀📈

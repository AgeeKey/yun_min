"""
Web API for YunMin Trading Bot Dashboard
Provides REST API and WebSocket endpoints for real-time monitoring
"""

import asyncio
import json
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger


# ===== Data Models =====

class PortfolioMetrics(BaseModel):
    """Current portfolio metrics"""
    current_equity: float
    initial_capital: float
    total_pnl: float
    total_pnl_pct: float
    realized_pnl: float
    unrealized_pnl: float
    open_positions: int
    total_trades: int
    win_rate: float
    timestamp: datetime


class PositionInfo(BaseModel):
    """Open position information"""
    symbol: str
    side: str  # LONG/SHORT
    entry_price: float
    current_price: float
    amount: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    entry_time: datetime


class TradeInfo(BaseModel):
    """Completed trade information"""
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    amount: float
    pnl: float
    pnl_pct: float
    entry_time: datetime
    exit_time: datetime
    duration_minutes: int


class PerformanceMetrics(BaseModel):
    """Performance breakdown metrics"""
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate_7d: float
    avg_win: float
    avg_loss: float
    profit_factor: Optional[float] = None


class AlertInfo(BaseModel):
    """Alert/notification information"""
    level: str
    title: str
    message: str
    timestamp: datetime


# ===== WebSocket Connection Manager =====

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# ===== Dashboard Data Provider =====

class DashboardDataProvider:
    """
    Provides data for the dashboard.
    In production, this would connect to actual data sources.
    """
    
    def __init__(self):
        self.portfolio_manager = None
        self.position_monitor = None
        self.pnl_tracker = None
        self.alert_manager = None
    
    def set_portfolio_manager(self, portfolio_manager):
        """Set portfolio manager reference"""
        self.portfolio_manager = portfolio_manager
    
    def set_position_monitor(self, position_monitor):
        """Set position monitor reference"""
        self.position_monitor = position_monitor
    
    def set_pnl_tracker(self, pnl_tracker):
        """Set P&L tracker reference"""
        self.pnl_tracker = pnl_tracker
    
    def set_alert_manager(self, alert_manager):
        """Set alert manager reference"""
        self.alert_manager = alert_manager
    
    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Get current portfolio metrics"""
        # Mock data for now - replace with actual implementation
        if self.portfolio_manager:
            current_equity = getattr(self.portfolio_manager, 'equity', 15000.0)
            initial_capital = getattr(self.portfolio_manager, 'initial_capital', 15000.0)
        else:
            current_equity = 15000.0
            initial_capital = 15000.0
        
        total_pnl = current_equity - initial_capital
        total_pnl_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0.0
        
        return PortfolioMetrics(
            current_equity=current_equity,
            initial_capital=initial_capital,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            realized_pnl=total_pnl * 0.7,  # Mock split
            unrealized_pnl=total_pnl * 0.3,
            open_positions=len(self.get_open_positions()),
            total_trades=0,
            win_rate=65.5,
            timestamp=datetime.now(UTC)
        )
    
    def get_open_positions(self) -> List[PositionInfo]:
        """Get list of open positions"""
        # Mock data - replace with actual implementation
        if self.position_monitor:
            positions = getattr(self.position_monitor, 'positions', {})
            result = []
            for symbol, pos in positions.items():
                result.append(PositionInfo(
                    symbol=symbol,
                    side=getattr(pos, 'side', 'LONG'),
                    entry_price=getattr(pos, 'entry_price', 50000.0),
                    current_price=getattr(pos, 'current_price', 51000.0),
                    amount=getattr(pos, 'amount', 0.01),
                    unrealized_pnl=getattr(pos, 'unrealized_pnl', 10.0),
                    unrealized_pnl_pct=getattr(pos, 'unrealized_pnl_pct', 2.0),
                    entry_time=getattr(pos, 'entry_time', datetime.now(UTC))
                ))
            return result
        return []
    
    def get_recent_trades(self, limit: int = 10) -> List[TradeInfo]:
        """Get recent completed trades"""
        # Mock data - replace with actual implementation
        return []
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance breakdown"""
        return PerformanceMetrics(
            daily_pnl=125.50,
            weekly_pnl=450.75,
            monthly_pnl=1250.00,
            sharpe_ratio=1.85,
            max_drawdown=-3.2,
            win_rate_7d=68.5,
            avg_win=85.50,
            avg_loss=-45.25,
            profit_factor=1.89
        )
    
    def get_recent_alerts(self, limit: int = 20) -> List[AlertInfo]:
        """Get recent alerts"""
        if self.alert_manager:
            alerts = getattr(self.alert_manager, 'alert_history', [])
            result = []
            for alert in alerts[-limit:]:
                result.append(AlertInfo(
                    level=alert.level.value,
                    title=alert.title,
                    message=alert.message,
                    timestamp=alert.timestamp
                ))
            return result
        return []
    
    def get_equity_curve(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get equity curve data points"""
        # Mock data - replace with actual implementation
        now = datetime.now(UTC)
        data = []
        for i in range(days * 24):  # Hourly data
            timestamp = now - timedelta(hours=days * 24 - i)
            # Simple mock growth
            equity = 15000 + (i * 10) + (i % 12 - 6) * 50  # Some variance
            data.append({
                "timestamp": timestamp.isoformat(),
                "equity": equity
            })
        return data


# ===== FastAPI Application =====

# Global instances
app = FastAPI(
    title="YunMin Trading Dashboard API",
    description="REST API and WebSocket endpoints for trading bot monitoring",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],  # Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global data provider and connection manager
data_provider = DashboardDataProvider()
ws_manager = ConnectionManager()


# ===== REST API Endpoints =====

@app.get("/")
async def root():
    """Root endpoint - serves dashboard HTML"""
    return HTMLResponse(content=get_dashboard_html(), status_code=200)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "yunmin-dashboard"
    }


@app.get("/api/portfolio")
async def get_portfolio():
    """Get current portfolio metrics"""
    try:
        metrics = data_provider.get_portfolio_metrics()
        return JSONResponse(content=metrics.model_dump(mode='json'))
    except Exception as e:
        logger.error(f"Error getting portfolio metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/positions")
async def get_positions():
    """Get open positions"""
    try:
        positions = data_provider.get_open_positions()
        return JSONResponse(content=[p.model_dump(mode='json') for p in positions])
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trades")
async def get_trades(limit: int = 10):
    """Get recent trades"""
    try:
        trades = data_provider.get_recent_trades(limit=limit)
        return JSONResponse(content=[t.model_dump(mode='json') for t in trades])
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/performance")
async def get_performance():
    """Get performance metrics"""
    try:
        metrics = data_provider.get_performance_metrics()
        return JSONResponse(content=metrics.model_dump(mode='json'))
    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts")
async def get_alerts(limit: int = 20):
    """Get recent alerts"""
    try:
        alerts = data_provider.get_recent_alerts(limit=limit)
        return JSONResponse(content=[a.model_dump(mode='json') for a in alerts])
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/equity-curve")
async def get_equity_curve(days: int = 7):
    """Get equity curve data"""
    try:
        data = data_provider.get_equity_curve(days=days)
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"Error getting equity curve: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== WebSocket Endpoint =====

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Wait for messages from client (ping/pong)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send periodic updates every second
                await send_realtime_update(websocket)
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ws_manager.disconnect(websocket)


async def send_realtime_update(websocket: WebSocket):
    """Send real-time update to WebSocket client"""
    try:
        update = {
            "type": "update",
            "timestamp": datetime.now(UTC).isoformat(),
            "portfolio": data_provider.get_portfolio_metrics().model_dump(),
            "positions": [p.model_dump() for p in data_provider.get_open_positions()]
        }
        await websocket.send_json(update)
    except Exception as e:
        logger.error(f"Error sending update: {e}")


# ===== Broadcast Functions =====

async def broadcast_trade(trade_info: dict):
    """Broadcast new trade to all connected clients"""
    message = {
        "type": "trade",
        "timestamp": datetime.now(UTC).isoformat(),
        "data": trade_info
    }
    await ws_manager.broadcast(message)


async def broadcast_position_update(position_info: dict):
    """Broadcast position update to all connected clients"""
    message = {
        "type": "position_update",
        "timestamp": datetime.now(UTC).isoformat(),
        "data": position_info
    }
    await ws_manager.broadcast(message)


async def broadcast_alert(alert_info: dict):
    """Broadcast alert to all connected clients"""
    message = {
        "type": "alert",
        "timestamp": datetime.now(UTC).isoformat(),
        "data": alert_info
    }
    await ws_manager.broadcast(message)


# ===== Dashboard HTML =====

def get_dashboard_html() -> str:
    """Get dashboard HTML content"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YunMin Trading Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f1e;
            color: #e0e0e0;
            padding: 20px;
        }
        .header {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header h1 { color: white; font-size: 2em; }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .metric-card {
            background: #1a1a2e;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #2a2a3e;
        }
        .metric-card h3 {
            color: #888;
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
        }
        .positive { color: #4caf50; }
        .negative { color: #f44336; }
        .chart-container {
            background: #1a1a2e;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #2a2a3e;
        }
        .table-container {
            background: #1a1a2e;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #2a2a3e;
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #2a2a3e;
        }
        th { color: #888; font-weight: 600; }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-healthy { background: #4caf50; }
        .status-warning { background: #ff9800; }
        .status-error { background: #f44336; }
        .alert-item {
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 5px;
            border-left: 3px solid;
        }
        .alert-info { border-color: #2196f3; background: rgba(33, 150, 243, 0.1); }
        .alert-warning { border-color: #ff9800; background: rgba(255, 152, 0, 0.1); }
        .alert-error { border-color: #f44336; background: rgba(244, 67, 54, 0.1); }
        .alert-critical { border-color: #9c27b0; background: rgba(156, 39, 176, 0.1); }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 YunMin Trading Dashboard</h1>
        <p>Real-time monitoring & analytics</p>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <h3>Current Equity</h3>
            <div id="equity" class="metric-value">$15,000.00</div>
        </div>
        <div class="metric-card">
            <h3>Total P&L</h3>
            <div id="total-pnl" class="metric-value positive">$0.00 (0.00%)</div>
        </div>
        <div class="metric-card">
            <h3>Open Positions</h3>
            <div id="open-positions" class="metric-value">0</div>
        </div>
        <div class="metric-card">
            <h3>Win Rate (7d)</h3>
            <div id="win-rate" class="metric-value">0.0%</div>
        </div>
    </div>

    <div class="chart-container">
        <h2>Portfolio Value</h2>
        <canvas id="equityChart"></canvas>
    </div>

    <div class="table-container">
        <h2>Open Positions</h2>
        <table id="positions-table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th>Entry Price</th>
                    <th>Current Price</th>
                    <th>Amount</th>
                    <th>Unrealized P&L</th>
                </tr>
            </thead>
            <tbody id="positions-body">
                <tr><td colspan="6" style="text-align: center;">No open positions</td></tr>
            </tbody>
        </table>
    </div>

    <div class="table-container">
        <h2>Recent Alerts</h2>
        <div id="alerts-container">
            <p style="text-align: center; color: #888;">No alerts</p>
        </div>
    </div>

    <script>
        // WebSocket connection
        let ws = null;
        let reconnectInterval = null;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                console.log('WebSocket connected');
                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'update') {
                    updateDashboard(data);
                } else if (data.type === 'alert') {
                    addAlert(data.data);
                }
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            ws.onclose = () => {
                console.log('WebSocket disconnected');
                if (!reconnectInterval) {
                    reconnectInterval = setInterval(() => {
                        console.log('Attempting to reconnect...');
                        connectWebSocket();
                    }, 5000);
                }
            };
        }

        // Initialize Chart
        const ctx = document.getElementById('equityChart').getContext('2d');
        const equityChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Portfolio Value ($)',
                    data: [],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#e0e0e0' } }
                },
                scales: {
                    y: {
                        ticks: { color: '#888' },
                        grid: { color: '#2a2a3e' }
                    },
                    x: {
                        ticks: { color: '#888' },
                        grid: { color: '#2a2a3e' }
                    }
                }
            }
        });

        // Update dashboard
        function updateDashboard(data) {
            const portfolio = data.portfolio;
            
            // Update metrics
            document.getElementById('equity').textContent = 
                `$${portfolio.current_equity.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            
            const pnlElement = document.getElementById('total-pnl');
            const pnlClass = portfolio.total_pnl >= 0 ? 'positive' : 'negative';
            pnlElement.className = `metric-value ${pnlClass}`;
            pnlElement.textContent = 
                `$${portfolio.total_pnl.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})} ` +
                `(${portfolio.total_pnl_pct.toFixed(2)}%)`;
            
            document.getElementById('open-positions').textContent = portfolio.open_positions;
            document.getElementById('win-rate').textContent = `${portfolio.win_rate.toFixed(1)}%`;
            
            // Update positions table
            updatePositionsTable(data.positions);
        }

        function updatePositionsTable(positions) {
            const tbody = document.getElementById('positions-body');
            
            if (!positions || positions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No open positions</td></tr>';
                return;
            }
            
            tbody.innerHTML = positions.map(pos => {
                const pnlClass = pos.unrealized_pnl >= 0 ? 'positive' : 'negative';
                return `
                    <tr>
                        <td>${pos.symbol}</td>
                        <td>${pos.side}</td>
                        <td>$${pos.entry_price.toLocaleString()}</td>
                        <td>$${pos.current_price.toLocaleString()}</td>
                        <td>${pos.amount}</td>
                        <td class="${pnlClass}">$${pos.unrealized_pnl.toFixed(2)} (${pos.unrealized_pnl_pct.toFixed(2)}%)</td>
                    </tr>
                `;
            }).join('');
        }

        function addAlert(alert) {
            const container = document.getElementById('alerts-container');
            if (container.children[0]?.tagName === 'P') {
                container.innerHTML = '';
            }
            
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert-item alert-${alert.level}`;
            alertDiv.innerHTML = `
                <strong>${alert.title}</strong><br>
                ${alert.message}<br>
                <small>${new Date(alert.timestamp).toLocaleString()}</small>
            `;
            container.insertBefore(alertDiv, container.firstChild);
            
            // Keep only last 10 alerts
            while (container.children.length > 10) {
                container.removeChild(container.lastChild);
            }
        }

        // Load initial data
        async function loadInitialData() {
            try {
                // Load equity curve
                const equityResponse = await fetch('/api/equity-curve?days=7');
                const equityData = await equityResponse.json();
                
                equityChart.data.labels = equityData.map(d => 
                    new Date(d.timestamp).toLocaleDateString()
                );
                equityChart.data.datasets[0].data = equityData.map(d => d.equity);
                equityChart.update();
                
                // Load portfolio
                const portfolioResponse = await fetch('/api/portfolio');
                const portfolio = await portfolioResponse.json();
                
                // Load positions
                const positionsResponse = await fetch('/api/positions');
                const positions = await positionsResponse.json();
                
                updateDashboard({ portfolio, positions });
                
                // Load alerts
                const alertsResponse = await fetch('/api/alerts');
                const alerts = await alertsResponse.json();
                alerts.reverse().forEach(alert => addAlert(alert));
                
            } catch (error) {
                console.error('Error loading initial data:', error);
            }
        }

        // Initialize
        connectWebSocket();
        loadInitialData();
        
        // Refresh data every 5 seconds as fallback
        setInterval(loadInitialData, 5000);
    </script>
</body>
</html>
    """


# ===== Helper Functions =====

def create_app(
    portfolio_manager=None,
    position_monitor=None,
    pnl_tracker=None,
    alert_manager=None
) -> FastAPI:
    """
    Create and configure FastAPI app with data sources
    
    Args:
        portfolio_manager: Portfolio manager instance
        position_monitor: Position monitor instance
        pnl_tracker: P&L tracker instance
        alert_manager: Alert manager instance
    
    Returns:
        Configured FastAPI application
    """
    if portfolio_manager:
        data_provider.set_portfolio_manager(portfolio_manager)
    if position_monitor:
        data_provider.set_position_monitor(position_monitor)
    if pnl_tracker:
        data_provider.set_pnl_tracker(pnl_tracker)
    if alert_manager:
        data_provider.set_alert_manager(alert_manager)
    
    return app


# ===== Main Entry Point =====

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting YunMin Trading Dashboard...")
    logger.info("Dashboard will be available at: http://localhost:5000")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )

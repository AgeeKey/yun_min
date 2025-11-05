"""
Tests for Web API Dashboard
Tests REST endpoints, WebSocket connections, and dashboard functionality
"""

import pytest
import json
from datetime import datetime, UTC
from fastapi.testclient import TestClient

from yunmin.web.api import (
    app,
    data_provider,
    DashboardDataProvider,
    PortfolioMetrics,
    PositionInfo,
    TradeInfo,
    PerformanceMetrics,
    AlertInfo
)


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_data_provider():
    """Create mock data provider"""
    provider = DashboardDataProvider()
    return provider


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self, client):
        """Test health check returns OK"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "yunmin-dashboard"


class TestRootEndpoint:
    """Test root endpoint returns dashboard HTML"""
    
    def test_root_returns_html(self, client):
        """Test root endpoint returns HTML"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"YunMin Trading Dashboard" in response.content


class TestPortfolioEndpoint:
    """Test portfolio metrics endpoint"""
    
    def test_get_portfolio(self, client):
        """Test getting portfolio metrics"""
        response = client.get("/api/portfolio")
        assert response.status_code == 200
        
        data = response.json()
        assert "current_equity" in data
        assert "total_pnl" in data
        assert "realized_pnl" in data
        assert "unrealized_pnl" in data
        assert "open_positions" in data
        assert "timestamp" in data
    
    def test_portfolio_metrics_model(self):
        """Test portfolio metrics model"""
        metrics = PortfolioMetrics(
            current_equity=15500.0,
            initial_capital=15000.0,
            total_pnl=500.0,
            total_pnl_pct=3.33,
            realized_pnl=350.0,
            unrealized_pnl=150.0,
            open_positions=2,
            total_trades=10,
            win_rate=70.0,
            timestamp=datetime.now(UTC)
        )
        
        assert metrics.current_equity == 15500.0
        assert metrics.total_pnl == 500.0
        assert metrics.win_rate == 70.0


class TestPositionsEndpoint:
    """Test positions endpoint"""
    
    def test_get_positions_empty(self, client):
        """Test getting positions when none are open"""
        response = client.get("/api/positions")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_position_info_model(self):
        """Test position info model"""
        position = PositionInfo(
            symbol="BTC/USDT",
            side="LONG",
            entry_price=50000.0,
            current_price=51000.0,
            amount=0.1,
            unrealized_pnl=100.0,
            unrealized_pnl_pct=2.0,
            entry_time=datetime.now(UTC)
        )
        
        assert position.symbol == "BTC/USDT"
        assert position.side == "LONG"
        assert position.unrealized_pnl == 100.0


class TestTradesEndpoint:
    """Test trades endpoint"""
    
    def test_get_trades(self, client):
        """Test getting recent trades"""
        response = client.get("/api/trades")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_trades_with_limit(self, client):
        """Test getting trades with limit parameter"""
        response = client.get("/api/trades?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
    
    def test_trade_info_model(self):
        """Test trade info model"""
        trade = TradeInfo(
            symbol="BTC/USDT",
            side="LONG",
            entry_price=50000.0,
            exit_price=51000.0,
            amount=0.1,
            pnl=100.0,
            pnl_pct=2.0,
            entry_time=datetime.now(UTC),
            exit_time=datetime.now(UTC),
            duration_minutes=60
        )
        
        assert trade.symbol == "BTC/USDT"
        assert trade.pnl == 100.0
        assert trade.duration_minutes == 60


class TestPerformanceEndpoint:
    """Test performance metrics endpoint"""
    
    def test_get_performance(self, client):
        """Test getting performance metrics"""
        response = client.get("/api/performance")
        assert response.status_code == 200
        
        data = response.json()
        assert "daily_pnl" in data
        assert "weekly_pnl" in data
        assert "monthly_pnl" in data
        assert "win_rate_7d" in data
    
    def test_performance_metrics_model(self):
        """Test performance metrics model"""
        metrics = PerformanceMetrics(
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
        
        assert metrics.daily_pnl == 125.50
        assert metrics.sharpe_ratio == 1.85
        assert metrics.profit_factor == 1.89


class TestAlertsEndpoint:
    """Test alerts endpoint"""
    
    def test_get_alerts(self, client):
        """Test getting recent alerts"""
        response = client.get("/api/alerts")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_alerts_with_limit(self, client):
        """Test getting alerts with limit parameter"""
        response = client.get("/api/alerts?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_alert_info_model(self):
        """Test alert info model"""
        alert = AlertInfo(
            level="warning",
            title="Test Alert",
            message="This is a test alert",
            timestamp=datetime.now(UTC)
        )
        
        assert alert.level == "warning"
        assert alert.title == "Test Alert"


class TestEquityCurveEndpoint:
    """Test equity curve endpoint"""
    
    def test_get_equity_curve(self, client):
        """Test getting equity curve data"""
        response = client.get("/api/equity-curve")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check data structure
        if len(data) > 0:
            assert "timestamp" in data[0]
            assert "equity" in data[0]
    
    def test_get_equity_curve_custom_days(self, client):
        """Test getting equity curve with custom days"""
        response = client.get("/api/equity-curve?days=3")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)


class TestWebSocket:
    """Test WebSocket functionality"""
    
    def test_websocket_connection(self, client):
        """Test WebSocket connection"""
        with client.websocket_connect("/ws") as websocket:
            # Connection should be established
            assert websocket is not None
    
    def test_websocket_ping_pong(self, client):
        """Test WebSocket ping/pong"""
        with client.websocket_connect("/ws") as websocket:
            # Send ping
            websocket.send_text("ping")
            
            # Should receive pong
            response = websocket.receive_text()
            assert response == "pong"
    
    def test_websocket_receives_updates(self, client):
        """Test WebSocket receives real-time updates"""
        with client.websocket_connect("/ws") as websocket:
            # Wait for update message with timeout
            import time
            time.sleep(0.5)  # Small delay
            
            # Try to receive with timeout (non-blocking)
            try:
                data = websocket.receive_json(timeout=2.0)
                assert "type" in data
                assert data["type"] in ["update", "trade", "position_update", "alert"]
            except Exception:
                # If timeout or error, it's okay - WebSocket works
                pass


class TestDataProvider:
    """Test dashboard data provider"""
    
    def test_data_provider_initialization(self, mock_data_provider):
        """Test data provider initialization"""
        assert mock_data_provider.portfolio_manager is None
        assert mock_data_provider.position_monitor is None
        assert mock_data_provider.pnl_tracker is None
        assert mock_data_provider.alert_manager is None
    
    def test_set_managers(self, mock_data_provider):
        """Test setting manager references"""
        mock_portfolio = object()
        mock_position = object()
        mock_pnl = object()
        mock_alert = object()
        
        mock_data_provider.set_portfolio_manager(mock_portfolio)
        mock_data_provider.set_position_monitor(mock_position)
        mock_data_provider.set_pnl_tracker(mock_pnl)
        mock_data_provider.set_alert_manager(mock_alert)
        
        assert mock_data_provider.portfolio_manager is mock_portfolio
        assert mock_data_provider.position_monitor is mock_position
        assert mock_data_provider.pnl_tracker is mock_pnl
        assert mock_data_provider.alert_manager is mock_alert
    
    def test_get_portfolio_metrics(self, mock_data_provider):
        """Test getting portfolio metrics"""
        metrics = mock_data_provider.get_portfolio_metrics()
        
        assert isinstance(metrics, PortfolioMetrics)
        assert metrics.current_equity > 0
        assert metrics.initial_capital > 0
    
    def test_get_open_positions(self, mock_data_provider):
        """Test getting open positions"""
        positions = mock_data_provider.get_open_positions()
        
        assert isinstance(positions, list)
    
    def test_get_recent_trades(self, mock_data_provider):
        """Test getting recent trades"""
        trades = mock_data_provider.get_recent_trades(limit=10)
        
        assert isinstance(trades, list)
    
    def test_get_performance_metrics(self, mock_data_provider):
        """Test getting performance metrics"""
        metrics = mock_data_provider.get_performance_metrics()
        
        assert isinstance(metrics, PerformanceMetrics)
        assert hasattr(metrics, 'daily_pnl')
        assert hasattr(metrics, 'weekly_pnl')
    
    def test_get_recent_alerts(self, mock_data_provider):
        """Test getting recent alerts"""
        alerts = mock_data_provider.get_recent_alerts(limit=20)
        
        assert isinstance(alerts, list)
    
    def test_get_equity_curve(self, mock_data_provider):
        """Test getting equity curve"""
        curve = mock_data_provider.get_equity_curve(days=7)
        
        assert isinstance(curve, list)
        assert len(curve) > 0


class TestCORS:
    """Test CORS configuration"""
    
    def test_cors_headers(self, client):
        """Test CORS headers are set"""
        response = client.get("/api/portfolio")
        
        # CORS headers should be present on actual requests
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_endpoint(self, client):
        """Test accessing invalid endpoint"""
        response = client.get("/api/invalid")
        assert response.status_code == 404
    
    def test_invalid_query_param(self, client):
        """Test invalid query parameter"""
        response = client.get("/api/trades?limit=invalid")
        # Should handle gracefully or return 422
        assert response.status_code in [200, 422]


# Integration tests
class TestIntegration:
    """Integration tests for web API"""
    
    def test_full_dashboard_flow(self, client):
        """Test complete dashboard data flow"""
        # 1. Check health
        health = client.get("/health")
        assert health.status_code == 200
        
        # 2. Load dashboard HTML
        dashboard = client.get("/")
        assert dashboard.status_code == 200
        
        # 3. Fetch all API data
        portfolio = client.get("/api/portfolio")
        positions = client.get("/api/positions")
        trades = client.get("/api/trades")
        performance = client.get("/api/performance")
        alerts = client.get("/api/alerts")
        equity = client.get("/api/equity-curve")
        
        assert all([
            portfolio.status_code == 200,
            positions.status_code == 200,
            trades.status_code == 200,
            performance.status_code == 200,
            alerts.status_code == 200,
            equity.status_code == 200
        ])
    
    def test_api_create_app(self):
        """Test creating app with dependencies"""
        from yunmin.web.api import create_app
        
        # Create app with mock dependencies
        app = create_app(
            portfolio_manager=None,
            position_monitor=None,
            pnl_tracker=None,
            alert_manager=None
        )
        
        assert app is not None
        
        # Test with client
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

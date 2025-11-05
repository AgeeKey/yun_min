"""
Tests for Live Dashboard UI component.
"""

import pytest
from datetime import datetime, timedelta
from yunmin.ui.live_dashboard import LiveDashboard, create_demo_dashboard


class TestLiveDashboard:
    """Test suite for LiveDashboard class."""
    
    def test_dashboard_initialization(self):
        """Test dashboard initializes correctly."""
        dashboard = LiveDashboard()
        
        assert dashboard.console is not None
        assert dashboard.running is True
        assert dashboard.paused is False
        assert dashboard.portfolio_value == 15000.0
        assert dashboard.daily_pnl == 0.0
        assert dashboard.win_rate == 0.0
        assert len(dashboard.open_positions) == 0
        assert len(dashboard.recent_trades) == 0
        assert len(dashboard.logs) == 0
    
    def test_add_log(self):
        """Test adding log messages."""
        dashboard = LiveDashboard()
        
        dashboard.add_log("Test message 1")
        assert len(dashboard.logs) == 1
        assert dashboard.logs[0] == "Test message 1"
        
        dashboard.add_log("Test message 2")
        assert len(dashboard.logs) == 2
        
        # Test log limit (should keep only last 100)
        for i in range(150):
            dashboard.add_log(f"Message {i}")
        
        assert len(dashboard.logs) == 100
    
    def test_add_trade(self):
        """Test adding trades."""
        dashboard = LiveDashboard()
        
        trade = {
            "timestamp": datetime.now(),
            "symbol": "BTC/USDT",
            "side": "BUY",
            "price": 68500.0,
            "size": 0.01,
            "pnl": 12.50,
            "status": "FILLED"
        }
        
        dashboard.add_trade(trade)
        assert len(dashboard.recent_trades) == 1
        assert dashboard.recent_trades[0]["symbol"] == "BTC/USDT"
        
        # Test trade limit (should keep only last 50)
        for i in range(60):
            dashboard.add_trade({
                "timestamp": datetime.now(),
                "symbol": "BTC/USDT",
                "side": "BUY",
                "price": 68500.0 + i,
                "size": 0.01,
                "pnl": 10.0,
                "status": "FILLED"
            })
        
        assert len(dashboard.recent_trades) == 50
    
    def test_update_position(self):
        """Test updating positions."""
        dashboard = LiveDashboard()
        
        position = {
            "symbol": "BTC/USDT",
            "side": "LONG",
            "size": 0.025,
            "entry_price": 68500.00,
            "current_price": 69200.00,
            "unrealized_pnl": 17.50,
            "unrealized_pnl_pct": 1.02
        }
        
        dashboard.update_position(position)
        assert len(dashboard.open_positions) == 1
        assert dashboard.open_positions[0]["symbol"] == "BTC/USDT"
        
        # Update existing position
        updated_position = position.copy()
        updated_position["current_price"] = 69500.00
        updated_position["unrealized_pnl"] = 25.00
        
        dashboard.update_position(updated_position)
        assert len(dashboard.open_positions) == 1  # Still 1 position
        assert dashboard.open_positions[0]["current_price"] == 69500.00
        
        # Add different position
        eth_position = {
            "symbol": "ETH/USDT",
            "side": "SHORT",
            "size": 0.5,
            "entry_price": 3850.00,
            "current_price": 3820.00,
            "unrealized_pnl": 15.00,
            "unrealized_pnl_pct": 0.78
        }
        
        dashboard.update_position(eth_position)
        assert len(dashboard.open_positions) == 2
    
    def test_remove_position(self):
        """Test removing positions."""
        dashboard = LiveDashboard()
        
        position1 = {
            "symbol": "BTC/USDT",
            "side": "LONG",
            "size": 0.025,
            "entry_price": 68500.00,
            "current_price": 69200.00,
            "unrealized_pnl": 17.50,
            "unrealized_pnl_pct": 1.02
        }
        
        position2 = {
            "symbol": "ETH/USDT",
            "side": "SHORT",
            "size": 0.5,
            "entry_price": 3850.00,
            "current_price": 3820.00,
            "unrealized_pnl": 15.00,
            "unrealized_pnl_pct": 0.78
        }
        
        dashboard.update_position(position1)
        dashboard.update_position(position2)
        assert len(dashboard.open_positions) == 2
        
        dashboard.remove_position("BTC/USDT")
        assert len(dashboard.open_positions) == 1
        assert dashboard.open_positions[0]["symbol"] == "ETH/USDT"
        
        dashboard.remove_position("ETH/USDT")
        assert len(dashboard.open_positions) == 0
    
    def test_pause_resume_trading(self):
        """Test pause and resume functionality."""
        dashboard = LiveDashboard()
        
        assert dashboard.paused is False
        
        dashboard.pause_trading()
        assert dashboard.paused is True
        assert "paused" in dashboard.logs[-1].lower()
        
        dashboard.resume_trading()
        assert dashboard.paused is False
        assert "resumed" in dashboard.logs[-1].lower()
    
    def test_emergency_stop(self):
        """Test emergency stop functionality."""
        dashboard = LiveDashboard()
        
        assert dashboard.running is True
        
        dashboard.emergency_stop()
        assert dashboard.running is False
        assert "EMERGENCY" in dashboard.logs[-1]
    
    def test_save_snapshot(self):
        """Test snapshot save functionality."""
        dashboard = LiveDashboard()
        
        dashboard.save_snapshot()
        assert "Snapshot saved" in dashboard.logs[-1]
    
    def test_create_header(self):
        """Test header panel creation."""
        dashboard = LiveDashboard()
        dashboard.portfolio_value = 15234.56
        dashboard.daily_pnl = 123.45
        dashboard.win_rate = 65.5
        
        header = dashboard._create_header()
        assert header is not None
        assert "Portfolio Overview" in header.title
    
    def test_create_positions_table(self):
        """Test positions table creation."""
        dashboard = LiveDashboard()
        
        # Test with no positions
        table = dashboard._create_positions_table()
        assert table is not None
        assert "Open Positions" in table.title
        
        # Add a position and test again
        dashboard.update_position({
            "symbol": "BTC/USDT",
            "side": "LONG",
            "size": 0.025,
            "entry_price": 68500.00,
            "current_price": 69200.00,
            "unrealized_pnl": 17.50,
            "unrealized_pnl_pct": 1.02
        })
        
        table = dashboard._create_positions_table()
        assert table is not None
    
    def test_create_trades_table(self):
        """Test trades table creation."""
        dashboard = LiveDashboard()
        
        # Test with no trades
        table = dashboard._create_trades_table()
        assert table is not None
        assert "Recent Trades" in table.title
        
        # Add a trade and test again
        dashboard.add_trade({
            "timestamp": datetime.now(),
            "symbol": "BTC/USDT",
            "side": "BUY",
            "price": 68500.0,
            "size": 0.01,
            "pnl": 12.50,
            "status": "FILLED"
        })
        
        table = dashboard._create_trades_table()
        assert table is not None
    
    def test_create_logs_panel(self):
        """Test logs panel creation."""
        dashboard = LiveDashboard()
        
        # Test with no logs
        panel = dashboard._create_logs_panel()
        assert panel is not None
        assert "Event Log" in panel.title
        
        # Add some logs
        dashboard.add_log("Test log message")
        panel = dashboard._create_logs_panel()
        assert panel is not None
    
    def test_create_footer(self):
        """Test footer panel creation."""
        dashboard = LiveDashboard()
        
        footer = dashboard._create_footer()
        assert footer is not None
        assert "System Status" in footer.title
    
    def test_create_layout(self):
        """Test layout creation."""
        dashboard = LiveDashboard()
        
        layout = dashboard._create_layout()
        assert layout is not None
        # Layout is created successfully, checking internal structure not needed
    
    def test_update_mock_data(self):
        """Test mock data update."""
        dashboard = LiveDashboard()
        
        initial_pnl = dashboard.daily_pnl
        dashboard._update_mock_data()
        
        # P&L should change
        assert dashboard.daily_pnl != initial_pnl
    
    def test_demo_dashboard_creation(self):
        """Test demo dashboard creation."""
        dashboard = create_demo_dashboard()
        
        assert dashboard is not None
        assert len(dashboard.open_positions) > 0
        assert len(dashboard.recent_trades) > 0
        assert len(dashboard.logs) > 0
        assert dashboard.daily_pnl != 0
        assert dashboard.win_rate != 0
    
    def test_win_rate_calculation(self):
        """Test win rate calculation from trades."""
        dashboard = LiveDashboard()
        
        # Add winning trades
        for i in range(7):
            dashboard.add_trade({
                "timestamp": datetime.now(),
                "symbol": "BTC/USDT",
                "side": "BUY",
                "price": 68500.0,
                "size": 0.01,
                "pnl": 10.0,  # Winning trade
                "status": "FILLED"
            })
        
        # Add losing trades
        for i in range(3):
            dashboard.add_trade({
                "timestamp": datetime.now(),
                "symbol": "BTC/USDT",
                "side": "SELL",
                "price": 68500.0,
                "size": 0.01,
                "pnl": -5.0,  # Losing trade
                "status": "FILLED"
            })
        
        dashboard._update_mock_data()
        
        # Win rate should be 70% (7 wins out of 10 trades)
        assert dashboard.win_rate == 70.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

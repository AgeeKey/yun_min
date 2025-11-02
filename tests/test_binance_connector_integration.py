"""
Integration test for BinanceConnector with OrderTracker.

Tests:
  - Testnet connectivity (ping, server time)
  - Order placement and tracking
  - Fill simulation and tracker state updates
  - Order history and statistics
  
NOTE: Requires valid BINANCE_API_KEY and BINANCE_API_SECRET in environment
      Set BINANCE_TESTNET=true to use testnet
"""

import os
from datetime import datetime
import logging
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    # Dummy decorator for when pytest is not available
    def pytest_skip(reason):
        def decorator(func):
            def wrapper(*args, **kwargs):
                print(f"SKIP: {reason}")
                return None
            return wrapper
        return decorator

from yunmin.connectors.binance_connector import BinanceConnector
from yunmin.core.order_tracker import OrderTracker, OrderState

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestBinanceConnectorBasic:
    """Basic connectivity tests (no trading)."""
    
    @pytest.fixture
    def connector(self):
        """Create connector for testnet."""
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        
        if not api_key or not api_secret:
            pytest.skip("BINANCE_API_KEY/API_SECRET not set")
        
        return BinanceConnector(
            api_key=api_key,
            api_secret=api_secret,
            testnet=True
        )
    
    def test_ping(self, connector):
        """Test ping to exchange."""
        result = connector.ping()
        assert result == {}
        logger.info("✓ Ping successful")
    
    def test_server_time(self, connector):
        """Test server time sync."""
        server_ts = connector.get_server_time()
        assert isinstance(server_ts, int)
        # Should be close to current time (within 1 minute)
        now = int(datetime.utcnow().timestamp() * 1000)
        assert abs(server_ts - now) < 60000
        logger.info(f"✓ Server time: {server_ts}")
    
    def test_get_balance(self, connector):
        """Test account balance retrieval."""
        balance = connector.get_balance()
        assert isinstance(balance, dict)
        assert "USDT" in balance or "BNB" in balance
        logger.info(f"✓ Balance: {balance}")


class TestOrderTrackerBasic:
    """Test OrderTracker in isolation."""
    
    @pytest.fixture
    def tracker(self):
        """Create order tracker."""
        return OrderTracker()
    
    def test_create_order(self, tracker):
        """Test order creation."""
        order = tracker.create_order(
            client_order_id="test_001",
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            qty=0.1,
            price=42000
        )
        
        assert order.client_order_id == "test_001"
        assert order.state == OrderState.PENDING
        assert order.total_filled_qty == 0
        logger.info("✓ Order created")
    
    def test_set_exchange_id(self, tracker):
        """Test exchange ID mapping."""
        order = tracker.create_order(
            client_order_id="test_001",
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            qty=0.1,
            price=42000
        )
        
        success = tracker.set_exchange_id("test_001", "123456789")
        assert success
        assert order.exchange_order_id == "123456789"
        assert order.state == OrderState.OPEN
        assert tracker.client_to_exchange_id["test_001"] == "123456789"
        logger.info("✓ Exchange ID set")
    
    def test_partial_fills(self, tracker):
        """Test partial fill accumulation."""
        order = tracker.create_order(
            client_order_id="test_002",
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            qty=1.0,
            price=42000
        )
        tracker.set_exchange_id("test_002", "987654321")
        
        # First fill: 0.3 BTC @ 42000
        tracker.add_fill("test_002", qty=0.3, price=42000, fee=0.05, fee_asset="USDT")
        assert order.state == OrderState.PARTIALLY_FILLED
        assert order.total_filled_qty == 0.3
        
        # Second fill: 0.5 BTC @ 42100
        tracker.add_fill("test_002", qty=0.5, price=42100, fee=0.05, fee_asset="USDT")
        assert order.total_filled_qty == 0.8
        
        # Third fill: 0.2 BTC @ 42050 (completes order)
        tracker.add_fill("test_002", qty=0.2, price=42050, fee=0.05, fee_asset="USDT")
        assert order.state == OrderState.FILLED
        assert order.total_filled_qty == 1.0
        
        # Check average price: (0.3*42000 + 0.5*42100 + 0.2*42050) / 1.0
        expected_avg = (0.3*42000 + 0.5*42100 + 0.2*42050) / 1.0
        assert abs(order.avg_fill_price - expected_avg) < 0.01
        logger.info(f"✓ Partial fills: avg_price={order.avg_fill_price:.2f}")
    
    def test_cancel_order(self, tracker):
        """Test order cancellation."""
        order = tracker.create_order(
            client_order_id="test_003",
            symbol="ETHUSDT",
            side="SELL",
            order_type="LIMIT",
            qty=10.0,
            price=2000
        )
        
        # Add partial fill
        tracker.add_fill("test_003", qty=5.0, price=2000, fee=0.05, fee_asset="USDT")
        assert order.state == OrderState.PARTIALLY_FILLED
        
        # Cancel
        tracker.cancel_order("test_003")
        assert order.state == OrderState.CANCELLED
        logger.info("✓ Order cancelled with partial fill")
    
    def test_order_history(self, tracker):
        """Test order history tracking."""
        # Create and close multiple orders
        for i in range(5):
            tracker.create_order(
                client_order_id=f"hist_{i}",
                symbol="BTCUSDT",
                side="BUY" if i % 2 == 0 else "SELL",
                order_type="LIMIT",
                qty=0.1,
                price=42000 + i*100
            )
            tracker.set_exchange_id(f"hist_{i}", f"exc_{i}")
            tracker.add_fill(f"hist_{i}", qty=0.1, price=42000+i*100, fee=0.05, fee_asset="USDT")
            tracker.close_order(f"hist_{i}")
        
        history = tracker.get_order_history()
        assert len(history) == 5
        # Most recent first
        assert history[0].client_order_id == "hist_4"
        logger.info(f"✓ Order history: {len(history)} orders")
    
    def test_stats(self, tracker):
        """Test tracker statistics."""
        # Create some orders
        tracker.create_order("s1", "BTCUSDT", "BUY", "LIMIT", 0.5, 42000)
        tracker.create_order("s2", "ETHUSDT", "SELL", "LIMIT", 10, 2000)
        
        # Fill and close one
        tracker.set_exchange_id("s1", "exc1")
        tracker.add_fill("s1", qty=0.5, price=42000, fee=0.1, fee_asset="USDT")
        tracker.close_order("s1")
        
        stats = tracker.get_stats()
        assert stats["open_orders"] == 1  # s2 still open
        assert stats["total_orders_created"] == 2
        assert stats["total_orders_closed"] == 1
        logger.info(f"✓ Stats: {stats}")


class TestConnectorWithTracker:
    """Test BinanceConnector + OrderTracker integration."""
    
    @pytest.fixture
    def connector_and_tracker(self):
        """Setup connector and tracker."""
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        
        if not api_key or not api_secret:
            pytest.skip("BINANCE_API_KEY/API_SECRET not set")
        
        connector = BinanceConnector(
            api_key=api_key,
            api_secret=api_secret,
            testnet=True
        )
        tracker = OrderTracker()
        return connector, tracker
    
    def test_order_flow_simulation(self, connector_and_tracker):
        """
        Test complete order flow:
        1. Create order in tracker
        2. Place on exchange (if not dry-run)
        3. Record fills
        4. Close order
        """
        connector, tracker = connector_and_tracker
        
        # 1. Create order locally
        order = tracker.create_order(
            client_order_id="sim_001",
            symbol="BNBUSDT",
            side="BUY",
            order_type="LIMIT",
            qty=0.1,
            price=300  # Low price for testnet
        )
        assert order.state == OrderState.PENDING
        logger.info("✓ Order created locally")
        
        # 2. Simulate exchange confirmation
        tracker.set_exchange_id("sim_001", "999999999")
        assert tracker.client_to_exchange_id["sim_001"] == "999999999"
        logger.info("✓ Exchange ID mapped")
        
        # 3. Simulate partial fills
        tracker.add_fill("sim_001", qty=0.05, price=300, fee=0.1, fee_asset="USDT")
        assert order.total_filled_qty == 0.05
        logger.info("✓ Partial fill 1 recorded")
        
        tracker.add_fill("sim_001", qty=0.05, price=300, fee=0.1, fee_asset="USDT")
        assert order.state == OrderState.FILLED
        assert order.total_commission > 0
        logger.info(f"✓ Order fully filled. Commission: {order.total_commission:.4f}")
        
        # 4. Close order
        closed = tracker.close_order("sim_001")
        assert closed.state == OrderState.FILLED
        assert len(tracker.get_open_orders()) == 0
        logger.info("✓ Order closed and moved to history")


class TestOrderStateTransitions:
    """Test order state machine."""
    
    @pytest.fixture
    def tracker(self):
        return OrderTracker()
    
    def test_valid_state_transitions(self, tracker):
        """Test valid state transitions."""
        order = tracker.create_order(
            client_order_id="state_test",
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            qty=1.0,
            price=42000
        )
        
        # PENDING → OPEN (via set_exchange_id)
        assert order.state == OrderState.PENDING
        tracker.set_exchange_id("state_test", "123")
        assert order.state == OrderState.OPEN
        
        # OPEN → PARTIALLY_FILLED (via add_fill)
        tracker.add_fill("state_test", qty=0.5, price=42000, fee=0.05, fee_asset="USDT")
        assert order.state == OrderState.PARTIALLY_FILLED
        
        # PARTIALLY_FILLED → FILLED (via add_fill)
        tracker.add_fill("state_test", qty=0.5, price=42000, fee=0.05, fee_asset="USDT")
        assert order.state == OrderState.FILLED
        
        logger.info("✓ State transitions: PENDING → OPEN → PARTIALLY_FILLED → FILLED")
    
    def test_cancel_from_various_states(self, tracker):
        """Test cancellation from different states."""
        # Cancel from PENDING
        o1 = tracker.create_order("c1", "BTCUSDT", "BUY", "LIMIT", 1.0, 42000)
        tracker.cancel_order("c1")
        assert o1.state == OrderState.CANCELLED
        
        # Cancel from OPEN
        o2 = tracker.create_order("c2", "BTCUSDT", "BUY", "LIMIT", 1.0, 42000)
        tracker.set_exchange_id("c2", "e2")
        tracker.cancel_order("c2")
        assert o2.state == OrderState.CANCELLED
        
        # Cancel from PARTIALLY_FILLED
        o3 = tracker.create_order("c3", "BTCUSDT", "BUY", "LIMIT", 1.0, 42000)
        tracker.set_exchange_id("c3", "e3")
        tracker.add_fill("c3", qty=0.3, price=42000, fee=0.05, fee_asset="USDT")
        tracker.cancel_order("c3")
        assert o3.state == OrderState.CANCELLED
        assert o3.total_filled_qty == 0.3
        
        logger.info("✓ Cancellation works from all states")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

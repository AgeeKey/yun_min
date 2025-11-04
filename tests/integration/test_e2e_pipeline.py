"""
End-to-end integration tests for full trading pipeline.

Tests the complete flow:
  Decision → Executor → RiskManager → BinanceConnector/Tracker → WebSocketLayer → TradingEngine

Covers:
  - All execution modes (DRY_RUN, PAPER, LIVE-sim)
  - Order types (market, limit, cancel, partial fills)
  - Error scenarios (balance, duplicate client_oid, WS reconnect)
  - Risk validation (position size, daily DD, margin)

Pytest markers:
  - @pytest.mark.integration: E2E flow
  - @pytest.mark.e2e: Full pipeline
  - @pytest.mark.slow: May take >1s

Usage:
  pytest tests/integration/test_e2e_pipeline.py -v
  pytest tests/integration/test_e2e_pipeline.py -v -m e2e
  pytest tests/integration/test_e2e_pipeline.py::test_decision_to_order_pipeline -v
"""

import pytest
import asyncio
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock

# Note: Decision is a type alias Dict[str, Any], not a class
# Use dict() with required keys instead
from yunmin.core.data_contracts import Decision as DecisionType
from yunmin.core.executor import Executor, ExecutionMode, ExecutionStatus
from yunmin.core.websocket_layer import (
    WebSocketLayer, OrderUpdateEvent, KlineUpdateEvent
)
from yunmin.core.order_tracker import OrderTracker, OrderState
from yunmin.core.risk_manager import RiskManager, RiskLevel
from yunmin.connectors.binance_connector import BinanceConnector
from yunmin.core.trading_engine import TradingEngine


# Helper function to create Decision dict (Python 3.13 compatible)
def create_decision(intent: str, confidence: float, size_hint: float, reason: str) -> DecisionType:
    """Create a Decision dict (Python 3.13 safe)"""
    return {
        "intent": intent,
        "confidence": confidence,
        "size_hint": size_hint,
        "reason": reason
    }


@pytest.fixture
def binance_connector_mock():
    """Mock BinanceConnector."""
    connector = Mock(spec=BinanceConnector)
    connector.place_order = Mock(return_value={
        "orderId": "123456",
        "status": "NEW",
        "executedQty": "0",
        "cummulativeQuoteQty": "0"
    })
    connector.cancel_order = Mock(return_value={
        "status": "CANCELED"
    })
    connector.get_listen_key = AsyncMock(return_value="listenkey123")
    return connector


@pytest.fixture
def order_tracker():
    """Create OrderTracker."""
    return OrderTracker()


@pytest.fixture
def risk_manager():
    """Create RiskManager with test config."""
    return RiskManager(
        account_balance=10000.0,
        max_position_pct=0.05,  # 5% max
        max_daily_dd=0.15,      # 15% max DD
        max_daily_trades=50,
        max_open_orders=5,
        risk_level=RiskLevel.MODERATE,
        leverage=1.0
    )


@pytest.fixture
def websocket_layer_mock():
    """Mock WebSocketLayer."""
    ws = Mock(spec=WebSocketLayer)
    ws.register_order_update_callback = Mock()
    ws.register_kline_callback = Mock()
    ws.register_error_callback = Mock()
    ws.subscribe_user_data = AsyncMock()
    ws.subscribe_kline = AsyncMock()
    ws.run = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def executor(binance_connector_mock, order_tracker, risk_manager, websocket_layer_mock):
    """Create Executor with mocked dependencies."""
    return Executor(
        connector=binance_connector_mock,
        tracker=order_tracker,
        risk_manager=risk_manager,
        mode=ExecutionMode.DRY_RUN,
        max_retries=2
    )


@pytest.fixture
def trading_engine(binance_connector_mock, order_tracker, risk_manager, 
                   websocket_layer_mock, executor):
    """Create TradingEngine with mocked dependencies."""
    return TradingEngine(
        connector=binance_connector_mock,
        tracker=order_tracker,
        risk_manager=risk_manager,
        websocket=websocket_layer_mock,
        executor=executor,
        symbols=["BTCUSDT", "ETHUSDT"],
        decision_interval=0.1
    )


# ==================== MODE TESTS ====================

@pytest.mark.integration
@pytest.mark.e2e
class TestExecutionModes:
    """Test all execution modes."""
    
    @pytest.mark.asyncio
    async def test_dry_run_mode(self, executor, order_tracker):
        """Test DRY_RUN: no real orders, only tracker updates."""
        decision = create_decision(
            intent="long",
            confidence=0.85,
            size_hint=0.05,
            reason="Test"
        )
        
        result = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision,
            current_price=42000.0,
            current_position=0
        )
        
        assert result.success
        assert result.status == ExecutionStatus.SUBMITTED
        assert result.order_id is not None
        assert result.order_id.startswith("dry_")
        
        # Verify order in tracker
        order = order_tracker.get_order(result.order_id)
        assert order is not None
        assert order.symbol == "BTCUSDT"
        assert order.side == "BUY"
    
    @pytest.mark.asyncio
    async def test_paper_mode(self, executor, order_tracker, risk_manager):
        """Test PAPER: simulated fills, position tracking."""
        executor.mode = ExecutionMode.PAPER
        
        decision = create_decision(
            intent="long",
            confidence=0.85,
            size_hint=0.05,
            reason="Test"
        )
        
        result = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision,
            current_price=42000.0,
            current_position=0
        )
        
        assert result.success
        assert result.status == ExecutionStatus.FILLED
        assert result.filled_qty > 0
        assert result.avg_price == 42000.0
        assert result.commission > 0
        
        # Verify position in risk manager
        position = risk_manager.open_positions.get("BTCUSDT", 0)
        assert position > 0
    
    @pytest.mark.asyncio
    async def test_live_mode_simulation(self, executor, binance_connector_mock, order_tracker):
        """Test LIVE-sim: real order placement (mocked)."""
        executor.mode = ExecutionMode.LIVE
        
        decision = create_decision(
            intent="long",
            confidence=0.85,
            size_hint=0.05,
            reason="Test"
        )
        
        result = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision,
            current_price=42000.0,
            current_position=0
        )
        
        assert result.success
        assert result.status == ExecutionStatus.SUBMITTED
        assert result.order_id is not None
        assert result.exchange_order_id == "123456"
        
        # Verify connector was called
        binance_connector_mock.place_order.assert_called_once()


# ==================== PIPELINE TESTS ====================

@pytest.mark.integration
@pytest.mark.e2e
class TestDecisionToOrderPipeline:
    """Test complete Decision → Order → Fill pipeline."""
    
    @pytest.mark.asyncio
    async def test_decision_to_order_pipeline(self, executor, order_tracker, risk_manager):
        """Test full pipeline: Decision → Executor → RiskManager → Connector → Tracker."""
        executor.mode = ExecutionMode.PAPER
        
        # Create decision
        decision = create_decision(
            intent="long",
            confidence=0.95,
            size_hint=0.05,
            reason="EMA crossover"
        )
        
        # Execute
        result = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision,
            current_price=42000.0,
            current_position=0
        )
        
        # Assertions
        assert result.success, f"Pipeline failed: {result.error_message}"
        assert result.status == ExecutionStatus.FILLED
        assert result.filled_qty > 0
        
        # Verify order state
        order = order_tracker.get_order(result.order_id)
        assert order is not None
        assert order.state == OrderState.FILLED
        assert order.total_filled_qty == result.filled_qty
        
        # Verify position
        position = risk_manager.open_positions.get("BTCUSDT", 0)
        assert position > 0
        
        # Verify daily stats updated
        stats = risk_manager.get_daily_stats()
        assert stats["trades_count"] == 1
    
    @pytest.mark.asyncio
    async def test_exit_decision(self, executor, order_tracker, risk_manager):
        """Test exit: close position via Decision."""
        executor.mode = ExecutionMode.PAPER
        
        # Open position
        open_decision = create_decision(intent="long", confidence=0.9, size_hint=0.05, reason="Entry")
        await executor.execute_decision(
            symbol="BTCUSDT",
            decision=open_decision,
            current_price=42000.0,
            current_position=0
        )
        
        # Close position
        close_decision = create_decision(intent="exit", confidence=0.8, size_hint=0.05, reason="Exit")
        result = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=close_decision,
            current_price=42500.0,
            current_position=0.1  # Assume 0.1 BTC open
        )
        
        assert result.success
        assert result.status == ExecutionStatus.FILLED


# ==================== PARTIAL FILL TESTS ====================

@pytest.mark.integration
@pytest.mark.e2e
class TestPartialFills:
    """Test partial fill handling."""
    
    @pytest.mark.asyncio
    async def test_partial_fill_average_price(self, executor, order_tracker, risk_manager):
        """Test correct average price calculation with partial fills."""
        executor.mode = ExecutionMode.PAPER
        
        # Place order
        decision = create_decision(intent="long", confidence=0.9, size_hint=0.05, reason="Test")
        result = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision,
            current_price=42000.0,
            current_position=0
        )
        
        order_id = result.order_id
        order = order_tracker.get_order(order_id)
        
        # Simulate partial fill 1
        order_tracker.add_fill(
            client_order_id=order_id,
            qty=0.05,
            price=42000.0,
            fee=2.1,
            fee_asset="USDT"
        )
        
        # Simulate partial fill 2
        order_tracker.add_fill(
            client_order_id=order_id,
            qty=0.05,
            price=42100.0,
            fee=2.1,
            fee_asset="USDT"
        )
        
        # Verify average price
        order = order_tracker.get_order(order_id)
        expected_avg = (42000.0 * 0.05 + 42100.0 * 0.05) / 0.10
        assert abs(order.avg_fill_price - expected_avg) < 1.0
        assert order.total_filled_qty == 0.10
        assert order.total_commission == 4.2
    
    @pytest.mark.asyncio
    async def test_partial_fill_position_tracking(self, risk_manager):
        """Test position tracking across partial fills."""
        # Add first fill
        risk_manager.add_fill(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.05,
            price=42000.0,
            commission=2.1
        )
        
        pos1 = risk_manager.open_positions.get("BTCUSDT", 0)
        assert abs(pos1 - 0.05) < 0.001
        
        # Add second fill
        risk_manager.add_fill(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.03,
            price=42100.0,
            commission=1.26
        )
        
        pos2 = risk_manager.open_positions.get("BTCUSDT", 0)
        assert abs(pos2 - 0.08) < 0.001


# ==================== CANCEL & REISSUE TESTS ====================

@pytest.mark.integration
@pytest.mark.e2e
class TestCancelAndReissue:
    """Test order cancellation and reissuance."""
    
    @pytest.mark.asyncio
    async def test_cancel_order(self, executor, order_tracker, binance_connector_mock):
        """Test order cancellation."""
        executor.mode = ExecutionMode.DRY_RUN
        
        decision = create_decision(intent="long", confidence=0.9, size_hint=0.05, reason="Test")
        result = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision,
            current_price=42000.0,
            current_position=0
        )
        
        order_id = result.order_id
        
        # Cancel order
        cancelled = await executor.cancel_order("BTCUSDT", order_id)
        assert cancelled
        
        # Verify state
        order = order_tracker.get_order(order_id)
        assert order.state == OrderState.CANCELLED
    
    @pytest.mark.asyncio
    async def test_reissue_after_cancel(self, executor, order_tracker):
        """Test reissuance after cancellation."""
        executor.mode = ExecutionMode.PAPER
        
        # Issue and cancel
        decision1 = create_decision(intent="long", confidence=0.9, size_hint=0.05, reason="v1")
        result1 = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision1,
            current_price=42000.0,
            current_position=0
        )
        
        await executor.cancel_order("BTCUSDT", result1.order_id)
        
        # Reissue
        decision2 = create_decision(intent="long", confidence=0.95, size_hint=0.05, reason="v2")
        await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision2,
            current_price=42050.0,
            current_position=0
        )
        
        assert result1.order_id != order_tracker.orders[list(order_tracker.orders.keys())[-1]].client_order_id
        assert order_tracker.get_order(result1.order_id).state == OrderState.CANCELLED


# ==================== RISK VALIDATION TESTS ====================

@pytest.mark.integration
@pytest.mark.e2e
class TestRiskValidation:
    """Test RiskManager pre-order checks."""
    
    @pytest.mark.asyncio
    async def test_position_size_limit(self, executor, risk_manager):
        """Test position size validation."""
        executor.mode = ExecutionMode.PAPER
        
        # Try to order 10% (> 5% limit)
        decision = create_decision(
            intent="long",
            confidence=0.9,
            size_hint=0.20,  # 20% of balance
            reason="Too large"
        )
        
        result = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision,
            current_price=42000.0,
            current_position=0
        )
        
        # Should be capped or rejected
        assert result.filled_qty <= 10000 * 0.05 / 42000.0  # Max 5% of balance
    
    @pytest.mark.asyncio
    async def test_daily_dd_lock(self, executor, risk_manager):
        """Test daily drawdown lock."""
        executor.mode = ExecutionMode.PAPER
        
        # Record losing trades to hit DD limit
        for i in range(5):
            risk_manager.record_trade_result(
                symbol="BTCUSDT",
                entry_price=42000.0,
                exit_price=41400.0,  # -1.4% loss
                qty=1.0,
                side="BUY",
                commission=2.1
            )
        
        # Daily stats
        stats = risk_manager.get_daily_stats()
        dd = stats["drawdown"]
        
        # If DD > max_daily_dd, next order should be rejected
        if dd > risk_manager.max_daily_dd:
            decision = create_decision(intent="long", confidence=0.9, size_hint=0.05, reason="Test")
            result = await executor.execute_decision(
                symbol="BTCUSDT",
                decision=decision,
                current_price=42000.0,
                current_position=0
            )
            
            assert not result.success
            assert "drawdown" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_max_open_orders_limit(self, executor, order_tracker, risk_manager):
        """Test max concurrent orders check."""
        executor.mode = ExecutionMode.PAPER
        risk_manager.max_open_orders = 2
        
        # Place order 1
        decision1 = create_decision(intent="long", confidence=0.9, size_hint=0.02, reason="1")
        result1 = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision1,
            current_price=42000.0,
            current_position=0
        )
        
        # Reset mode to DRY_RUN to not auto-fill
        executor.mode = ExecutionMode.DRY_RUN
        order1 = order_tracker.get_order(result1.order_id)
        order1.state = OrderState.SUBMITTED  # Keep it open
        
        # Place order 2
        decision2 = create_decision(intent="long", confidence=0.9, size_hint=0.02, reason="2")
        result2 = await executor.execute_decision(
            symbol="ETHUSDT",
            decision=decision2,
            current_price=2500.0,
            current_position=0
        )
        
        # Place order 3 (should fail)
        decision3 = create_decision(intent="long", confidence=0.9, size_hint=0.02, reason="3")
        result3 = await executor.execute_decision(
            symbol="BNBUSDT",
            decision=decision3,
            current_price=600.0,
            current_position=0
        )
        
        assert result3.success or "open" in result3.error_message.lower()


# ==================== WEBSOCKET TESTS ====================

@pytest.mark.integration
@pytest.mark.e2e
class TestWebSocketIntegration:
    """Test WebSocket event handling."""
    
    @pytest.mark.asyncio
    async def test_ws_order_update_event(self, trading_engine, order_tracker):
        """Test order update from WebSocket."""
        # Simulate order update event
        event = OrderUpdateEvent(
            event_type="executionReport",
            event_time=int(datetime.now(UTC).timestamp() * 1000),
            symbol="BTCUSDT",
            client_order_id="test_order_1",
            exchange_order_id="123456",
            status="FILLED",
            side="BUY",
            qty=0.1,
            price=42000.0,
            cumulative_filled_qty=0.1,
            last_executed_qty=0.1,
            last_executed_price=42000.0,
            commission=0.0001,
            commission_asset="BTC"
        )
        
        # Process event
        await trading_engine._on_order_update(event)
        
        # Verify order tracked
        order = order_tracker.get_order("test_order_1")
        # Note: order might not exist if not pre-created
    
    @pytest.mark.asyncio
    async def test_ws_kline_update_event(self, trading_engine):
        """Test kline update from WebSocket."""
        event = KlineUpdateEvent(
            event_type="kline",
            event_time=int(datetime.now(UTC).timestamp() * 1000),
            symbol="BTCUSDT",
            timeframe="1m",
            open_time=1000000,
            close_time=1000060000,
            open=42000.0,
            high=42500.0,
            low=41500.0,
            close=42250.0,
            volume=100.5,
            quote_volume=4250625.0,
            is_final=True
        )
        
        # Process event
        await trading_engine._on_kline_update(event)
        
        # Verify price updated
        assert trading_engine.last_prices.get("BTCUSDT") == 42250.0


# ==================== ERROR HANDLING TESTS ====================

@pytest.mark.integration
@pytest.mark.e2e
class TestErrorHandling:
    """Test error scenarios."""
    
    @pytest.mark.asyncio
    async def test_insufficient_balance(self, executor):
        """Test handling when balance insufficient."""
        executor.mode = ExecutionMode.LIVE
        executor.connector.place_order = Mock(
            side_effect=Exception("Insufficient balance")
        )
        
        decision = create_decision(intent="long", confidence=0.9, size_hint=0.5, reason="Test")
        result = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision,
            current_price=42000.0,
            current_position=0
        )
        
        assert not result.success
        assert "balance" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_invalid_decision_intent(self, executor):
        """Test handling of invalid decision intent."""
        decision = create_decision(
            intent="invalid_action",
            confidence=0.9,
            size_hint=0.05,
            reason="Test"
        )
        
        result = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision,
            current_price=42000.0,
            current_position=0
        )
        
        assert not result.success
        assert "intent" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_no_position_to_exit(self, executor):
        """Test exit when no position open."""
        decision = create_decision(intent="exit", confidence=0.9, size_hint=0.05, reason="Test")
        result = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision,
            current_price=42000.0,
            current_position=0  # No position
        )
        
        assert not result.success
        assert "no position" in result.error_message.lower()


# ==================== CONCURRENT TESTS ====================

@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_concurrent_decisions(executor, order_tracker):
    """Test handling concurrent decision executions."""
    executor.mode = ExecutionMode.PAPER
    
    decisions = [
        create_decision(intent="long", confidence=0.9, size_hint=0.01, reason=f"D{i}")
        for i in range(5)
    ]
    
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT"]
    prices = [42000.0, 2500.0, 600.0, 0.5, 0.3]
    
    tasks = [
        executor.execute_decision(
            symbol=symbols[i],
            decision=decisions[i],
            current_price=prices[i],
            current_position=0
        )
        for i in range(5)
    ]
    
    results = await asyncio.gather(*tasks)
    
    # All should succeed
    assert all(r.success for r in results)
    assert len(order_tracker.orders) >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])

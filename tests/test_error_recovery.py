"""
Tests for Error Recovery Module
"""

import pytest
from unittest.mock import Mock, AsyncMock

from yunmin.core.error_recovery import (
    ErrorRecoveryManager,
    RecoveryConfig,
    RecoveryState,
    ExponentialBackoff,
    NetworkErrorHandler,
    ExchangeAPIErrorHandler
)


# ==================== ExponentialBackoff Tests ====================

def test_exponential_backoff_initial():
    """Test exponential backoff starts with initial delay"""
    backoff = ExponentialBackoff(initial=1.0, maximum=60.0, multiplier=2.0)
    
    delay = backoff.next_delay()
    assert 0.8 <= delay <= 1.2  # 1.0 ± 20% jitter


def test_exponential_backoff_increases():
    """Test backoff increases exponentially"""
    backoff = ExponentialBackoff(initial=1.0, maximum=60.0, multiplier=2.0)
    
    delay1 = backoff.next_delay()
    delay2 = backoff.next_delay()
    delay3 = backoff.next_delay()
    
    # Second delay should be roughly 2x first (with jitter)
    assert delay2 > delay1
    assert delay3 > delay2


def test_exponential_backoff_maximum():
    """Test backoff respects maximum"""
    backoff = ExponentialBackoff(initial=30.0, maximum=60.0, multiplier=2.0)
    
    # After several iterations, should be capped at max
    for _ in range(10):
        delay = backoff.next_delay()
    
    # Should be around max (60.0 ± 20% jitter)
    assert delay <= 72.0  # 60 + 20%


def test_exponential_backoff_reset():
    """Test backoff reset"""
    backoff = ExponentialBackoff(initial=1.0, maximum=60.0, multiplier=2.0)
    
    backoff.next_delay()
    backoff.next_delay()
    backoff.reset()
    
    assert backoff.attempt == 0
    assert backoff.current == 1.0


# ==================== ErrorRecoveryManager Tests ====================

@pytest.mark.asyncio
async def test_recovery_manager_success_no_retry():
    """Test successful operation without retry"""
    config = RecoveryConfig(max_retries=3)
    manager = ErrorRecoveryManager(config)
    
    async def success_operation():
        return "success"
    
    result = await manager.execute_with_retry(
        success_operation,
        operation_name="test"
    )
    
    assert result == "success"
    assert manager.state == RecoveryState.HEALTHY
    assert manager.consecutive_errors == 0


@pytest.mark.asyncio
async def test_recovery_manager_retry_then_success():
    """Test operation fails then succeeds"""
    config = RecoveryConfig(max_retries=5, initial_backoff=0.01)
    manager = ErrorRecoveryManager(config)
    
    attempt_counter = {"count": 0}
    
    async def flaky_operation():
        attempt_counter["count"] += 1
        if attempt_counter["count"] < 3:
            raise ConnectionError("Network timeout")
        return "success"
    
    result = await manager.execute_with_retry(
        flaky_operation,
        operation_name="flaky test"
    )
    
    assert result == "success"
    assert attempt_counter["count"] == 3
    assert manager.state == RecoveryState.HEALTHY
    assert manager.consecutive_errors == 0


@pytest.mark.asyncio
async def test_recovery_manager_max_retries_exceeded():
    """Test max retries exceeded"""
    config = RecoveryConfig(max_retries=3, initial_backoff=0.01)
    manager = ErrorRecoveryManager(config)
    
    async def always_fail():
        raise ValueError("Always fails")
    
    with pytest.raises(ValueError):
        await manager.execute_with_retry(
            always_fail,
            operation_name="failing test"
        )
    
    assert manager.state == RecoveryState.CRITICAL
    assert manager.consecutive_errors >= config.critical_error_threshold


@pytest.mark.asyncio
async def test_recovery_manager_reconnect_exchange():
    """Test exchange reconnection"""
    config = RecoveryConfig(max_retries=3, initial_backoff=0.01)
    manager = ErrorRecoveryManager(config)
    
    # Mock exchange connector
    exchange = Mock()
    exchange.connect = AsyncMock(return_value=True)
    
    result = await manager.reconnect_exchange(exchange)
    
    assert result is True
    assert manager.state == RecoveryState.HEALTHY
    assert exchange.connect.called


@pytest.mark.asyncio
async def test_recovery_manager_restore_positions():
    """Test position restoration from database"""
    config = RecoveryConfig()
    manager = ErrorRecoveryManager(config)
    
    # Mock repository
    repository = Mock()
    mock_positions = [
        {"symbol": "BTC/USDT", "side": "LONG", "amount": 0.01},
        {"symbol": "ETH/USDT", "side": "SHORT", "amount": 0.1}
    ]
    repository.get_open_positions = Mock(return_value=mock_positions)
    
    positions = await manager.restore_positions_from_db(repository)
    
    assert len(positions) == 2
    assert positions[0]["symbol"] == "BTC/USDT"
    assert repository.get_open_positions.called


def test_recovery_manager_health_check():
    """Test health check"""
    config = RecoveryConfig()
    manager = ErrorRecoveryManager(config)
    
    health = manager.health_check()
    
    assert health["state"] == "healthy"
    assert health["consecutive_errors"] == 0
    assert health["is_healthy"] is True


def test_recovery_manager_degraded_mode():
    """Test degraded mode"""
    config = RecoveryConfig()
    manager = ErrorRecoveryManager(config)
    
    manager.enter_degraded_mode()
    assert manager.state == RecoveryState.DEGRADED
    
    manager.exit_degraded_mode()
    assert manager.state == RecoveryState.HEALTHY


# ==================== NetworkErrorHandler Tests ====================

def test_network_error_detection():
    """Test network error detection"""
    assert NetworkErrorHandler.is_network_error(ConnectionError("test"))
    assert NetworkErrorHandler.is_network_error(TimeoutError("test"))
    assert NetworkErrorHandler.is_network_error(OSError("test"))
    assert not NetworkErrorHandler.is_network_error(ValueError("test"))


@pytest.mark.asyncio
async def test_network_error_handling():
    """Test network error handling with reconnection"""
    config = RecoveryConfig(max_retries=3, initial_backoff=0.01)
    manager = ErrorRecoveryManager(config)
    
    reconnect_callback = AsyncMock(return_value=True)
    
    await NetworkErrorHandler.handle_network_error(
        ConnectionError("Network down"),
        manager,
        reconnect_callback
    )
    
    assert reconnect_callback.called


# ==================== ExchangeAPIErrorHandler Tests ====================

def test_api_error_is_retryable():
    """Test retryable error codes"""
    assert ExchangeAPIErrorHandler.is_retryable(-1001)  # Internal error
    assert ExchangeAPIErrorHandler.is_retryable(-1003)  # Too many requests
    assert ExchangeAPIErrorHandler.is_retryable(-1021)  # Timestamp out of sync
    assert not ExchangeAPIErrorHandler.is_retryable(-1000)  # Unknown error


@pytest.mark.asyncio
async def test_api_error_handling():
    """Test API error handling"""
    config = RecoveryConfig()
    manager = ErrorRecoveryManager(config)
    
    # Test retryable error
    await ExchangeAPIErrorHandler.handle_api_error(
        -1003,
        "Too many requests",
        manager
    )
    
    # Test non-retryable error
    await ExchangeAPIErrorHandler.handle_api_error(
        -9999,
        "Critical error",
        manager
    )
    
    assert manager.state == RecoveryState.CRITICAL


# ==================== Integration Tests ====================

@pytest.mark.asyncio
async def test_full_recovery_cycle():
    """Test complete recovery cycle"""
    config = RecoveryConfig(max_retries=5, initial_backoff=0.01)
    manager = ErrorRecoveryManager(config)
    
    # Simulate flaky exchange connection
    connection_attempts = {"count": 0}
    
    async def connect_exchange():
        connection_attempts["count"] += 1
        if connection_attempts["count"] < 3:
            raise ConnectionError("Network timeout")
        return True
    
    # First connection fails, retries, then succeeds
    result = await manager.execute_with_retry(
        connect_exchange,
        operation_name="exchange connection"
    )
    
    assert result is True
    assert connection_attempts["count"] == 3
    
    # Check health after recovery
    health = manager.health_check()
    assert health["is_healthy"] is True
    assert health["consecutive_errors"] == 0


@pytest.mark.asyncio
async def test_critical_state_after_failures():
    """Test critical state after repeated failures"""
    config = RecoveryConfig(
        max_retries=2,
        initial_backoff=0.01,
        critical_error_threshold=2
    )
    manager = ErrorRecoveryManager(config)
    
    async def always_fail():
        raise RuntimeError("Critical failure")
    
    # First failure
    with pytest.raises(RuntimeError):
        await manager.execute_with_retry(always_fail, operation_name="test1")
    
    # Second failure - should trigger critical state
    with pytest.raises(RuntimeError):
        await manager.execute_with_retry(always_fail, operation_name="test2")
    
    health = manager.health_check()
    assert health["state"] == "critical"
    assert manager.consecutive_errors >= config.critical_error_threshold

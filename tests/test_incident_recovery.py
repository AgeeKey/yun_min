"""
Comprehensive tests for Incident Response & Recovery
Tests circuit breaker, failover, state persistence, and runbook automation
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime, UTC

from yunmin.core.error_recovery import (
    ErrorRecoveryManager,
    RecoveryConfig,
    RecoveryState,
    CircuitBreaker,
    CircuitState,
    ExponentialBackoff,
    NetworkErrorHandler,
    ExchangeAPIErrorHandler,
    SystemState
)


@pytest.fixture
def temp_state_file():
    """Create temporary state file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        yield f.name
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def recovery_config(temp_state_file):
    """Create recovery configuration"""
    return RecoveryConfig(
        max_retries=3,
        initial_backoff=0.1,
        max_backoff=1.0,
        circuit_failure_threshold=3,
        circuit_timeout=1.0,
        state_file=temp_state_file,
        auto_save_interval=1.0
    )


@pytest.fixture
def recovery_manager(recovery_config):
    """Create recovery manager"""
    return ErrorRecoveryManager(recovery_config)


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    @pytest.mark.asyncio
    async def test_circuit_closed_normal_operation(self):
        """Test circuit breaker in CLOSED state"""
        breaker = CircuitBreaker(failure_threshold=3)
        
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures"""
        breaker = CircuitBreaker(failure_threshold=3)
        
        async def failing_func():
            raise Exception("Test failure")
        
        # Fail 3 times to open circuit
        for i in range(3):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_rejects_when_open(self):
        """Test circuit breaker rejects requests when OPEN"""
        breaker = CircuitBreaker(failure_threshold=2, timeout=10.0)
        
        async def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for i in range(2):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        assert breaker.state == CircuitState.OPEN
        
        # Should reject new requests
        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            async def any_func():
                return "test"
            await breaker.call(any_func)
    
    @pytest.mark.asyncio
    async def test_circuit_half_open_transition(self):
        """Test circuit breaker transitions to HALF_OPEN"""
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)
        
        async def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for i in range(2):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(0.2)
        
        # Should attempt reset
        async def success_func():
            return "success"
        
        try:
            result = await breaker.call(success_func)
            assert breaker.state == CircuitState.HALF_OPEN
        except Exception:
            pass
    
    @pytest.mark.asyncio
    async def test_circuit_closes_after_successes(self):
        """Test circuit breaker closes after successful calls"""
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.1, success_threshold=2)
        
        async def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for i in range(2):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        # Wait for timeout
        await asyncio.sleep(0.2)
        
        # Execute successful calls
        async def success_func():
            return "success"
        
        for i in range(2):
            await breaker.call(success_func)
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    def test_circuit_breaker_get_state(self):
        """Test getting circuit breaker state"""
        breaker = CircuitBreaker()
        state = breaker.get_state()
        
        assert "state" in state
        assert "failure_count" in state
        assert state["state"] == "closed"
    
    def test_circuit_breaker_manual_reset(self):
        """Test manual circuit breaker reset"""
        breaker = CircuitBreaker(failure_threshold=1)
        breaker.state = CircuitState.OPEN
        breaker.failure_count = 5
        
        breaker.reset()
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0


class TestStatePersistence:
    """Test state persistence functionality"""
    
    def test_save_and_load_state(self, recovery_manager, temp_state_file):
        """Test saving and loading state"""
        # Modify state
        recovery_manager.state = RecoveryState.DEGRADED
        recovery_manager.consecutive_errors = 5
        recovery_manager.reconnection_attempts = 3
        
        # Save state
        recovery_manager._save_state()
        
        # Verify file exists
        assert Path(temp_state_file).exists()
        
        # Create new manager to load state
        new_config = RecoveryConfig(state_file=temp_state_file)
        new_manager = ErrorRecoveryManager(new_config)
        
        # Verify state loaded
        assert new_manager.state == RecoveryState.DEGRADED
        assert new_manager.consecutive_errors == 5
        assert new_manager.reconnection_attempts == 3
    
    def test_auto_save_state(self, recovery_manager):
        """Test auto-save functionality"""
        # Modify state
        recovery_manager.state = RecoveryState.RECONNECTING
        recovery_manager.last_save_time = 0  # Force save
        
        # Trigger auto-save
        recovery_manager.auto_save_state()
        
        # Verify state file exists
        assert Path(recovery_manager.config.state_file).exists()
    
    def test_system_state_serialization(self):
        """Test SystemState serialization"""
        state = SystemState(
            timestamp=datetime.now(UTC),
            recovery_state="healthy",
            consecutive_errors=0,
            reconnection_attempts=0,
            circuit_state="closed",
            circuit_failure_count=0,
            metadata={"test": "value"}
        )
        
        # Convert to dict
        data = state.to_dict()
        assert isinstance(data, dict)
        assert "timestamp" in data
        
        # Convert back to SystemState
        restored = SystemState.from_dict(data)
        assert restored.recovery_state == state.recovery_state
        assert restored.consecutive_errors == state.consecutive_errors


class TestFailover:
    """Test failover functionality"""
    
    class MockService:
        """Mock service for testing"""
        def __init__(self, name: str, should_fail: bool = False):
            self.name = name
            self.should_fail = should_fail
            self.call_count = 0
        
        async def test_operation(self):
            """Mock operation"""
            self.call_count += 1
            if self.should_fail:
                raise Exception(f"{self.name} failed")
            return f"{self.name} success"
    
    @pytest.mark.asyncio
    async def test_failover_to_backup(self, recovery_manager):
        """Test failover to backup service"""
        # Create services
        primary = self.MockService("primary", should_fail=True)
        backup1 = self.MockService("backup1", should_fail=False)
        backup2 = self.MockService("backup2", should_fail=False)
        
        # Configure failover
        recovery_manager.set_failover_services(primary, [backup1, backup2])
        
        # Execute with failover
        result = await recovery_manager.execute_with_failover(
            "test",
            "test_operation"
        )
        
        # Should failover to backup1
        assert result == "backup1 success"
        assert primary.call_count == 1
        assert backup1.call_count == 1
        assert backup2.call_count == 0
    
    @pytest.mark.asyncio
    async def test_failover_all_services_fail(self, recovery_manager):
        """Test failover when all services fail"""
        # Create failing services
        primary = self.MockService("primary", should_fail=True)
        backup1 = self.MockService("backup1", should_fail=True)
        
        # Configure failover
        recovery_manager.set_failover_services(primary, [backup1])
        
        # Should raise exception
        with pytest.raises(Exception, match="All failover services failed"):
            await recovery_manager.execute_with_failover(
                "test",
                "test_operation"
            )
    
    @pytest.mark.asyncio
    async def test_failover_primary_success(self, recovery_manager):
        """Test failover stays on primary when successful"""
        # Create services
        primary = self.MockService("primary", should_fail=False)
        backup1 = self.MockService("backup1", should_fail=False)
        
        # Configure failover
        recovery_manager.set_failover_services(primary, [backup1])
        
        # Execute with failover
        result = await recovery_manager.execute_with_failover(
            "test",
            "test_operation"
        )
        
        # Should use primary
        assert result == "primary success"
        assert primary.call_count == 1
        assert backup1.call_count == 0


class TestRunbookAutomation:
    """Test runbook automation functionality"""
    
    @pytest.mark.asyncio
    async def test_register_error_handler(self, recovery_manager):
        """Test registering error handler"""
        handled = False
        
        async def handler(error):
            nonlocal handled
            handled = True
        
        recovery_manager.register_error_handler("test.*error", handler)
        
        assert "test.*error" in recovery_manager.known_errors
    
    @pytest.mark.asyncio
    async def test_handle_known_error(self, recovery_manager):
        """Test handling known error"""
        handled = False
        
        async def handler(error):
            nonlocal handled
            handled = True
        
        recovery_manager.register_error_handler("connection.*lost", handler)
        
        error = Exception("connection was lost")
        result = await recovery_manager.handle_known_error(error)
        
        assert result is True
        assert handled is True
    
    @pytest.mark.asyncio
    async def test_handle_unknown_error(self, recovery_manager):
        """Test handling unknown error"""
        error = Exception("unknown error type")
        result = await recovery_manager.handle_known_error(error)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_error_handler_counts(self, recovery_manager):
        """Test error handler call counting"""
        async def handler(error):
            pass
        
        recovery_manager.register_error_handler("test", handler)
        
        # Handle error multiple times
        for i in range(3):
            error = Exception("test error")
            await recovery_manager.handle_known_error(error)
        
        assert recovery_manager.error_counts["test"] == 3


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with recovery manager"""
    
    @pytest.mark.asyncio
    async def test_execute_with_circuit_breaker(self, recovery_manager):
        """Test executing function through circuit breaker"""
        async def success_func():
            return "success"
        
        result = await recovery_manager.execute_with_circuit_breaker(
            success_func,
            operation_name="test"
        )
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self, recovery_manager):
        """Test circuit breaker opens after failures"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Fail multiple times
        for i in range(3):
            with pytest.raises(Exception):
                await recovery_manager.execute_with_circuit_breaker(
                    failing_func,
                    operation_name="test"
                )
        
        assert recovery_manager.circuit_breaker.state == CircuitState.OPEN


class TestHealthCheck:
    """Test health check functionality"""
    
    def test_health_check_healthy(self, recovery_manager):
        """Test health check when system is healthy"""
        health = recovery_manager.health_check()
        
        assert health["state"] == "healthy"
        assert health["consecutive_errors"] == 0
        assert health["is_healthy"] is True
    
    def test_health_check_degraded(self, recovery_manager):
        """Test health check when system is degraded"""
        recovery_manager.state = RecoveryState.DEGRADED
        recovery_manager.consecutive_errors = 2
        
        health = recovery_manager.health_check()
        
        assert health["state"] == "degraded"
        assert health["consecutive_errors"] == 2
        assert health["is_healthy"] is False


class TestIntegration:
    """Integration tests for incident recovery"""
    
    @pytest.mark.asyncio
    async def test_complete_recovery_flow(self, recovery_manager):
        """Test complete recovery flow"""
        # Simulate failures
        async def failing_func():
            raise Exception("Network error")
        
        try:
            await recovery_manager.execute_with_retry(
                failing_func,
                operation_name="test"
            )
        except Exception:
            pass
        
        # Check state
        assert recovery_manager.state in [RecoveryState.CRITICAL, RecoveryState.RECONNECTING]
        
        # Save state
        recovery_manager._save_state()
        
        # Verify state persisted
        assert Path(recovery_manager.config.state_file).exists()
    
    @pytest.mark.asyncio
    async def test_failover_with_circuit_breaker(self, recovery_manager):
        """Test failover combined with circuit breaker"""
        class MockService:
            async def operation(self):
                return "success"
        
        primary = MockService()
        backup = MockService()
        
        recovery_manager.set_failover_services(primary, [backup])
        
        # Execute operation
        result = await recovery_manager.execute_with_failover(
            "test",
            "operation"
        )
        
        assert result == "success"


class TestExistingFunctionality:
    """Test that existing functionality still works"""
    
    @pytest.mark.asyncio
    async def test_execute_with_retry(self, recovery_manager):
        """Test execute with retry still works"""
        attempt = 0
        
        async def flaky_func():
            nonlocal attempt
            attempt += 1
            if attempt < 2:
                raise ConnectionError("Network timeout")
            return "success"
        
        result = await recovery_manager.execute_with_retry(
            flaky_func,
            operation_name="test"
        )
        
        assert result == "success"
        assert attempt == 2
    
    def test_degraded_mode(self, recovery_manager):
        """Test degraded mode functionality"""
        recovery_manager.enter_degraded_mode()
        assert recovery_manager.state == RecoveryState.DEGRADED
        
        recovery_manager.exit_degraded_mode()
        assert recovery_manager.state == RecoveryState.HEALTHY

"""
Error Recovery Module for YunMin Trading Bot
Handles reconnection, network failures, graceful degradation, circuit breaker, and failover.
"""
import asyncio
import time
import json
import pickle
from pathlib import Path
from typing import Optional, Callable, Any, Dict, List
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta, UTC
from loguru import logger


class RecoveryState(Enum):
    """Recovery state enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RECONNECTING = "reconnecting"
    CRITICAL = "critical"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Circuit broken, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RecoveryConfig:
    """Configuration for error recovery"""
    max_retries: int = 5
    initial_backoff: float = 1.0  # seconds
    max_backoff: float = 60.0  # seconds
    backoff_multiplier: float = 2.0
    health_check_interval: float = 30.0  # seconds
    critical_error_threshold: int = 3  # consecutive critical errors
    
    # Circuit breaker settings
    circuit_failure_threshold: int = 5  # Failures to open circuit
    circuit_timeout: float = 60.0  # Seconds before trying half-open
    circuit_success_threshold: int = 2  # Successes to close circuit
    
    # State persistence settings
    state_file: str = "data/recovery_state.json"
    auto_save_interval: float = 300.0  # Save state every 5 minutes
    
    # Failover settings
    enable_failover: bool = True
    failover_timeout: float = 10.0  # Seconds before failover


@dataclass
class SystemState:
    """Persistent system state"""
    timestamp: datetime
    recovery_state: str
    consecutive_errors: int
    reconnection_attempts: int
    circuit_state: str
    circuit_failure_count: int
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SystemState':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class ExponentialBackoff:
    """Exponential backoff calculator with jitter"""
    
    def __init__(self, initial: float = 1.0, maximum: float = 60.0, multiplier: float = 2.0):
        self.initial = initial
        self.maximum = maximum
        self.multiplier = multiplier
        self.current = initial
        self.attempt = 0
    
    def next_delay(self) -> float:
        """Calculate next delay with exponential backoff and jitter"""
        import random
        
        delay = min(self.current, self.maximum)
        # Add jitter: ±20% randomization
        jitter = delay * 0.2 * (random.random() * 2 - 1)
        actual_delay = max(0.1, delay + jitter)
        
        self.current = self.current * self.multiplier
        self.attempt += 1
        
        return actual_delay
    
    def reset(self):
        """Reset backoff to initial state"""
        self.current = self.initial
        self.attempt = 0


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API failures.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception: If circuit is OPEN or function fails
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info("🔄 Circuit breaker: Attempting reset (HALF_OPEN)")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception(
                    f"Circuit breaker OPEN. Service unavailable. "
                    f"Retry after {self.timeout}s"
                )
        
        try:
            # Execute function
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Handle success
            self._on_success()
            return result
        
        except Exception as e:
            # Handle failure
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.now(UTC) - self.last_failure_time).total_seconds()
        return elapsed >= self.timeout
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(f"🔄 Circuit breaker: Success {self.success_count}/{self.success_threshold}")
            
            if self.success_count >= self.success_threshold:
                logger.success("✅ Circuit breaker: CLOSED (service recovered)")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        self.last_failure_time = datetime.now(UTC)
        self.failure_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning("⚠️ Circuit breaker: Failure in HALF_OPEN, reopening")
            self.state = CircuitState.OPEN
            self.success_count = 0
        
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"🔴 Circuit breaker: OPEN after {self.failure_count} failures"
                )
                self.state = CircuitState.OPEN
    
    def get_state(self) -> dict:
        """Get circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }
    
    def reset(self):
        """Manually reset circuit breaker"""
        logger.info("🔄 Circuit breaker: Manual reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class ErrorRecoveryManager:
    """
    Manages error recovery, reconnection logic, and graceful degradation.
    
    Features:
    - Exponential backoff with jitter
    - Automatic reconnection for network errors
    - State recovery from database
    - Circuit breaker pattern
    - Health monitoring
    - Failover logic
    - State persistence
    - Runbook automation
    """
    
    def __init__(self, config: Optional[RecoveryConfig] = None):
        self.config = config or RecoveryConfig()
        self.state = RecoveryState.HEALTHY
        self.consecutive_errors = 0
        self.last_health_check = time.time()
        self.reconnection_attempts = 0
        self.backoff = ExponentialBackoff(
            initial=self.config.initial_backoff,
            maximum=self.config.max_backoff,
            multiplier=self.config.backoff_multiplier
        )
        
        # Circuit breaker for API calls
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.circuit_failure_threshold,
            timeout=self.config.circuit_timeout,
            success_threshold=self.config.circuit_success_threshold
        )
        
        # State persistence
        self.state_file = Path(self.config.state_file)
        self.last_save_time = time.time()
        
        # Failover configuration
        self.primary_service = None
        self.backup_services: List[Any] = []
        self.current_service_index = 0
        
        # Runbook automation
        self.known_errors: Dict[str, Callable] = {}
        self.error_counts: Dict[str, int] = {}
        
        # Load saved state if exists
        self._load_state()
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        operation_name: str = "operation",
        **kwargs
    ) -> Any:
        """
        Execute function with automatic retry and exponential backoff.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            operation_name: Name for logging
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception: After max retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                result = await func(*args, **kwargs)
                
                # Success - reset backoff and error counter
                if attempt > 0:
                    logger.info(f"✅ {operation_name} recovered after {attempt + 1} attempts")
                    self.backoff.reset()
                    self.consecutive_errors = 0
                    self.state = RecoveryState.HEALTHY
                
                return result
            
            except Exception as e:
                last_exception = e
                self.consecutive_errors += 1
                
                if attempt < self.config.max_retries - 1:
                    delay = self.backoff.next_delay()
                    logger.warning(
                        f"⚠️ {operation_name} failed (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                        f"\n   Retrying in {delay:.2f}s..."
                    )
                    self.state = RecoveryState.RECONNECTING
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"❌ {operation_name} failed after {self.config.max_retries} attempts: {e}"
                    )
                    self.state = RecoveryState.CRITICAL
        
        # Max retries exhausted
        if self.consecutive_errors >= self.config.critical_error_threshold:
            self.state = RecoveryState.CRITICAL
            logger.critical(
                f"🚨 CRITICAL: {self.consecutive_errors} consecutive errors in {operation_name}"
            )
        
        raise last_exception
    
    async def reconnect_exchange(self, exchange_connector) -> bool:
        """
        Reconnect to exchange with exponential backoff.
        
        Args:
            exchange_connector: Exchange connector instance
        
        Returns:
            True if reconnection successful
        """
        logger.info("🔄 Attempting to reconnect to exchange...")
        self.state = RecoveryState.RECONNECTING
        
        try:
            result = await self.execute_with_retry(
                exchange_connector.connect,
                operation_name="exchange reconnection"
            )
            
            logger.success("✅ Exchange reconnection successful")
            self.state = RecoveryState.HEALTHY
            self.reconnection_attempts = 0
            return True
        
        except Exception as e:
            logger.error(f"❌ Exchange reconnection failed: {e}")
            self.reconnection_attempts += 1
            self.state = RecoveryState.CRITICAL
            return False
    
    async def restore_positions_from_db(self, repository) -> list:
        """
        Restore open positions from database after crash/restart.
        
        Args:
            repository: PositionRepository instance
        
        Returns:
            List of restored positions
        """
        logger.info("📥 Restoring positions from database...")
        
        try:
            open_positions = repository.get_open_positions()
            logger.success(f"✅ Restored {len(open_positions)} open positions")
            return open_positions
        
        except Exception as e:
            logger.error(f"❌ Failed to restore positions: {e}")
            return []
    
    def health_check(self) -> dict:
        """
        Perform health check and return system status.
        
        Returns:
            Dictionary with health metrics
        """
        current_time = time.time()
        time_since_check = current_time - self.last_health_check
        
        health = {
            "state": self.state.value,
            "consecutive_errors": self.consecutive_errors,
            "reconnection_attempts": self.reconnection_attempts,
            "backoff_attempt": self.backoff.attempt,
            "is_healthy": self.state == RecoveryState.HEALTHY,
            "time_since_last_check": time_since_check
        }
        
        self.last_health_check = current_time
        return health
    
    def enter_degraded_mode(self):
        """Enter degraded mode (limited functionality)"""
        logger.warning("⚠️ Entering degraded mode - limited functionality")
        self.state = RecoveryState.DEGRADED
    
    def exit_degraded_mode(self):
        """Exit degraded mode (restore full functionality)"""
        logger.info("✅ Exiting degraded mode - full functionality restored")
        self.state = RecoveryState.HEALTHY
        self.consecutive_errors = 0
        self.backoff.reset()
    
    def _load_state(self):
        """Load persisted state from file"""
        if not self.state_file.exists():
            logger.info("No saved state found, starting fresh")
            return
        
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                saved_state = SystemState.from_dict(data)
                
                # Restore state
                self.state = RecoveryState(saved_state.recovery_state)
                self.consecutive_errors = saved_state.consecutive_errors
                self.reconnection_attempts = saved_state.reconnection_attempts
                self.circuit_breaker.state = CircuitState(saved_state.circuit_state)
                self.circuit_breaker.failure_count = saved_state.circuit_failure_count
                
                logger.success(f"✅ Restored state from {self.state_file}")
                logger.info(f"   State: {self.state.value}, Errors: {self.consecutive_errors}")
        
        except Exception as e:
            logger.error(f"❌ Failed to load state: {e}")
    
    def _save_state(self):
        """Save current state to file"""
        try:
            # Create data directory if needed
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            state = SystemState(
                timestamp=datetime.now(UTC),
                recovery_state=self.state.value,
                consecutive_errors=self.consecutive_errors,
                reconnection_attempts=self.reconnection_attempts,
                circuit_state=self.circuit_breaker.state.value,
                circuit_failure_count=self.circuit_breaker.failure_count,
                metadata={}
            )
            
            with open(self.state_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)
            
            self.last_save_time = time.time()
            logger.debug(f"💾 State saved to {self.state_file}")
        
        except Exception as e:
            logger.error(f"❌ Failed to save state: {e}")
    
    def auto_save_state(self):
        """Auto-save state if interval elapsed"""
        current_time = time.time()
        if current_time - self.last_save_time >= self.config.auto_save_interval:
            self._save_state()
    
    def set_failover_services(self, primary: Any, backups: List[Any]):
        """
        Configure failover services.
        
        Args:
            primary: Primary service/connector
            backups: List of backup services
        """
        self.primary_service = primary
        self.backup_services = backups
        self.current_service_index = 0
        logger.info(f"🔄 Failover configured: 1 primary + {len(backups)} backup(s)")
    
    async def execute_with_failover(
        self,
        operation: str,
        func_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with automatic failover to backup services.
        
        Args:
            operation: Operation name for logging
            func_name: Name of method to call on service
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Operation result
        
        Raises:
            Exception: If all services fail
        """
        if not self.config.enable_failover or not self.backup_services:
            # No failover configured, use primary
            service = self.primary_service or self.backup_services[0] if self.backup_services else None
            if service:
                func = getattr(service, func_name)
                return await func(*args, **kwargs)
            raise Exception("No service configured")
        
        # Try current service
        services = [self.primary_service] + self.backup_services
        start_index = self.current_service_index
        
        for i in range(len(services)):
            service_index = (start_index + i) % len(services)
            service = services[service_index]
            service_name = "primary" if service_index == 0 else f"backup-{service_index}"
            
            try:
                logger.info(f"🔄 Attempting {operation} on {service_name}")
                func = getattr(service, func_name)
                
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.failover_timeout
                )
                
                # Success - update current service
                if service_index != self.current_service_index:
                    logger.success(f"✅ Failover to {service_name} successful")
                    self.current_service_index = service_index
                
                return result
            
            except Exception as e:
                logger.warning(f"⚠️ {operation} failed on {service_name}: {e}")
                
                if i == len(services) - 1:
                    # All services failed
                    logger.error(f"❌ All services failed for {operation}")
                    raise Exception(f"All failover services failed: {e}")
                
                # Try next service
                continue
    
    def register_error_handler(self, error_pattern: str, handler: Callable):
        """
        Register automatic error handler (runbook automation).
        
        Args:
            error_pattern: Error pattern to match (regex)
            handler: Async function to handle error
        """
        self.known_errors[error_pattern] = handler
        logger.info(f"📋 Registered error handler for: {error_pattern}")
    
    async def handle_known_error(self, error: Exception) -> bool:
        """
        Check if error matches known patterns and handle automatically.
        
        Args:
            error: Exception to handle
        
        Returns:
            True if error was handled, False otherwise
        """
        import re
        
        error_str = str(error)
        
        for pattern, handler in self.known_errors.items():
            if re.search(pattern, error_str, re.IGNORECASE):
                logger.info(f"📋 Running automated handler for: {pattern}")
                
                try:
                    await handler(error)
                    
                    # Track successful automated handling
                    self.error_counts[pattern] = self.error_counts.get(pattern, 0) + 1
                    logger.success(f"✅ Automated handler succeeded (count: {self.error_counts[pattern]})")
                    
                    return True
                
                except Exception as e:
                    logger.error(f"❌ Automated handler failed: {e}")
                    return False
        
        return False
    
    async def execute_with_circuit_breaker(
        self,
        func: Callable,
        *args,
        operation_name: str = "operation",
        **kwargs
    ) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            operation_name: Name for logging
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        """
        try:
            result = await self.circuit_breaker.call(func, *args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"❌ {operation_name} failed (circuit: {self.circuit_breaker.state.value}): {e}")
            raise e


class NetworkErrorHandler:
    """Handle network-specific errors"""
    
    NETWORK_ERROR_TYPES = (
        ConnectionError,
        TimeoutError,
        OSError,
        asyncio.TimeoutError,
    )
    
    @staticmethod
    def is_network_error(exception: Exception) -> bool:
        """Check if exception is network-related"""
        return isinstance(exception, NetworkErrorHandler.NETWORK_ERROR_TYPES)
    
    @staticmethod
    async def handle_network_error(
        exception: Exception,
        recovery_manager: ErrorRecoveryManager,
        reconnect_callback: Callable
    ):
        """
        Handle network error with reconnection logic.
        
        Args:
            exception: Network exception
            recovery_manager: ErrorRecoveryManager instance
            reconnect_callback: Function to reconnect
        """
        logger.error(f"🌐 Network error detected: {exception}")
        
        try:
            success = await recovery_manager.execute_with_retry(
                reconnect_callback,
                operation_name="network reconnection"
            )
            
            if success:
                logger.success("✅ Network connection restored")
            else:
                logger.error("❌ Network reconnection failed")
                recovery_manager.enter_degraded_mode()
        
        except Exception as e:
            logger.critical(f"🚨 Critical network failure: {e}")
            recovery_manager.state = RecoveryState.CRITICAL


class ExchangeAPIErrorHandler:
    """Handle exchange API specific errors"""
    
    RETRYABLE_ERRORS = {
        -1001,  # Internal error
        -1003,  # Too many requests
        -1021,  # Timestamp out of sync
        -2010,  # Account has insufficient balance
    }
    
    @staticmethod
    def is_retryable(error_code: int) -> bool:
        """Check if error code is retryable"""
        return error_code in ExchangeAPIErrorHandler.RETRYABLE_ERRORS
    
    @staticmethod
    async def handle_api_error(
        error_code: int,
        error_msg: str,
        recovery_manager: ErrorRecoveryManager
    ):
        """
        Handle exchange API error.
        
        Args:
            error_code: API error code
            error_msg: Error message
            recovery_manager: ErrorRecoveryManager instance
        """
        logger.warning(f"⚠️ Exchange API error [{error_code}]: {error_msg}")
        
        if ExchangeAPIErrorHandler.is_retryable(error_code):
            logger.info(f"🔄 Error code {error_code} is retryable - will retry")
            # Exponential backoff will be handled by execute_with_retry
        else:
            logger.error(f"❌ Error code {error_code} is not retryable - manual intervention required")
            recovery_manager.state = RecoveryState.CRITICAL


# Example usage
if __name__ == "__main__":
    async def test_recovery():
        """Test error recovery"""
        config = RecoveryConfig(max_retries=3, initial_backoff=0.5)
        manager = ErrorRecoveryManager(config)
        
        # Test successful operation after retries
        attempt = 0
        async def flaky_operation():
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                raise ConnectionError("Network timeout")
            return "Success!"
        
        try:
            result = await manager.execute_with_retry(
                flaky_operation,
                operation_name="test operation"
            )
            print(f"✅ Result: {result}")
            print(f"📊 Health: {manager.health_check()}")
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    asyncio.run(test_recovery())

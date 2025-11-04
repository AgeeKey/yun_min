"""
Error Recovery Module for YunMin Trading Bot
Handles reconnection, network failures, and graceful degradation.
"""
import asyncio
import time
from typing import Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class RecoveryState(Enum):
    """Recovery state enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RECONNECTING = "reconnecting"
    CRITICAL = "critical"


@dataclass
class RecoveryConfig:
    """Configuration for error recovery"""
    max_retries: int = 5
    initial_backoff: float = 1.0  # seconds
    max_backoff: float = 60.0  # seconds
    backoff_multiplier: float = 2.0
    health_check_interval: float = 30.0  # seconds
    critical_error_threshold: int = 3  # consecutive critical errors


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


class ErrorRecoveryManager:
    """
    Manages error recovery, reconnection logic, and graceful degradation.
    
    Features:
    - Exponential backoff with jitter
    - Automatic reconnection for network errors
    - State recovery from database
    - Circuit breaker pattern
    - Health monitoring
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

"""
Emergency Safety Protocol

Panic button and emergency procedures for the trading bot.
Provides emergency stop, pause trading, and safe mode functionalities.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from loguru import logger
from pathlib import Path
import json


class TradingMode(Enum):
    """Trading bot operational modes."""
    NORMAL = "normal"  # Normal trading
    PAUSED = "paused"  # No new positions, keep existing
    SAFE_MODE = "safe_mode"  # Monitoring only, no trading
    EMERGENCY_STOP = "emergency_stop"  # Close all positions immediately


class EmergencyTrigger(Enum):
    """Types of emergency triggers."""
    MANUAL = "manual"  # Manual trigger by user
    API_RATE_LIMIT = "api_rate_limit"  # API rate limit exceeded
    NETWORK_DISCONNECT = "network_disconnect"  # Network issues
    DATABASE_ERROR = "database_error"  # Database corruption
    EXCESSIVE_LOSSES = "excessive_losses"  # Drawdown threshold
    UNKNOWN_ERROR = "unknown_error"  # Unknown critical error


@dataclass
class EmergencyEvent:
    """Record of an emergency event."""
    timestamp: datetime
    trigger: EmergencyTrigger
    mode_before: TradingMode
    mode_after: TradingMode
    reason: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'trigger': self.trigger.value,
            'mode_before': self.mode_before.value,
            'mode_after': self.mode_after.value,
            'reason': self.reason,
            'metadata': self.metadata
        }


class EmergencySafetyProtocol:
    """
    Emergency safety protocol for trading bot.
    
    Features:
    - Emergency STOP: close all positions immediately
    - Pause trading: stop new positions, keep existing
    - Safe mode: monitoring only, no trading
    - Auto-trigger conditions
    - Event logging and history
    """
    
    def __init__(
        self,
        storage_path: str = "data/emergency",
        auto_trigger_enabled: bool = True,
        network_timeout_threshold: int = 300,  # 5 minutes
        require_confirmation: bool = True
    ):
        """
        Initialize emergency safety protocol.
        
        Args:
            storage_path: Path to store emergency events
            auto_trigger_enabled: Enable automatic emergency triggers
            network_timeout_threshold: Network disconnect threshold in seconds
            require_confirmation: Require confirmation for manual triggers
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.auto_trigger_enabled = auto_trigger_enabled
        self.network_timeout_threshold = network_timeout_threshold
        self.require_confirmation = require_confirmation
        
        # Current state
        self.current_mode = TradingMode.NORMAL
        self.emergency_events: list[EmergencyEvent] = []
        
        # Auto-trigger tracking
        self.network_disconnect_start: Optional[datetime] = None
        self.last_api_call_time: Optional[datetime] = None
        
        # Load history
        self._load_events()
        
        logger.info("EmergencySafetyProtocol initialized in {} mode", self.current_mode.value)
    
    def _save_event(self, event: EmergencyEvent):
        """Save emergency event to disk."""
        file_path = self.storage_path / f"event_{event.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        with open(file_path, 'w') as f:
            json.dump(event.to_dict(), f, indent=2)
    
    def _load_events(self):
        """Load emergency events from disk."""
        if not self.storage_path.exists():
            return
        
        for file_path in sorted(self.storage_path.glob("event_*.json")):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # For now, just track in memory (could reconstruct EmergencyEvent if needed)
                    self.emergency_events.append(data)
            except Exception as e:
                logger.error(f"Failed to load event from {file_path}: {e}")
    
    def get_current_mode(self) -> TradingMode:
        """Get current trading mode."""
        return self.current_mode
    
    def is_trading_allowed(self) -> bool:
        """Check if trading is allowed in current mode."""
        return self.current_mode == TradingMode.NORMAL
    
    def is_new_positions_allowed(self) -> bool:
        """Check if opening new positions is allowed."""
        return self.current_mode in [TradingMode.NORMAL]
    
    def emergency_stop(
        self,
        reason: str,
        trigger: EmergencyTrigger = EmergencyTrigger.MANUAL,
        metadata: Optional[Dict[str, Any]] = None,
        confirmed: bool = False
    ) -> bool:
        """
        Trigger emergency stop - close all positions immediately.
        
        Args:
            reason: Reason for emergency stop
            trigger: Type of trigger
            metadata: Additional metadata
            confirmed: Confirmation flag
            
        Returns:
            True if emergency stop activated, False if cancelled
        """
        if self.require_confirmation and not confirmed and trigger == EmergencyTrigger.MANUAL:
            logger.warning("Emergency stop requires confirmation. Set confirmed=True to proceed.")
            return False
        
        mode_before = self.current_mode
        self.current_mode = TradingMode.EMERGENCY_STOP
        
        event = EmergencyEvent(
            timestamp=datetime.now(),
            trigger=trigger,
            mode_before=mode_before,
            mode_after=TradingMode.EMERGENCY_STOP,
            reason=reason,
            metadata=metadata or {}
        )
        
        self.emergency_events.append(event)
        self._save_event(event)
        
        logger.critical(
            "🚨 EMERGENCY STOP ACTIVATED 🚨\n"
            "Trigger: {}\n"
            "Reason: {}\n"
            "Action: Closing all positions immediately",
            trigger.value, reason
        )
        
        return True
    
    def pause_trading(
        self,
        reason: str,
        trigger: EmergencyTrigger = EmergencyTrigger.MANUAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Pause trading - stop new positions but keep existing ones.
        
        Args:
            reason: Reason for pausing
            trigger: Type of trigger
            metadata: Additional metadata
            
        Returns:
            True if paused successfully
        """
        if self.current_mode == TradingMode.EMERGENCY_STOP:
            logger.error("Cannot pause - system in emergency stop. Must resume first.")
            return False
        
        mode_before = self.current_mode
        self.current_mode = TradingMode.PAUSED
        
        event = EmergencyEvent(
            timestamp=datetime.now(),
            trigger=trigger,
            mode_before=mode_before,
            mode_after=TradingMode.PAUSED,
            reason=reason,
            metadata=metadata or {}
        )
        
        self.emergency_events.append(event)
        self._save_event(event)
        
        logger.warning(
            "⏸️  TRADING PAUSED\n"
            "Reason: {}\n"
            "Action: No new positions will be opened",
            reason
        )
        
        return True
    
    def enable_safe_mode(
        self,
        reason: str,
        trigger: EmergencyTrigger = EmergencyTrigger.MANUAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Enable safe mode - monitoring only, no trading.
        
        Args:
            reason: Reason for safe mode
            trigger: Type of trigger
            metadata: Additional metadata
            
        Returns:
            True if safe mode enabled
        """
        mode_before = self.current_mode
        self.current_mode = TradingMode.SAFE_MODE
        
        event = EmergencyEvent(
            timestamp=datetime.now(),
            trigger=trigger,
            mode_before=mode_before,
            mode_after=TradingMode.SAFE_MODE,
            reason=reason,
            metadata=metadata or {}
        )
        
        self.emergency_events.append(event)
        self._save_event(event)
        
        logger.warning(
            "🛡️  SAFE MODE ENABLED\n"
            "Reason: {}\n"
            "Action: Monitoring only - no trading allowed",
            reason
        )
        
        return True
    
    def resume_trading(
        self,
        confirmed: bool = False
    ) -> bool:
        """
        Resume normal trading.
        
        Args:
            confirmed: Confirmation flag
            
        Returns:
            True if resumed successfully
        """
        if self.require_confirmation and not confirmed:
            logger.warning("Resume requires confirmation. Set confirmed=True to proceed.")
            return False
        
        if self.current_mode == TradingMode.EMERGENCY_STOP:
            logger.warning("System in emergency stop. Review conditions before resuming.")
            if not confirmed:
                return False
        
        mode_before = self.current_mode
        self.current_mode = TradingMode.NORMAL
        
        event = EmergencyEvent(
            timestamp=datetime.now(),
            trigger=EmergencyTrigger.MANUAL,
            mode_before=mode_before,
            mode_after=TradingMode.NORMAL,
            reason="Manual resume",
            metadata={}
        )
        
        self.emergency_events.append(event)
        self._save_event(event)
        
        logger.info(
            "✅ TRADING RESUMED\n"
            "Previous mode: {}\n"
            "Action: Normal trading operations",
            mode_before.value
        )
        
        return True
    
    def check_network_disconnect(self, is_connected: bool):
        """
        Check network connectivity and trigger emergency if needed.
        
        Args:
            is_connected: Current network connection status
        """
        if not self.auto_trigger_enabled:
            return
        
        now = datetime.now()
        
        if not is_connected:
            if self.network_disconnect_start is None:
                self.network_disconnect_start = now
                logger.warning("Network disconnect detected")
            else:
                # Check if exceeded threshold
                disconnect_duration = (now - self.network_disconnect_start).total_seconds()
                if disconnect_duration >= self.network_timeout_threshold:
                    if self.current_mode != TradingMode.EMERGENCY_STOP:
                        self.emergency_stop(
                            reason=f"Network disconnected for {disconnect_duration:.0f} seconds",
                            trigger=EmergencyTrigger.NETWORK_DISCONNECT,
                            metadata={'disconnect_duration': disconnect_duration},
                            confirmed=True
                        )
        else:
            # Connected - reset
            if self.network_disconnect_start:
                logger.info("Network connection restored")
                self.network_disconnect_start = None
    
    def check_api_rate_limit(self, rate_limit_exceeded: bool):
        """
        Check API rate limiting and trigger pause if needed.
        
        Args:
            rate_limit_exceeded: Whether rate limit was exceeded
        """
        if not self.auto_trigger_enabled:
            return
        
        if rate_limit_exceeded:
            if self.current_mode == TradingMode.NORMAL:
                self.pause_trading(
                    reason="API rate limit exceeded",
                    trigger=EmergencyTrigger.API_RATE_LIMIT,
                    metadata={'timestamp': datetime.now().isoformat()}
                )
    
    def check_database_integrity(self, is_corrupted: bool):
        """
        Check database integrity and trigger emergency if corrupted.
        
        Args:
            is_corrupted: Whether database is corrupted
        """
        if not self.auto_trigger_enabled:
            return
        
        if is_corrupted:
            if self.current_mode != TradingMode.EMERGENCY_STOP:
                self.emergency_stop(
                    reason="Database corruption detected",
                    trigger=EmergencyTrigger.DATABASE_ERROR,
                    metadata={'timestamp': datetime.now().isoformat()},
                    confirmed=True
                )
    
    def check_excessive_losses(self, drawdown_percentage: float, threshold: float = 7.0):
        """
        Check for excessive losses and trigger emergency if threshold exceeded.
        
        Args:
            drawdown_percentage: Current drawdown percentage
            threshold: Drawdown threshold for emergency stop (default: 7%)
        """
        if not self.auto_trigger_enabled:
            return
        
        if drawdown_percentage >= threshold:
            if self.current_mode != TradingMode.EMERGENCY_STOP:
                self.emergency_stop(
                    reason=f"Excessive losses: {drawdown_percentage:.2f}% drawdown",
                    trigger=EmergencyTrigger.EXCESSIVE_LOSSES,
                    metadata={
                        'drawdown_percentage': drawdown_percentage,
                        'threshold': threshold
                    },
                    confirmed=True
                )
    
    def get_recent_events(self, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Get recent emergency events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        return self.emergency_events[-limit:]
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get current status summary.
        
        Returns:
            Status dictionary
        """
        return {
            'current_mode': self.current_mode.value,
            'trading_allowed': self.is_trading_allowed(),
            'new_positions_allowed': self.is_new_positions_allowed(),
            'auto_trigger_enabled': self.auto_trigger_enabled,
            'require_confirmation': self.require_confirmation,
            'total_events': len(self.emergency_events),
            'recent_events': [
                {
                    'timestamp': e.get('timestamp') if isinstance(e, dict) else e.timestamp.isoformat(),
                    'trigger': e.get('trigger') if isinstance(e, dict) else e.trigger.value,
                    'mode_after': e.get('mode_after') if isinstance(e, dict) else e.mode_after.value,
                    'reason': e.get('reason') if isinstance(e, dict) else e.reason,
                }
                for e in self.emergency_events[-5:]
            ]
        }

"""
Tests for Emergency Safety Protocol
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import shutil
from yunmin.core.emergency import (
    EmergencySafetyProtocol,
    TradingMode,
    EmergencyTrigger,
    EmergencyEvent
)


@pytest.fixture
def temp_storage_path():
    """Create temporary directory for emergency data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def protocol(temp_storage_path):
    """Create an emergency safety protocol instance."""
    return EmergencySafetyProtocol(
        storage_path=temp_storage_path,
        require_confirmation=False  # Disable for testing
    )


class TestEmergencyEvent:
    """Test EmergencyEvent dataclass."""
    
    def test_emergency_event_creation(self):
        """Test creating emergency event."""
        event = EmergencyEvent(
            timestamp=datetime.now(),
            trigger=EmergencyTrigger.MANUAL,
            mode_before=TradingMode.NORMAL,
            mode_after=TradingMode.PAUSED,
            reason="Test",
            metadata={'key': 'value'}
        )
        
        assert event.trigger == EmergencyTrigger.MANUAL
        assert event.mode_before == TradingMode.NORMAL
        assert event.mode_after == TradingMode.PAUSED
    
    def test_emergency_event_to_dict(self):
        """Test event serialization."""
        event = EmergencyEvent(
            timestamp=datetime.now(),
            trigger=EmergencyTrigger.MANUAL,
            mode_before=TradingMode.NORMAL,
            mode_after=TradingMode.PAUSED,
            reason="Test",
            metadata={}
        )
        
        data = event.to_dict()
        
        assert 'timestamp' in data
        assert data['trigger'] == 'manual'
        assert data['mode_before'] == 'normal'
        assert data['mode_after'] == 'paused'


class TestEmergencySafetyProtocol:
    """Test EmergencySafetyProtocol functionality."""
    
    def test_initialization(self, protocol):
        """Test protocol initialization."""
        assert protocol.current_mode == TradingMode.NORMAL
        assert protocol.is_trading_allowed()
        assert protocol.is_new_positions_allowed()
        assert protocol.auto_trigger_enabled
    
    def test_emergency_stop(self, protocol):
        """Test emergency stop activation."""
        success = protocol.emergency_stop(
            reason="Test emergency",
            confirmed=True
        )
        
        assert success
        assert protocol.current_mode == TradingMode.EMERGENCY_STOP
        assert not protocol.is_trading_allowed()
        assert not protocol.is_new_positions_allowed()
        assert len(protocol.emergency_events) == 1
    
    def test_emergency_stop_requires_confirmation(self, temp_storage_path):
        """Test that emergency stop requires confirmation."""
        protocol = EmergencySafetyProtocol(
            storage_path=temp_storage_path,
            require_confirmation=True
        )
        
        # Without confirmation
        success = protocol.emergency_stop(
            reason="Test",
            confirmed=False
        )
        
        assert not success
        assert protocol.current_mode == TradingMode.NORMAL
    
    def test_emergency_stop_auto_trigger(self, protocol):
        """Test emergency stop with auto-trigger."""
        success = protocol.emergency_stop(
            reason="Network failure",
            trigger=EmergencyTrigger.NETWORK_DISCONNECT,
            confirmed=True
        )
        
        assert success
        event = protocol.emergency_events[0]
        assert event.trigger == EmergencyTrigger.NETWORK_DISCONNECT
    
    def test_pause_trading(self, protocol):
        """Test pause trading."""
        success = protocol.pause_trading(
            reason="Manual pause"
        )
        
        assert success
        assert protocol.current_mode == TradingMode.PAUSED
        assert not protocol.is_trading_allowed()
        assert not protocol.is_new_positions_allowed()
    
    def test_pause_from_emergency_stop_fails(self, protocol):
        """Test cannot pause when in emergency stop."""
        protocol.emergency_stop(reason="Test", confirmed=True)
        
        success = protocol.pause_trading(reason="Try to pause")
        
        assert not success
        assert protocol.current_mode == TradingMode.EMERGENCY_STOP
    
    def test_enable_safe_mode(self, protocol):
        """Test enabling safe mode."""
        success = protocol.enable_safe_mode(
            reason="Testing safe mode"
        )
        
        assert success
        assert protocol.current_mode == TradingMode.SAFE_MODE
        assert not protocol.is_trading_allowed()
        assert not protocol.is_new_positions_allowed()
    
    def test_resume_trading_from_paused(self, protocol):
        """Test resuming trading from paused state."""
        # First pause
        protocol.pause_trading(reason="Test")
        assert protocol.current_mode == TradingMode.PAUSED
        
        # Then resume
        success = protocol.resume_trading(confirmed=True)
        
        assert success
        assert protocol.current_mode == TradingMode.NORMAL
        assert protocol.is_trading_allowed()
    
    def test_resume_trading_from_safe_mode(self, protocol):
        """Test resuming from safe mode."""
        protocol.enable_safe_mode(reason="Test")
        
        success = protocol.resume_trading(confirmed=True)
        
        assert success
        assert protocol.current_mode == TradingMode.NORMAL
    
    def test_resume_from_emergency_requires_confirmation(self, temp_storage_path):
        """Test resuming from emergency stop requires confirmation."""
        protocol = EmergencySafetyProtocol(
            storage_path=temp_storage_path,
            require_confirmation=True
        )
        
        protocol.emergency_stop(reason="Test", confirmed=True)
        
        # Try to resume without confirmation
        success = protocol.resume_trading(confirmed=False)
        
        assert not success
        assert protocol.current_mode == TradingMode.EMERGENCY_STOP
    
    def test_check_network_disconnect(self, protocol):
        """Test network disconnect auto-trigger."""
        # Simulate short disconnect (shouldn't trigger)
        protocol.check_network_disconnect(is_connected=False)
        assert protocol.current_mode == TradingMode.NORMAL
        
        # Simulate network restored
        protocol.check_network_disconnect(is_connected=True)
        assert protocol.network_disconnect_start is None
    
    def test_check_network_disconnect_threshold(self, temp_storage_path):
        """Test network disconnect exceeds threshold."""
        import time
        protocol = EmergencySafetyProtocol(
            storage_path=temp_storage_path,
            network_timeout_threshold=0  # Immediate trigger for testing
        )
        
        # Simulate disconnect - first call sets the start time
        protocol.check_network_disconnect(is_connected=False)
        assert protocol.current_mode == TradingMode.NORMAL  # Not triggered yet
        
        # Wait a tiny bit and check again
        time.sleep(0.01)
        protocol.check_network_disconnect(is_connected=False)
        
        # Should trigger emergency stop now
        assert protocol.current_mode == TradingMode.EMERGENCY_STOP
    
    def test_check_api_rate_limit(self, protocol):
        """Test API rate limit auto-trigger."""
        protocol.check_api_rate_limit(rate_limit_exceeded=True)
        
        assert protocol.current_mode == TradingMode.PAUSED
        
        # Should have logged event
        assert len(protocol.emergency_events) == 1
        assert protocol.emergency_events[0].trigger == EmergencyTrigger.API_RATE_LIMIT
    
    def test_check_database_integrity(self, protocol):
        """Test database integrity check."""
        protocol.check_database_integrity(is_corrupted=True)
        
        assert protocol.current_mode == TradingMode.EMERGENCY_STOP
        assert len(protocol.emergency_events) == 1
        assert protocol.emergency_events[0].trigger == EmergencyTrigger.DATABASE_ERROR
    
    def test_check_excessive_losses(self, protocol):
        """Test excessive losses trigger."""
        # 8% drawdown should trigger emergency (default threshold 7%)
        protocol.check_excessive_losses(drawdown_percentage=8.0)
        
        assert protocol.current_mode == TradingMode.EMERGENCY_STOP
        assert len(protocol.emergency_events) == 1
        assert protocol.emergency_events[0].trigger == EmergencyTrigger.EXCESSIVE_LOSSES
    
    def test_check_excessive_losses_below_threshold(self, protocol):
        """Test losses below threshold don't trigger."""
        protocol.check_excessive_losses(drawdown_percentage=5.0)
        
        assert protocol.current_mode == TradingMode.NORMAL
        assert len(protocol.emergency_events) == 0
    
    def test_auto_trigger_disabled(self, temp_storage_path):
        """Test auto-triggers are disabled when configured."""
        protocol = EmergencySafetyProtocol(
            storage_path=temp_storage_path,
            auto_trigger_enabled=False
        )
        
        # Try to trigger with various conditions
        protocol.check_network_disconnect(is_connected=False)
        protocol.check_api_rate_limit(rate_limit_exceeded=True)
        protocol.check_excessive_losses(drawdown_percentage=10.0)
        
        # Should remain in normal mode
        assert protocol.current_mode == TradingMode.NORMAL
        assert len(protocol.emergency_events) == 0
    
    def test_get_recent_events(self, protocol):
        """Test getting recent events."""
        # Create multiple events
        for i in range(15):
            protocol.pause_trading(reason=f"Test {i}")
            protocol.resume_trading(confirmed=True)
        
        recent = protocol.get_recent_events(limit=5)
        assert len(recent) <= 5
    
    def test_get_status_summary(self, protocol):
        """Test status summary."""
        protocol.pause_trading(reason="Test")
        
        status = protocol.get_status_summary()
        
        assert status['current_mode'] == 'paused'
        assert status['trading_allowed'] is False
        assert status['new_positions_allowed'] is False
        assert status['auto_trigger_enabled'] is True
        assert status['total_events'] == 1
        assert len(status['recent_events']) > 0
    
    def test_event_persistence(self, temp_storage_path):
        """Test event persistence across instances."""
        # Create first instance and trigger emergency
        protocol1 = EmergencySafetyProtocol(storage_path=temp_storage_path)
        protocol1.emergency_stop(reason="Test", confirmed=True)
        
        # Create second instance
        protocol2 = EmergencySafetyProtocol(storage_path=temp_storage_path)
        
        # Should have loaded the event
        assert len(protocol2.emergency_events) == 1
    
    def test_multiple_emergency_triggers(self, protocol):
        """Test handling multiple emergency triggers."""
        # Trigger various emergencies
        protocol.pause_trading(reason="First event")
        protocol.resume_trading(confirmed=True)
        protocol.enable_safe_mode(reason="Second event")
        protocol.resume_trading(confirmed=True)
        protocol.emergency_stop(reason="Third event", confirmed=True)
        
        assert len(protocol.emergency_events) == 5  # pause, resume, safe, resume, stop
        
        status = protocol.get_status_summary()
        assert status['total_events'] == 5
    
    def test_event_metadata(self, protocol):
        """Test that event metadata is stored correctly."""
        metadata = {
            'drawdown_percentage': 8.5,
            'threshold': 7.0,
            'additional_info': 'test'
        }
        
        protocol.emergency_stop(
            reason="Test with metadata",
            metadata=metadata,
            confirmed=True
        )
        
        event = protocol.emergency_events[0]
        assert event.metadata == metadata
    
    def test_trading_mode_transitions(self, protocol):
        """Test all valid mode transitions."""
        # Normal -> Paused
        protocol.pause_trading(reason="Test")
        assert protocol.current_mode == TradingMode.PAUSED
        
        # Paused -> Normal
        protocol.resume_trading(confirmed=True)
        assert protocol.current_mode == TradingMode.NORMAL
        
        # Normal -> Safe Mode
        protocol.enable_safe_mode(reason="Test")
        assert protocol.current_mode == TradingMode.SAFE_MODE
        
        # Safe Mode -> Normal
        protocol.resume_trading(confirmed=True)
        assert protocol.current_mode == TradingMode.NORMAL
        
        # Normal -> Emergency Stop
        protocol.emergency_stop(reason="Test", confirmed=True)
        assert protocol.current_mode == TradingMode.EMERGENCY_STOP
        
        # Emergency Stop -> Normal (with confirmation)
        protocol.resume_trading(confirmed=True)
        assert protocol.current_mode == TradingMode.NORMAL

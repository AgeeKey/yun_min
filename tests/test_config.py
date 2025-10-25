"""
Tests for Configuration System
"""

import pytest
import tempfile
import os
from yunmin.core.config import (
    YunMinConfig,
    ExchangeConfig,
    TradingConfig,
    RiskConfig,
    load_config,
    save_config
)


class TestConfigClasses:
    """Test configuration classes."""
    
    def test_exchange_config_defaults(self):
        """Test exchange config defaults."""
        config = ExchangeConfig()
        
        assert config.name == "binance"
        assert config.testnet is True
        assert config.enable_rate_limit is True
        
    def test_trading_config_defaults(self):
        """Test trading config defaults."""
        config = TradingConfig()
        
        assert config.mode == "dry_run"
        assert config.symbol == "BTC/USDT"
        assert config.timeframe == "5m"
        assert config.initial_capital == 10000.0
        
    def test_risk_config_defaults(self):
        """Test risk config defaults."""
        config = RiskConfig()
        
        assert config.max_position_size == 0.1
        assert config.max_leverage == 3.0
        assert config.enable_circuit_breaker is True
        
    def test_yunmin_config_initialization(self):
        """Test main config initialization."""
        config = YunMinConfig()
        
        assert config.exchange is not None
        assert config.trading is not None
        assert config.risk is not None
        assert config.strategy is not None


class TestConfigPersistence:
    """Test config loading and saving."""
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_file = f.name
            
        try:
            # Create config
            config = YunMinConfig()
            config.trading.symbol = "ETH/USDT"
            config.risk.max_leverage = 5.0
            
            # Save config
            save_config(config, temp_file)
            assert os.path.exists(temp_file)
            
            # Load config
            loaded_config = load_config(temp_file)
            
            # Verify
            assert loaded_config.trading.symbol == "ETH/USDT"
            assert loaded_config.risk.max_leverage == 5.0
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                
    def test_load_nonexistent_config(self):
        """Test loading non-existent config file."""
        # Should return default config
        config = load_config("nonexistent_file.yaml")
        assert config is not None
        assert config.trading.mode == "dry_run"

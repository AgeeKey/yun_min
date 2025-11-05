"""
Tests for Configuration Wizard.
"""

import pytest
from pathlib import Path
import yaml
from unittest.mock import patch, MagicMock
from yunmin.cli_wizard import ConfigWizard


class TestConfigWizard:
    """Test suite for ConfigWizard class."""
    
    def test_wizard_initialization(self):
        """Test wizard initializes correctly."""
        wizard = ConfigWizard()
        assert wizard.config == {}
        assert isinstance(wizard.EXCHANGES, dict)
        assert isinstance(wizard.TRADING_PAIRS, list)
        assert isinstance(wizard.RISK_PROFILES, dict)
    
    def test_exchanges_available(self):
        """Test exchange options are defined."""
        wizard = ConfigWizard()
        assert "binance" in wizard.EXCHANGES
        assert "binance_testnet" in wizard.EXCHANGES
    
    def test_trading_pairs_available(self):
        """Test trading pairs are defined."""
        wizard = ConfigWizard()
        assert "BTC/USDT" in wizard.TRADING_PAIRS
        assert "ETH/USDT" in wizard.TRADING_PAIRS
        assert len(wizard.TRADING_PAIRS) >= 5
    
    def test_risk_profiles_structure(self):
        """Test risk profile structure."""
        wizard = ConfigWizard()
        
        for profile_name, settings in wizard.RISK_PROFILES.items():
            assert "max_position_size" in settings
            assert "max_leverage" in settings
            assert "max_daily_drawdown" in settings
            assert "stop_loss_pct" in settings
            assert "take_profit_pct" in settings
            
            # Validate ranges
            assert 0 < settings["max_position_size"] <= 1.0
            assert 1.0 <= settings["max_leverage"] <= 10.0
            assert 0 < settings["stop_loss_pct"] <= 0.1
    
    def test_conservative_profile_safest(self):
        """Test conservative profile has safest settings."""
        wizard = ConfigWizard()
        
        conservative = wizard.RISK_PROFILES["conservative"]
        moderate = wizard.RISK_PROFILES["moderate"]
        aggressive = wizard.RISK_PROFILES["aggressive"]
        
        # Conservative should have smallest position size
        assert conservative["max_position_size"] < moderate["max_position_size"]
        assert moderate["max_position_size"] < aggressive["max_position_size"]
        
        # Conservative should have lowest leverage
        assert conservative["max_leverage"] <= moderate["max_leverage"]
        assert moderate["max_leverage"] <= aggressive["max_leverage"]
    
    def test_strategy_types_available(self):
        """Test strategy types are defined."""
        wizard = ConfigWizard()
        assert "ai_v2" in wizard.STRATEGY_TYPES
        assert "ai_v3" in wizard.STRATEGY_TYPES
        assert "rule_based" in wizard.STRATEGY_TYPES
    
    def test_ai_providers_available(self):
        """Test AI providers are defined."""
        wizard = ConfigWizard()
        assert "groq" in wizard.AI_PROVIDERS
        assert "openrouter" in wizard.AI_PROVIDERS
        assert "openai" in wizard.AI_PROVIDERS
        assert "grok" in wizard.AI_PROVIDERS
    
    def test_get_strategy_config_rule_based(self):
        """Test rule-based strategy configuration."""
        wizard = ConfigWizard()
        wizard.config["strategy_type"] = "rule_based"
        
        strategy_config = wizard._get_strategy_config()
        
        assert strategy_config["name"] == "ema_crossover"
        assert "fast_ema" in strategy_config
        assert "slow_ema" in strategy_config
        assert "rsi_period" in strategy_config
    
    def test_get_strategy_config_ai(self):
        """Test AI strategy configuration."""
        wizard = ConfigWizard()
        wizard.config["strategy_type"] = "ai_v3"
        
        strategy_config = wizard._get_strategy_config()
        
        assert strategy_config["name"] == "ai_v3"
        assert "lookback_periods" in strategy_config
        assert "confidence_threshold" in strategy_config
    
    def test_get_llm_config_with_provider(self):
        """Test LLM configuration with AI provider."""
        wizard = ConfigWizard()
        wizard.config["ai_provider"] = "groq"
        wizard.config["explain_trades"] = True
        
        llm_config = wizard._get_llm_config()
        
        assert llm_config["enabled"] is True
        assert llm_config["provider"] == "groq"
        assert llm_config["explain_trades"] is True
    
    def test_get_llm_config_without_provider(self):
        """Test LLM configuration without AI provider."""
        wizard = ConfigWizard()
        
        llm_config = wizard._get_llm_config()
        
        assert llm_config["enabled"] is False
        assert "provider" in llm_config
    
    def test_get_notification_config(self):
        """Test notification configuration."""
        wizard = ConfigWizard()
        wizard.config["alert_channels"] = ["telegram", "email"]
        
        notif_config = wizard._get_notification_config()
        
        assert notif_config["telegram_enabled"] is True
        assert notif_config["email_enabled"] is True
        assert notif_config["desktop_enabled"] is False
    
    def test_get_notification_config_empty(self):
        """Test notification configuration with no channels."""
        wizard = ConfigWizard()
        wizard.config["alert_channels"] = []
        
        notif_config = wizard._get_notification_config()
        
        assert notif_config["telegram_enabled"] is False
        assert notif_config["email_enabled"] is False
        assert notif_config["desktop_enabled"] is False
    
    @patch('yunmin.cli_wizard.questionary')
    def test_select_exchange_testnet(self, mock_questionary):
        """Test exchange selection (testnet)."""
        mock_select = MagicMock()
        mock_select.ask.return_value = "binance_testnet"
        mock_questionary.select.return_value = mock_select
        
        wizard = ConfigWizard()
        wizard._select_exchange()
        
        assert wizard.config["exchange"]["name"] == "binance"
        assert wizard.config["exchange"]["testnet"] is True
        assert wizard.config["exchange"]["enable_rate_limit"] is True
    
    @patch('yunmin.cli_wizard.questionary')
    def test_select_exchange_live(self, mock_questionary):
        """Test exchange selection (live)."""
        mock_select = MagicMock()
        mock_select.ask.return_value = "binance"
        mock_questionary.select.return_value = mock_select
        
        wizard = ConfigWizard()
        wizard._select_exchange()
        
        assert wizard.config["exchange"]["name"] == "binance"
        assert wizard.config["exchange"]["testnet"] is False
    
    @patch('yunmin.cli_wizard.questionary')
    def test_select_trading_pair_preset(self, mock_questionary):
        """Test trading pair selection from presets."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False  # Don't use custom
        
        mock_select = MagicMock()
        mock_select.ask.return_value = "ETH/USDT"
        
        mock_questionary.confirm.return_value = mock_confirm
        mock_questionary.select.return_value = mock_select
        
        wizard = ConfigWizard()
        wizard._select_trading_pair()
        
        assert wizard.config["trading_pair"] == "ETH/USDT"
    
    @patch('yunmin.cli_wizard.questionary')
    def test_select_trading_pair_custom(self, mock_questionary):
        """Test custom trading pair selection."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True  # Use custom
        
        mock_text = MagicMock()
        mock_text.ask.return_value = "MATIC/USDT"
        
        mock_questionary.confirm.return_value = mock_confirm
        mock_questionary.text.return_value = mock_text
        
        wizard = ConfigWizard()
        wizard._select_trading_pair()
        
        assert wizard.config["trading_pair"] == "MATIC/USDT"
    
    @patch('yunmin.cli_wizard.questionary')
    def test_set_initial_capital(self, mock_questionary):
        """Test setting initial capital."""
        mock_text = MagicMock()
        mock_text.ask.return_value = "15000"
        mock_questionary.text.return_value = mock_text
        
        wizard = ConfigWizard()
        wizard._set_initial_capital()
        
        assert wizard.config["initial_capital"] == 15000.0
    
    @patch('yunmin.cli_wizard.questionary')
    def test_select_risk_profile(self, mock_questionary):
        """Test risk profile selection."""
        mock_select = MagicMock()
        mock_select.ask.return_value = "moderate"
        mock_questionary.select.return_value = mock_select
        
        wizard = ConfigWizard()
        wizard._select_risk_profile()
        
        assert wizard.config["risk_profile"] == "moderate"
        assert "risk_settings" in wizard.config
        assert wizard.config["risk_settings"]["max_position_size"] == 0.08
    
    @patch('yunmin.cli_wizard.questionary')
    def test_select_strategy(self, mock_questionary):
        """Test strategy selection."""
        mock_select = MagicMock()
        mock_select.ask.return_value = "ai_v3"
        mock_questionary.select.return_value = mock_select
        
        wizard = ConfigWizard()
        wizard._select_strategy()
        
        assert wizard.config["strategy_type"] == "ai_v3"
    
    @patch('yunmin.cli_wizard.questionary')
    def test_select_ai_provider(self, mock_questionary):
        """Test AI provider selection."""
        mock_select = MagicMock()
        mock_select.ask.return_value = "groq"
        
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True
        
        mock_questionary.select.return_value = mock_select
        mock_questionary.confirm.return_value = mock_confirm
        
        wizard = ConfigWizard()
        wizard._select_ai_provider()
        
        assert wizard.config["ai_provider"] == "groq"
        assert wizard.config["explain_trades"] is True
    
    @patch('yunmin.cli_wizard.questionary')
    def test_select_position_sizing(self, mock_questionary):
        """Test position sizing method selection."""
        mock_select = MagicMock()
        mock_select.ask.return_value = "dynamic"
        mock_questionary.select.return_value = mock_select
        
        wizard = ConfigWizard()
        wizard._select_position_sizing()
        
        assert wizard.config["position_sizing"] == "dynamic"
    
    @patch('yunmin.cli_wizard.questionary')
    def test_select_alert_channels(self, mock_questionary):
        """Test alert channels selection."""
        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = ["telegram", "desktop"]
        mock_questionary.checkbox.return_value = mock_checkbox
        
        wizard = ConfigWizard()
        wizard._select_alert_channels()
        
        assert "telegram" in wizard.config["alert_channels"]
        assert "desktop" in wizard.config["alert_channels"]
        assert len(wizard.config["alert_channels"]) == 2
    
    def test_generate_config_structure(self, tmp_path):
        """Test generated configuration structure."""
        wizard = ConfigWizard()
        
        # Set up minimal config
        wizard.config = {
            "exchange": {"name": "binance", "testnet": True, "enable_rate_limit": True},
            "trading_pair": "BTC/USDT",
            "initial_capital": 10000.0,
            "risk_profile": "moderate",
            "risk_settings": wizard.RISK_PROFILES["moderate"],
            "strategy_type": "ai_v3",
            "ai_provider": "groq",
            "explain_trades": True,
            "position_sizing": "fixed",
            "alert_channels": ["telegram"]
        }
        
        # Change to tmp_path for testing
        import os
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            # Generate config
            config_path = wizard._generate_config()
            
            # Check that a config path was returned
            assert config_path is not None
            assert "strategy_moderate" in config_path
            
            # Verify file exists
            assert Path(config_path).exists()
            
            # Read and verify structure
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                assert "exchange" in config_data
                assert "trading" in config_data
                assert "risk" in config_data
        finally:
            os.chdir(original_dir)
    
    def test_write_yaml_with_comments(self, tmp_path):
        """Test YAML writing with comments."""
        wizard = ConfigWizard()
        
        test_file = tmp_path / "test.yaml"
        data = {
            "# Comment line": None,
            "key1": "value1",
            "key2": {"nested": "value"}
        }
        
        with open(test_file, 'w') as f:
            wizard._write_yaml_with_comments(f, data)
        
        # Read back and verify
        content = test_file.read_text()
        assert "# Comment line" in content
        assert "key1" in content
        assert "key2" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

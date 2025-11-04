"""
Strategy Configuration Wizard for YunMin Trading Bot

Interactive CLI wizard to help users configure trading strategies without
manually editing YAML files.
"""

import questionary
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from datetime import datetime


class ConfigWizard:
    """
    Interactive configuration wizard for YunMin trading bot.
    
    Guides users through setting up their trading configuration with
    validation and best practices built in.
    """
    
    EXCHANGES = {
        "binance": "Binance (Live)",
        "binance_testnet": "Binance Testnet (Safe for testing)"
    }
    
    TRADING_PAIRS = [
        "BTC/USDT",
        "ETH/USDT",
        "BNB/USDT",
        "SOL/USDT",
        "XRP/USDT",
        "ADA/USDT",
        "DOGE/USDT"
    ]
    
    RISK_PROFILES = {
        "conservative": {
            "max_position_size": 0.05,  # 5% per position
            "max_leverage": 1.5,
            "max_daily_drawdown": 0.03,  # 3%
            "stop_loss_pct": 0.02,  # 2%
            "take_profit_pct": 0.03  # 3%
        },
        "moderate": {
            "max_position_size": 0.08,  # 8% per position
            "max_leverage": 2.0,
            "max_daily_drawdown": 0.04,  # 4%
            "stop_loss_pct": 0.025,  # 2.5%
            "take_profit_pct": 0.04  # 4%
        },
        "aggressive": {
            "max_position_size": 0.12,  # 12% per position
            "max_leverage": 3.0,
            "max_daily_drawdown": 0.06,  # 6%
            "stop_loss_pct": 0.03,  # 3%
            "take_profit_pct": 0.05  # 5%
        }
    }
    
    STRATEGY_TYPES = {
        "ai_v2": "AI Strategy V2 (Multi-model with basic risk management)",
        "ai_v3": "AI Strategy V3 (Advanced AI with enhanced features)",
        "rule_based": "Rule-based (EMA crossover with RSI)"
    }
    
    AI_PROVIDERS = {
        "groq": "Groq (Fast, Llama 3.3 70B)",
        "openrouter": "OpenRouter (Llama 3.3 70B)",
        "openai": "OpenAI (GPT-4o-mini)",
        "grok": "Grok (X.AI)"
    }
    
    POSITION_SIZING_METHODS = {
        "fixed": "Fixed percentage of capital",
        "dynamic": "Dynamic based on volatility and performance"
    }
    
    ALERT_CHANNELS = {
        "telegram": "Telegram notifications",
        "email": "Email notifications",
        "desktop": "Desktop notifications"
    }
    
    def __init__(self):
        """Initialize the configuration wizard."""
        self.config: Dict[str, Any] = {}
    
    def run(self) -> Optional[str]:
        """
        Run the interactive configuration wizard.
        
        Returns:
            Path to the generated config file, or None if cancelled
        """
        print("\n" + "=" * 60)
        print("🚀 YunMin Trading Bot - Configuration Wizard")
        print("=" * 60)
        print("\nThis wizard will help you set up your trading strategy")
        print("in just a few minutes. Let's get started!\n")
        
        try:
            # Step 1: Exchange selection
            self._select_exchange()
            
            # Step 2: Trading pair
            self._select_trading_pair()
            
            # Step 3: Initial capital
            self._set_initial_capital()
            
            # Step 4: Risk tolerance
            self._select_risk_profile()
            
            # Step 5: Strategy type
            self._select_strategy()
            
            # Step 6: AI provider (if AI strategy selected)
            if self.config.get("strategy_type") in ["ai_v2", "ai_v3"]:
                self._select_ai_provider()
            
            # Step 7: Position sizing method
            self._select_position_sizing()
            
            # Step 8: Alert channels
            self._select_alert_channels()
            
            # Preview configuration
            if not self._preview_and_confirm():
                print("\n❌ Configuration cancelled")
                return None
            
            # Generate and save configuration
            config_path = self._generate_config()
            
            print(f"\n✅ Configuration saved to: {config_path}")
            print(f"\n🚀 You can now run the bot with:")
            print(f"   yunmin run --config {config_path}")
            
            return config_path
            
        except KeyboardInterrupt:
            print("\n\n❌ Wizard cancelled by user")
            return None
    
    def _select_exchange(self):
        """Select exchange to trade on."""
        exchange = questionary.select(
            "Which exchange would you like to use?",
            choices=[
                questionary.Choice(
                    title=f"{name} ({'Recommended for beginners' if 'testnet' in key.lower() else 'For experienced traders'})",
                    value=key
                )
                for key, name in self.EXCHANGES.items()
            ],
            default="binance_testnet"
        ).ask()
        
        self.config["exchange"] = {
            "name": "binance",
            "testnet": "testnet" in exchange.lower(),
            "enable_rate_limit": True
        }
    
    def _select_trading_pair(self):
        """Select trading pair."""
        # First ask if they want a custom pair
        use_custom = questionary.confirm(
            "Do you want to use a custom trading pair?",
            default=False
        ).ask()
        
        if use_custom:
            pair = questionary.text(
                "Enter trading pair (e.g., BTC/USDT):",
                validate=lambda text: len(text) > 0 and "/" in text
            ).ask()
        else:
            pair = questionary.select(
                "Select a trading pair:",
                choices=self.TRADING_PAIRS,
                default="BTC/USDT"
            ).ask()
        
        self.config["trading_pair"] = pair
    
    def _set_initial_capital(self):
        """Set initial capital amount."""
        capital = questionary.text(
            "Enter your initial capital (USD):",
            default="10000",
            validate=lambda text: text.replace('.', '').isdigit() and float(text) > 0
        ).ask()
        
        self.config["initial_capital"] = float(capital)
    
    def _select_risk_profile(self):
        """Select risk tolerance profile."""
        profile = questionary.select(
            "Select your risk tolerance:",
            choices=[
                questionary.Choice(
                    title="Conservative - Lower risk, smaller positions (Recommended for beginners)",
                    value="conservative"
                ),
                questionary.Choice(
                    title="Moderate - Balanced risk/reward",
                    value="moderate"
                ),
                questionary.Choice(
                    title="Aggressive - Higher risk, larger positions (For experienced traders only)",
                    value="aggressive"
                )
            ],
            default="moderate"
        ).ask()
        
        self.config["risk_profile"] = profile
        self.config["risk_settings"] = self.RISK_PROFILES[profile]
    
    def _select_strategy(self):
        """Select trading strategy type."""
        strategy = questionary.select(
            "Select your trading strategy:",
            choices=[
                questionary.Choice(
                    title=desc,
                    value=key
                )
                for key, desc in self.STRATEGY_TYPES.items()
            ],
            default="ai_v3"
        ).ask()
        
        self.config["strategy_type"] = strategy
    
    def _select_ai_provider(self):
        """Select AI provider for AI strategies."""
        provider = questionary.select(
            "Select AI/LLM provider:",
            choices=[
                questionary.Choice(
                    title=desc,
                    value=key
                )
                for key, desc in self.AI_PROVIDERS.items()
            ],
            default="groq"
        ).ask()
        
        self.config["ai_provider"] = provider
        
        # Ask if they want to enable explanations
        explain = questionary.confirm(
            "Enable trade explanations? (AI will explain each decision)",
            default=True
        ).ask()
        
        self.config["explain_trades"] = explain
    
    def _select_position_sizing(self):
        """Select position sizing method."""
        method = questionary.select(
            "Select position sizing method:",
            choices=[
                questionary.Choice(
                    title=desc,
                    value=key
                )
                for key, desc in self.POSITION_SIZING_METHODS.items()
            ],
            default="fixed"
        ).ask()
        
        self.config["position_sizing"] = method
    
    def _select_alert_channels(self):
        """Select alert/notification channels."""
        channels = questionary.checkbox(
            "Select notification channels (use space to select, enter to confirm):",
            choices=[
                questionary.Choice(
                    title=desc,
                    value=key
                )
                for key, desc in self.ALERT_CHANNELS.items()
            ]
        ).ask()
        
        self.config["alert_channels"] = channels if channels else []
    
    def _preview_and_confirm(self) -> bool:
        """Show configuration preview and ask for confirmation."""
        print("\n" + "=" * 60)
        print("📋 Configuration Preview")
        print("=" * 60)
        
        # Display key settings
        print(f"\n Exchange:        {'Binance Testnet' if self.config['exchange']['testnet'] else 'Binance Live'}")
        print(f" Trading Pair:    {self.config['trading_pair']}")
        print(f" Initial Capital: ${self.config['initial_capital']:,.2f}")
        print(f" Risk Profile:    {self.config['risk_profile'].title()}")
        print(f" Strategy:        {self.STRATEGY_TYPES[self.config['strategy_type']]}")
        
        if self.config.get("ai_provider"):
            print(f" AI Provider:     {self.AI_PROVIDERS[self.config['ai_provider']]}")
        
        print(f" Position Sizing: {self.POSITION_SIZING_METHODS[self.config['position_sizing']]}")
        
        if self.config.get("alert_channels"):
            channels_str = ", ".join([self.ALERT_CHANNELS[ch] for ch in self.config["alert_channels"]])
            print(f" Alerts:          {channels_str}")
        else:
            print(f" Alerts:          None configured")
        
        print(f"\n Risk Settings:")
        risk = self.config["risk_settings"]
        print(f"   Max Position Size:    {risk['max_position_size']*100:.1f}%")
        print(f"   Max Leverage:         {risk['max_leverage']}x")
        print(f"   Stop Loss:            {risk['stop_loss_pct']*100:.1f}%")
        print(f"   Take Profit:          {risk['take_profit_pct']*100:.1f}%")
        
        print("\n" + "=" * 60)
        
        return questionary.confirm(
            "Does this configuration look correct?",
            default=True
        ).ask()
    
    def _generate_config(self) -> str:
        """
        Generate YAML configuration file from wizard inputs.
        
        Returns:
            Path to the generated config file
        """
        # Create config directory if it doesn't exist
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"strategy_{self.config['risk_profile']}_{timestamp}.yaml"
        config_path = config_dir / filename
        
        # Build YAML configuration
        yaml_config = {
            "# YunMin Trading Agent Configuration": None,
            "# Generated by Configuration Wizard": None,
            f"# Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}": None,
            
            "exchange": self.config["exchange"],
            
            "trading": {
                "mode": "dry_run",
                "symbol": self.config["trading_pair"],
                "timeframe": "5m",
                "initial_capital": self.config["initial_capital"]
            },
            
            "risk": {
                **self.config["risk_settings"],
                "enable_circuit_breaker": True,
                "short": {
                    "stop_loss_pct": self.config["risk_settings"]["stop_loss_pct"] * 1.2,
                    "take_profit_pct": self.config["risk_settings"]["take_profit_pct"] * 1.25,
                    "max_position_size": self.config["risk_settings"]["max_position_size"] * 0.75,
                    "trailing_stop_pct": 2.5
                }
            },
            
            "strategy": self._get_strategy_config(),
            
            "ml": {
                "enabled": False,
                "model_type": "xgboost",
                "retrain_interval": 86400,
                "feature_lookback": 100
            },
            
            "llm": self._get_llm_config(),
            
            "database": {
                "db_url": "sqlite:///data/yunmin.db",
                "redis_url": "redis://localhost:6379/0"
            },
            
            "notification": self._get_notification_config(),
            
            "log_level": "INFO",
            "data_dir": "./data"
        }
        
        # Write YAML file
        with open(config_path, 'w') as f:
            # Write with custom formatting
            self._write_yaml_with_comments(f, yaml_config)
        
        return str(config_path)
    
    def _get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy-specific configuration."""
        strategy_type = self.config["strategy_type"]
        
        if strategy_type == "rule_based":
            return {
                "name": "ema_crossover",
                "fast_ema": 12,
                "slow_ema": 26,
                "rsi_period": 14,
                "rsi_overbought": 68.0,
                "rsi_oversold": 32.0
            }
        else:
            # AI strategies use similar base config
            return {
                "name": strategy_type,
                "lookback_periods": 100,
                "confidence_threshold": 0.65
            }
    
    def _get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        if self.config.get("ai_provider"):
            return {
                "enabled": True,
                "provider": self.config["ai_provider"],
                "explain_trades": self.config.get("explain_trades", True)
            }
        else:
            return {
                "enabled": False,
                "provider": "grok"
            }
    
    def _get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration."""
        channels = self.config.get("alert_channels", [])
        
        return {
            "telegram_enabled": "telegram" in channels,
            "email_enabled": "email" in channels,
            "desktop_enabled": "desktop" in channels
        }
    
    def _write_yaml_with_comments(self, file, data: Dict[str, Any]):
        """Write YAML with preserved comments."""
        for key, value in data.items():
            if key.startswith("#"):
                file.write(f"{key}\n")
            elif value is None:
                continue
            else:
                yaml.dump({key: value}, file, default_flow_style=False, sort_keys=False)
                file.write("\n")


def run_wizard():
    """Run the configuration wizard."""
    wizard = ConfigWizard()
    config_path = wizard.run()
    
    if config_path:
        print("\n✨ Setup complete! Happy trading! 🚀\n")
    
    return config_path


if __name__ == "__main__":
    run_wizard()

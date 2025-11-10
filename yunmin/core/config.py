"""
Configuration management for Yun Min trading agent.
Loads configuration from YAML files and environment variables.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file automatically
load_dotenv()


class ExchangeConfig(BaseSettings):
    """Exchange API configuration."""
    
    model_config = ConfigDict(env_prefix="YUNMIN_EXCHANGE_")
    
    name: str = Field(default="binance", description="Exchange name (binance, bybit, okx)")
    api_key: str = Field(default="", description="API key (from env)")
    api_secret: str = Field(default="", description="API secret (from env)")
    testnet: bool = Field(default=True, description="Use testnet/sandbox")
    enable_rate_limit: bool = Field(default=True, description="Enable rate limiting")



class TradingConfig(BaseSettings):
    """Trading parameters configuration."""
    
    model_config = ConfigDict(env_prefix="YUNMIN_TRADING_")
    
    mode: str = Field(default="dry_run", description="Trading mode: dry_run, paper, live")
    symbol: str = Field(default="BTC/USDT", description="Trading pair")
    timeframe: str = Field(default="5m", description="Candle timeframe")
    initial_capital: float = Field(default=10000.0, description="Initial capital in USDT")


class RiskConfig(BaseSettings):
    """Risk management configuration."""
    
    model_config = ConfigDict(env_prefix="YUNMIN_RISK_")
    
    max_position_size: float = Field(default=0.1, description="Max position size (fraction of capital)")
    max_leverage: float = Field(default=3.0, description="Maximum leverage allowed")
    max_total_exposure: float = Field(default=0.15, description="Max total exposure across all positions")
    max_daily_drawdown: float = Field(default=0.05, description="Max daily drawdown (5%)")
    stop_loss_pct: float = Field(default=0.02, description="Stop loss percentage")
    take_profit_pct: float = Field(default=0.03, description="Take profit percentage")
    enable_circuit_breaker: bool = Field(default=True, description="Enable emergency circuit breaker")
    
    # Margin safety thresholds (CRITICAL - Problem #2 fix)
    min_margin_level: float = Field(default=200.0, description="Minimum safe margin level (%)")
    critical_margin_level: float = Field(default=150.0, description="Critical margin level (%) - emergency exit")
    
    # Funding rate limits (CRITICAL - Problem #2 fix)
    max_funding_rate: float = Field(default=0.001, description="Maximum acceptable funding rate (0.001 = 0.1%)")


class StrategyConfig(BaseSettings):
    """Strategy configuration."""
    
    model_config = ConfigDict(env_prefix="YUNMIN_STRATEGY_")
    
    name: str = Field(default="ema_crossover", description="Strategy name")
    fast_ema: int = Field(default=9, description="Fast EMA period")
    slow_ema: int = Field(default=21, description="Slow EMA period")
    rsi_period: int = Field(default=14, description="RSI period")
    rsi_overbought: float = Field(default=70.0, description="RSI overbought threshold")
    rsi_oversold: float = Field(default=30.0, description="RSI oversold threshold")


class MLConfig(BaseSettings):
    """Machine Learning configuration."""
    
    model_config = ConfigDict(env_prefix="YUNMIN_ML_")
    
    enabled: bool = Field(default=False, description="Enable ML predictions")
    model_type: str = Field(default="xgboost", description="Model type: xgboost, lightgbm, lstm")
    retrain_interval: int = Field(default=86400, description="Retrain interval in seconds")
    feature_lookback: int = Field(default=100, description="Lookback period for features")


class LLMConfig(BaseSettings):
    """LLM integration configuration."""
    
    model_config = ConfigDict(env_prefix="YUNMIN_LLM_")
    
    enabled: bool = Field(default=False, description="Enable LLM features")
    provider: str = Field(default="openai", description="LLM provider: openai, grok")
    api_key: str = Field(default="", description="LLM API key")
    model: str = Field(default="gpt-5", description="Model name (gpt-5, gpt-4o-mini, llama-3.3, etc.)")
    explain_trades: bool = Field(default=True, description="Generate trade explanations")
    
    # OpenAI cascade strategy (optional)
    fallback_model: Optional[str] = Field(default=None, description="Fallback model when limits exceeded")
    max_daily_tokens_gpt5: Optional[int] = Field(default=250000, description="Daily token limit for GPT-5")
    max_daily_tokens_mini: Optional[int] = Field(default=2500000, description="Daily token limit for mini models")


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    
    model_config = ConfigDict(env_prefix="YUNMIN_DB_")
    
    db_url: str = Field(default="sqlite:///yunmin.db", description="Database URL")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")


class NotificationConfig(BaseSettings):
    """Notification configuration."""
    
    model_config = ConfigDict(env_prefix="YUNMIN_NOTIFY_")
    
    telegram_enabled: bool = Field(default=False, description="Enable Telegram notifications")
    telegram_token: str = Field(default="", description="Telegram bot token")
    telegram_chat_id: str = Field(default="", description="Telegram chat ID")


class YunMinConfig(BaseSettings):
    """Main configuration class for Yun Min trading agent."""
    
    model_config = ConfigDict(env_prefix="YUNMIN_")
    
    # Sub-configurations
    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    ml: MLConfig = Field(default_factory=MLConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    
    # General settings
    log_level: str = Field(default="INFO", description="Logging level")
    data_dir: str = Field(default="./data", description="Data directory")


def load_config(config_file: Optional[str] = None) -> YunMinConfig:
    """
    Load configuration from file and environment variables.
    
    Args:
        config_file: Path to YAML configuration file
        
    Returns:
        YunMinConfig instance
    """
    config_dict: Dict[str, Any] = {}
    
    # Load from YAML file if provided
    if config_file and os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config_dict = yaml.safe_load(f) or {}
    
    # Create config object (env vars will override YAML values)
    config = YunMinConfig(**config_dict)
    
    return config


def save_config(config: YunMinConfig, config_file: str) -> None:
    """
    Save configuration to YAML file.
    
    Args:
        config: YunMinConfig instance
        config_file: Path to save configuration
    """
    config_dict = config.model_dump()
    
    os.makedirs(os.path.dirname(config_file) or ".", exist_ok=True)
    with open(config_file, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False)

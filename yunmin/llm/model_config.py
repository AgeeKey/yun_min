"""
OpenAI Model Configuration for YunMin Trading Bot

Поддерживаемые модели:
- GPT-5.1, GPT-5, GPT-4.1, GPT-4o: 250k tokens/day
- O1, O3: Reasoning models (250k tokens/day)
- GPT-4o-mini, O1-mini, O3-mini: 2.5M tokens/day
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ModelTier(Enum):
    """Тиры моделей по лимитам токенов."""
    STANDARD = "standard"      # 250k tokens/day
    HIGH_VOLUME = "high_volume"  # 2.5M tokens/day
    REASONING = "reasoning"     # O1/O3 reasoning models


@dataclass
class ModelConfig:
    """Конфигурация модели OpenAI."""
    name: str
    tier: ModelTier
    max_tokens_per_day: int
    recommended_request_tokens: int
    description: str
    best_for: list[str]
    cost_per_1m_input: float  # USD
    cost_per_1m_output: float  # USD


# Каталог доступных моделей
AVAILABLE_MODELS = {
    # === GPT-5.1 Series ===
    "gpt-5.1": ModelConfig(
        name="gpt-5.1",
        tier=ModelTier.STANDARD,
        max_tokens_per_day=250_000,
        recommended_request_tokens=2048,
        description="Latest GPT-5.1 flagship model",
        best_for=["complex reasoning", "advanced trading strategies", "market analysis"],
        cost_per_1m_input=5.00,
        cost_per_1m_output=15.00
    ),
    "gpt-5.1-codex": ModelConfig(
        name="gpt-5.1-codex",
        tier=ModelTier.STANDARD,
        max_tokens_per_day=250_000,
        recommended_request_tokens=2048,
        description="GPT-5.1 optimized for code",
        best_for=["strategy generation", "technical analysis code", "backtest creation"],
        cost_per_1m_input=5.00,
        cost_per_1m_output=15.00
    ),
    "gpt-5.1-codex-mini": ModelConfig(
        name="gpt-5.1-codex-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=1024,
        description="Compact GPT-5.1 codex for high volume",
        best_for=["frequent trading decisions", "rapid backtesting", "24/7 trading"],
        cost_per_1m_input=0.20,
        cost_per_1m_output=0.60
    ),
    
    # === GPT-5 Series ===
    "gpt-5": ModelConfig(
        name="gpt-5",
        tier=ModelTier.STANDARD,
        max_tokens_per_day=250_000,
        recommended_request_tokens=2048,
        description="GPT-5 standard model",
        best_for=["general trading analysis", "market sentiment", "strategy planning"],
        cost_per_1m_input=4.00,
        cost_per_1m_output=12.00
    ),
    "gpt-5-mini": ModelConfig(
        name="gpt-5-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=1024,
        description="Compact GPT-5 for high volume",
        best_for=["frequent signals", "real-time decisions", "cost-effective 24/7"],
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.50
    ),
    "gpt-5-nano": ModelConfig(
        name="gpt-5-nano",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=512,
        description="Ultra-compact GPT-5",
        best_for=["ultra-high frequency", "simple signals", "minimal cost"],
        cost_per_1m_input=0.10,
        cost_per_1m_output=0.30
    ),
    
    # === GPT-4.1 Series ===
    "gpt-4.1": ModelConfig(
        name="gpt-4.1",
        tier=ModelTier.STANDARD,
        max_tokens_per_day=250_000,
        recommended_request_tokens=2048,
        description="Latest GPT-4.1 flagship",
        best_for=["proven reliability", "stable trading", "conservative approach"],
        cost_per_1m_input=3.00,
        cost_per_1m_output=10.00
    ),
    "gpt-4.1-mini": ModelConfig(
        name="gpt-4.1-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=1024,
        description="Compact GPT-4.1",
        best_for=["balanced performance/cost", "medium frequency trading"],
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.50
    ),
    "gpt-4.1-nano": ModelConfig(
        name="gpt-4.1-nano",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=512,
        description="Ultra-compact GPT-4.1",
        best_for=["high frequency", "low cost", "simple strategies"],
        cost_per_1m_input=0.10,
        cost_per_1m_output=0.30
    ),
    
    # === GPT-4o Series ===
    "gpt-4o": ModelConfig(
        name="gpt-4o",
        tier=ModelTier.STANDARD,
        max_tokens_per_day=250_000,
        recommended_request_tokens=2048,
        description="GPT-4 optimized",
        best_for=["multimodal analysis", "chart pattern recognition"],
        cost_per_1m_input=2.50,
        cost_per_1m_output=8.00
    ),
    "gpt-4o-mini": ModelConfig(
        name="gpt-4o-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=1024,
        description="Compact GPT-4o - RECOMMENDED FOR TRADING",
        best_for=["real-time trading", "cost-effective 24/7", "proven performance"],
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.60
    ),
    
    # === O-Series (Reasoning Models) ===
    "o1": ModelConfig(
        name="o1",
        tier=ModelTier.REASONING,
        max_tokens_per_day=250_000,
        recommended_request_tokens=4096,
        description="O1 reasoning model - deep analysis",
        best_for=["complex market analysis", "strategy development", "risk assessment"],
        cost_per_1m_input=15.00,
        cost_per_1m_output=60.00
    ),
    "o1-mini": ModelConfig(
        name="o1-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=2048,
        description="O1-mini reasoning for high volume",
        best_for=["frequent analysis", "real-time reasoning", "cost-effective"],
        cost_per_1m_input=1.00,
        cost_per_1m_output=4.00
    ),
    
    "o3": ModelConfig(
        name="o3",
        tier=ModelTier.REASONING,
        max_tokens_per_day=250_000,
        recommended_request_tokens=4096,
        description="O3 advanced reasoning",
        best_for=["cutting-edge analysis", "complex strategies", "research"],
        cost_per_1m_input=20.00,
        cost_per_1m_output=80.00
    ),
    "o3-mini": ModelConfig(
        name="o3-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=2048,
        description="O3-mini reasoning for high volume",
        best_for=["frequent reasoning", "real-time insights", "balanced cost"],
        cost_per_1m_input=1.50,
        cost_per_1m_output=6.00
    ),
    
    "o4-mini": ModelConfig(
        name="o4-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=2048,
        description="O4-mini next-gen reasoning",
        best_for=["future-proof", "experimental strategies", "innovation"],
        cost_per_1m_input=2.00,
        cost_per_1m_output=8.00
    ),
}


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """Получить конфигурацию модели по имени."""
    return AVAILABLE_MODELS.get(model_name)


def get_recommended_model_for_trading() -> str:
    """
    Получить рекомендуемую модель для торговли.
    
    Returns:
        gpt-4o-mini - лучший баланс цена/качество для 24/7 торговли
    """
    return "gpt-4o-mini"


def get_models_by_tier(tier: ModelTier) -> dict[str, ModelConfig]:
    """Получить все модели определённого тира."""
    return {
        name: config
        for name, config in AVAILABLE_MODELS.items()
        if config.tier == tier
    }


def calculate_daily_cost(
    model_name: str,
    decisions_per_day: int = 288,  # 5-min candles = 288/day
    avg_input_tokens: int = 800,
    avg_output_tokens: int = 200
) -> dict:
    """
    Рассчитать дневную стоимость использования модели.
    
    Args:
        model_name: Название модели
        decisions_per_day: Количество решений в день (default: 288 для 5m)
        avg_input_tokens: Средний размер промпта
        avg_output_tokens: Средний размер ответа
    
    Returns:
        {
            'daily_cost_usd': float,
            'monthly_cost_usd': float,
            'tokens_per_day': int,
            'within_limits': bool,
            'safety_margin': str
        }
    """
    config = get_model_config(model_name)
    if not config:
        return {'error': f'Model {model_name} not found'}
    
    # Посчитать общее использование токенов
    total_input_tokens = decisions_per_day * avg_input_tokens
    total_output_tokens = decisions_per_day * avg_output_tokens
    total_tokens = total_input_tokens + total_output_tokens
    
    # Проверить лимит
    within_limits = total_tokens <= config.max_tokens_per_day
    safety_margin = f"{(config.max_tokens_per_day - total_tokens) / config.max_tokens_per_day * 100:.1f}%"
    
    # Посчитать стоимость
    input_cost = (total_input_tokens / 1_000_000) * config.cost_per_1m_input
    output_cost = (total_output_tokens / 1_000_000) * config.cost_per_1m_output
    daily_cost = input_cost + output_cost
    monthly_cost = daily_cost * 30
    
    return {
        'model': model_name,
        'daily_cost_usd': round(daily_cost, 2),
        'monthly_cost_usd': round(monthly_cost, 2),
        'tokens_per_day': total_tokens,
        'max_tokens_per_day': config.max_tokens_per_day,
        'within_limits': within_limits,
        'safety_margin': safety_margin,
        'decisions_per_day': decisions_per_day
    }


def print_model_comparison():
    """Вывести сравнительную таблицу моделей."""
    print("\n" + "="*100)
    print("OpenAI Models for Trading - Cost & Performance Comparison")
    print("="*100)
    
    for tier in ModelTier:
        models = get_models_by_tier(tier)
        if not models:
            continue
        
        print(f"\n{tier.value.upper()} TIER ({list(models.values())[0].max_tokens_per_day:,} tokens/day):")
        print("-" * 100)
        
        for name, config in models.items():
            cost_info = calculate_daily_cost(name)
            print(f"\n{name:20} | ${cost_info['monthly_cost_usd']:>6.2f}/mo | {config.description}")
            print(f"{'':20} | Best for: {', '.join(config.best_for[:2])}")
    
    print("\n" + "="*100)
    print("RECOMMENDATION: gpt-4o-mini - Best balance for 24/7 trading (~$3.60/month)")
    print("="*100 + "\n")


if __name__ == "__main__":
    # Демонстрация
    print_model_comparison()
    
    # Показать рекомендацию
    recommended = get_recommended_model_for_trading()
    print(f"\n🎯 Recommended for trading: {recommended}")
    
    cost = calculate_daily_cost(recommended)
    print(f"   Daily cost: ${cost['daily_cost_usd']:.2f}")
    print(f"   Monthly cost: ${cost['monthly_cost_usd']:.2f}")
    print(f"   Tokens/day: {cost['tokens_per_day']:,} / {cost['max_tokens_per_day']:,}")
    print(f"   Safety margin: {cost['safety_margin']}")

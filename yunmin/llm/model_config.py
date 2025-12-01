"""
OpenAI Model Configuration for YunMin Trading Bot

🎉 ВСЕ МОДЕЛИ БЕСПЛАТНЫ! 🎉

Лимиты токенов в день:
- Standard: 250k tokens/day (GPT-5.1, GPT-5, GPT-4.1, GPT-4o, O1, O3)
- High Volume: 2.5M tokens/day (все mini/nano модели)
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ModelTier(Enum):
    """Тиры моделей по лимитам токенов."""
    STANDARD = "standard"      # 250k tokens/day - БЕСПЛАТНО
    HIGH_VOLUME = "high_volume"  # 2.5M tokens/day - БЕСПЛАТНО
    REASONING = "reasoning"     # O1/O3 reasoning models - БЕСПЛАТНО


@dataclass
class ModelConfig:
    """Конфигурация модели OpenAI (все модели бесплатны!)."""
    name: str
    tier: ModelTier
    max_tokens_per_day: int
    recommended_request_tokens: int
    description: str
    best_for: list[str]


# Каталог БЕСПЛАТНЫХ моделей
AVAILABLE_MODELS = {
    # === GPT-5.1 Series (250k/day FREE) ===
    "gpt-5.1": ModelConfig(
        name="gpt-5.1",
        tier=ModelTier.STANDARD,
        max_tokens_per_day=250_000,
        recommended_request_tokens=2048,
        description="Latest GPT-5.1 flagship - FREE 250k/day",
        best_for=["complex reasoning", "advanced trading strategies", "market analysis"]
    ),
    "gpt-5.1-codex": ModelConfig(
        name="gpt-5.1-codex",
        tier=ModelTier.STANDARD,
        max_tokens_per_day=250_000,
        recommended_request_tokens=2048,
        description="GPT-5.1 code optimized - FREE 250k/day",
        best_for=["strategy generation", "technical analysis code", "backtest creation"]
    ),
    "gpt-5.1-codex-mini": ModelConfig(
        name="gpt-5.1-codex-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=1024,
        description="GPT-5.1 codex mini - FREE 2.5M/day! 🚀",
        best_for=["24/7 trading", "rapid backtesting", "high frequency"]
    ),
    
    # === GPT-5 Series ===
    "gpt-5": ModelConfig(
        name="gpt-5",
        tier=ModelTier.STANDARD,
        max_tokens_per_day=250_000,
        recommended_request_tokens=2048,
        description="GPT-5 standard - FREE 250k/day",
        best_for=["general trading analysis", "market sentiment", "strategy planning"]
    ),
    "gpt-5-mini": ModelConfig(
        name="gpt-5-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=1024,
        description="GPT-5 mini - FREE 2.5M/day! Perfect for 24/7",
        best_for=["frequent signals", "real-time decisions", "unlimited trading"]
    ),
    "gpt-5-nano": ModelConfig(
        name="gpt-5-nano",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=512,
        description="GPT-5 nano - FREE 2.5M/day! Ultra-fast",
        best_for=["ultra-high frequency", "simple signals", "maximum speed"]
    ),
    
    # === GPT-4.1 Series ===
    "gpt-4.1": ModelConfig(
        name="gpt-4.1",
        tier=ModelTier.STANDARD,
        max_tokens_per_day=250_000,
        recommended_request_tokens=2048,
        description="GPT-4.1 flagship - FREE 250k/day",
        best_for=["proven reliability", "stable trading", "conservative approach"]
    ),
    "gpt-4.1-mini": ModelConfig(
        name="gpt-4.1-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=1024,
        description="GPT-4.1 mini - FREE 2.5M/day!",
        best_for=["balanced performance", "medium frequency trading", "24/7"]
    ),
    "gpt-4.1-nano": ModelConfig(
        name="gpt-4.1-nano",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=512,
        description="GPT-4.1 nano - FREE 2.5M/day!",
        best_for=["high frequency", "simple strategies", "maximum decisions"]
    ),
    
    # === GPT-4o Series ===
    "gpt-4o": ModelConfig(
        name="gpt-4o",
        tier=ModelTier.STANDARD,
        max_tokens_per_day=250_000,
        recommended_request_tokens=2048,
        description="GPT-4o optimized - FREE 250k/day",
        best_for=["multimodal analysis", "chart pattern recognition", "proven quality"]
    ),
    "gpt-4o-mini": ModelConfig(
        name="gpt-4o-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=1024,
        description="GPT-4o mini - FREE 2.5M/day! ⭐ RECOMMENDED",
        best_for=["real-time trading", "24/7 unlimited", "proven + high volume"]
    ),
    
    # === O-Series (Reasoning Models) ===
    "o1": ModelConfig(
        name="o1",
        tier=ModelTier.REASONING,
        max_tokens_per_day=250_000,
        recommended_request_tokens=4096,
        description="O1 reasoning - FREE 250k/day",
        best_for=["complex market analysis", "strategy development", "risk assessment"]
    ),
    "o1-mini": ModelConfig(
        name="o1-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=2048,
        description="O1-mini reasoning - FREE 2.5M/day! 🧠",
        best_for=["frequent analysis", "real-time reasoning", "deep thinking + volume"]
    ),
    
    "o3": ModelConfig(
        name="o3",
        tier=ModelTier.REASONING,
        max_tokens_per_day=250_000,
        recommended_request_tokens=4096,
        description="O3 advanced reasoning - FREE 250k/day",
        best_for=["cutting-edge analysis", "complex strategies", "research"]
    ),
    "o3-mini": ModelConfig(
        name="o3-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=2048,
        description="O3-mini reasoning - FREE 2.5M/day! 🧠⚡",
        best_for=["frequent reasoning", "real-time insights", "advanced + volume"]
    ),
    
    "o4-mini": ModelConfig(
        name="o4-mini",
        tier=ModelTier.HIGH_VOLUME,
        max_tokens_per_day=2_500_000,
        recommended_request_tokens=2048,
        description="O4-mini next-gen - FREE 2.5M/day! 🚀",
        best_for=["future-proof", "experimental strategies", "cutting edge"]
    ),
}


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """Получить конфигурацию модели по имени."""
    return AVAILABLE_MODELS.get(model_name)


def get_recommended_model_for_trading() -> str:
    """
    Получить рекомендуемую модель для торговли.
    
    Returns:
        gpt-4o-mini - лучший баланс для 24/7 торговли (2.5M tokens/day FREE!)
    """
    return "gpt-4o-mini"


def get_models_by_tier(tier: ModelTier) -> dict[str, ModelConfig]:
    """Получить все модели определённого тира."""
    return {
        name: config
        for name, config in AVAILABLE_MODELS.items()
        if config.tier == tier
    }


def calculate_daily_usage(
    model_name: str,
    decisions_per_day: int = 288,  # 5-min candles = 288/day
    avg_input_tokens: int = 800,
    avg_output_tokens: int = 200
) -> dict:
    """
    Рассчитать дневное использование модели.
    
    🎉 ВСЕ МОДЕЛИ БЕСПЛАТНЫ! Нет стоимости, только лимиты токенов.
    
    Args:
        model_name: Название модели
        decisions_per_day: Количество решений в день (default: 288 для 5m свечей)
        avg_input_tokens: Средний размер промпта
        avg_output_tokens: Средний размер ответа
    
    Returns:
        {
            'model': str,
            'tokens_per_day': int,
            'max_tokens_per_day': int,
            'within_limits': bool,
            'safety_margin_pct': float,
            'is_free': True,
            'decisions_per_day': int
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
    safety_margin_pct = ((config.max_tokens_per_day - total_tokens) / config.max_tokens_per_day * 100) if within_limits else 0
    
    return {
        'model': model_name,
        'tokens_per_day': total_tokens,
        'max_tokens_per_day': config.max_tokens_per_day,
        'within_limits': within_limits,
        'safety_margin_pct': round(safety_margin_pct, 1),
        'is_free': True,  # 🎉 ВСЁ БЕСПЛАТНО!
        'decisions_per_day': decisions_per_day,
        'tier': config.tier.value
    }


def print_model_comparison():
    """Вывести сравнительную таблицу БЕСПЛАТНЫХ моделей."""
    print("\n" + "="*100)
    print("🎉 OpenAI Models for Trading - ALL FREE! 🎉")
    print("="*100)
    
    for tier in ModelTier:
        models = get_models_by_tier(tier)
        if not models:
            continue
        
        print(f"\n{tier.value.upper()} TIER ({list(models.values())[0].max_tokens_per_day:,} tokens/day - FREE!):")
        print("-" * 100)
        
        for name, config in models.items():
            usage_info = calculate_daily_usage(name)
            status = "✅ OK" if usage_info['within_limits'] else "⚠️  OVER LIMIT"
            margin = usage_info['safety_margin_pct']
            
            print(f"\n{name:20} | {status} | {margin:>5.1f}% margin | {config.description}")
            print(f"{'':20} | Best for: {', '.join(config.best_for[:2])}")
            print(f"{'':20} | Usage: {usage_info['tokens_per_day']:,} / {usage_info['max_tokens_per_day']:,} tokens/day")
    
    print("\n" + "="*100)
    print("💡 ALL MODELS ARE FREE! Just respect daily token limits.")
    print("⭐ RECOMMENDATION: gpt-4o-mini (2.5M/day) or gpt-5.1-codex-mini (2.5M/day) for 24/7 trading")
    print("="*100 + "\n")


def suggest_best_model(decisions_per_day: int) -> str:
    """
    Предложить лучшую модель для заданного количества решений.
    
    Args:
        decisions_per_day: Сколько решений нужно принимать в день
    
    Returns:
        Название рекомендуемой модели
    """
    tokens_per_day = decisions_per_day * 1000  # ~1000 tokens per decision
    
    if tokens_per_day <= 250_000:
        # Можно использовать Standard модели
        return "gpt-5.1"  # Лучшая стандартная модель
    else:
        # Нужна High Volume модель
        if tokens_per_day <= 2_500_000:
            return "gpt-4o-mini"  # Проверенная и надёжная
        else:
            return "Contact support - need more than 2.5M tokens/day"


if __name__ == "__main__":
    # Демонстрация
    print_model_comparison()
    
    # Показать рекомендацию
    recommended = get_recommended_model_for_trading()
    print(f"\n🎯 Recommended for 24/7 trading: {recommended}")
    
    usage = calculate_daily_usage(recommended)
    print(f"   Tokens/day: {usage['tokens_per_day']:,} / {usage['max_tokens_per_day']:,}")
    print(f"   Safety margin: {usage['safety_margin_pct']:.1f}%")
    print(f"   Is FREE: {usage['is_free']} 🎉")
    print(f"   Can make {usage['decisions_per_day']} decisions per day!")

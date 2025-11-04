import json
from analyze_strategy_with_ai import StrategyAnalyzer

# Загружаем результаты
with open('backtest_v3_realdata_20251104_142513.json', 'r') as f:
    results = json.load(f)

# Создаем анализатор
analyzer = StrategyAnalyzer()

# Получаем предложения по улучшению
print("=" * 70)
print("🔧 AI RECOMMENDATIONS FOR IMPROVEMENT")
print("=" * 70)

suggestions = analyzer.suggest_improvements(
    results,
    strategy_params={
        'fast_ema': 9,
        'slow_ema': 21,
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'stop_loss': 2.0,
        'take_profit': 4.0
    }
)

print(suggestions)
print("\n" + "=" * 70)

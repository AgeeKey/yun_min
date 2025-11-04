"""
AI Анализ торговых стратегий через Groq
Использует бесплатный Groq API для анализа результатов бэктестов
"""
import os
import json
from groq import Groq
from datetime import datetime

class StrategyAnalyzer:
    """Анализирует результаты стратегий с помощью Groq AI"""
    
    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: Groq API ключ (если None, берется из переменной окружения)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY не найден! Установите: $env:GROQ_API_KEY='ваш_ключ'")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"  # Новейшая модель для анализа
    
    def analyze_backtest_results(self, results: dict, detailed: bool = True) -> str:
        """
        Анализирует результаты бэктеста
        
        Args:
            results: Словарь с результатами (metrics, trades, etc)
            detailed: Если True, дает подробный анализ
        
        Returns:
            Текстовый анализ от AI
        """
        # Формируем промпт для AI
        prompt = self._create_analysis_prompt(results, detailed)
        
        # Запрос к Groq
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Ты эксперт по криптотрейдингу и анализу торговых систем. 
                    Анализируй результаты бэктестов профессионально, честно указывай на проблемы.
                    Давай конкретные рекомендации по улучшению."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=2000 if detailed else 500,
            temperature=0.3  # Низкая температура для точности
        )
        
        return response.choices[0].message.content
    
    def _create_analysis_prompt(self, results: dict, detailed: bool) -> str:
        """Создает промпт для AI анализа"""
        
        metrics = results.get('metrics', {})
        
        prompt = f"""Проанализируй результаты бэктеста криптовалютной торговой стратегии:

📊 ОСНОВНЫЕ МЕТРИКИ:
- Total Return: {metrics.get('total_return', 0):.2f}%
- Win Rate: {metrics.get('win_rate', 0):.2f}%
- Total Trades: {metrics.get('total_trades', 0)}
- Winning Trades: {metrics.get('winning_trades', 0)}
- Losing Trades: {metrics.get('losing_trades', 0)}
- Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%
- Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}
- Profit Factor: {metrics.get('profit_factor', 0):.2f}

💰 ПРИБЫЛЬНОСТЬ:
- Avg Win: {metrics.get('avg_win', 0):.2f}%
- Avg Loss: {metrics.get('avg_loss', 0):.2f}%
- Best Trade: {metrics.get('best_trade', 0):.2f}%
- Worst Trade: {metrics.get('worst_trade', 0):.2f}%

⏱ ДЛИТЕЛЬНОСТЬ:
- Avg Trade Duration: {metrics.get('avg_trade_duration_hours', 0):.1f} часов
"""
        
        # Добавляем информацию о сделках если есть
        trades = results.get('trades', [])
        if trades:
            long_trades = [t for t in trades if t.get('side') == 'LONG']
            short_trades = [t for t in trades if t.get('side') == 'SHORT']
            
            prompt += f"""
📈 LONG vs SHORT:
- LONG сделок: {len(long_trades)}
- SHORT сделок: {len(short_trades)}
"""
            
            if long_trades:
                long_wins = [t for t in long_trades if t.get('pnl_pct', 0) > 0]
                prompt += f"- LONG Win Rate: {len(long_wins)/len(long_trades)*100:.1f}%\n"
            
            if short_trades:
                short_wins = [t for t in short_trades if t.get('pnl_pct', 0) > 0]
                prompt += f"- SHORT Win Rate: {len(short_wins)/len(short_trades)*100:.1f}%\n"
        
        if detailed:
            prompt += """

Дай ПОДРОБНЫЙ анализ:
1. Оценка общей производительности (1-10 баллов)
2. Сильные стороны стратегии
3. Слабые стороны и риски
4. Конкретные рекомендации по улучшению
5. Стоит ли запускать на реальных деньгах? (да/нет и почему)

Отвечай на русском, структурированно."""
        else:
            prompt += """

Дай КРАТКУЮ оценку (3-4 предложения):
- Годится ли стратегия?
- Главная проблема (если есть)
- Ключевая рекомендация

Отвечай на русском."""
        
        return prompt
    
    def compare_strategies(self, strategy1: dict, strategy2: dict, 
                          name1: str = "V1", name2: str = "V2") -> str:
        """
        Сравнивает две стратегии
        
        Args:
            strategy1: Результаты первой стратегии
            strategy2: Результаты второй стратегии
            name1: Название первой стратегии
            name2: Название второй стратегии
        
        Returns:
            Сравнительный анализ
        """
        m1 = strategy1.get('metrics', {})
        m2 = strategy2.get('metrics', {})
        
        prompt = f"""Сравни две криптовалютные торговые стратегии:

{name1}:
- Return: {m1.get('total_return', 0):.2f}%
- Win Rate: {m1.get('win_rate', 0):.2f}%
- Trades: {m1.get('total_trades', 0)}
- Drawdown: {m1.get('max_drawdown', 0):.2f}%
- Sharpe: {m1.get('sharpe_ratio', 0):.2f}

{name2}:
- Return: {m2.get('total_return', 0):.2f}%
- Win Rate: {m2.get('win_rate', 0):.2f}%
- Trades: {m2.get('total_trades', 0)}
- Drawdown: {m2.get('max_drawdown', 0):.2f}%
- Sharpe: {m2.get('sharpe_ratio', 0):.2f}

Какая стратегия лучше и почему? Дай конкретные рекомендации.
Отвечай на русском, структурированно."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Ты эксперт по сравнительному анализу торговых стратегий."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    def suggest_improvements(self, results: dict, strategy_params: dict = None) -> str:
        """
        Предлагает улучшения для стратегии
        
        Args:
            results: Результаты бэктеста
            strategy_params: Параметры стратегии (опционально)
        
        Returns:
            Предложения по улучшению
        """
        metrics = results.get('metrics', {})
        
        prompt = f"""На основе результатов бэктеста предложи конкретные улучшения:

ТЕКУЩИЕ РЕЗУЛЬТАТЫ:
- Return: {metrics.get('total_return', 0):.2f}%
- Win Rate: {metrics.get('win_rate', 0):.2f}%
- Drawdown: {metrics.get('max_drawdown', 0):.2f}%
- Avg Win/Loss: {metrics.get('avg_win', 0):.2f}% / {metrics.get('avg_loss', 0):.2f}%
"""
        
        if strategy_params:
            prompt += f"\nПАРАМЕТРЫ СТРАТЕГИИ:\n{json.dumps(strategy_params, indent=2)}\n"
        
        prompt += """
Предложи ТОП-5 конкретных улучшений:
1. Какие параметры изменить?
2. Какие фильтры добавить?
3. Как улучшить risk management?
4. Какие сигналы усилить/убрать?
5. Другие идеи

Отвечай конкретно и на русском."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Ты эксперт по оптимизации торговых стратегий."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=1500,
            temperature=0.4  # Чуть больше креативности для идей
        )
        
        return response.choices[0].message.content


def analyze_from_json(json_path: str, detailed: bool = True):
    """
    Анализирует результаты из JSON файла
    
    Args:
        json_path: Путь к JSON файлу с результатами
        detailed: Подробный анализ
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    analyzer = StrategyAnalyzer()
    
    print("=" * 70)
    print("🤖 AI АНАЛИЗ СТРАТЕГИИ")
    print("=" * 70)
    print(f"Файл: {json_path}")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    analysis = analyzer.analyze_backtest_results(results, detailed=detailed)
    print(analysis)
    print()
    print("=" * 70)
    
    return analysis


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python analyze_strategy_with_ai.py <путь_к_json> [--brief]")
        print("\nПример:")
        print("  python analyze_strategy_with_ai.py backtest_v3_20241104.json")
        print("  python analyze_strategy_with_ai.py backtest_v3_20241104.json --brief")
        sys.exit(1)
    
    json_path = sys.argv[1]
    detailed = "--brief" not in sys.argv
    
    try:
        analyze_from_json(json_path, detailed=detailed)
    except FileNotFoundError:
        print(f"❌ Файл не найден: {json_path}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

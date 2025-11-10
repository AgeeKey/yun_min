"""
Backtesting Engine - тестирование стратегий на исторических данных

Позволяет:
- Загрузка исторических OHLCV данных
- Симуляция торговли
- Расчёт метрик производительности
- Генерация отчётов
- Walk-Forward Analysis
- Monte Carlo Simulation
"""

from .backtester import Backtester
from .data_loader import HistoricalDataLoader
from .metrics import PerformanceMetrics
from .report_generator import ReportGenerator
from .walkforward import WalkForwardAnalyzer, WalkForwardWindow, WalkForwardResult
from .montecarlo import MonteCarloSimulator, MonteCarloResult

__all__ = [
    'Backtester',
    'HistoricalDataLoader',
    'PerformanceMetrics',
    'ReportGenerator',
    'WalkForwardAnalyzer',
    'WalkForwardWindow',
    'WalkForwardResult',
    'MonteCarloSimulator',
    'MonteCarloResult',
]

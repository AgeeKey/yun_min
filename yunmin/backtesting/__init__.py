"""
Backtesting Engine - тестирование стратегий на исторических данных

Позволяет:
- Загрузка исторических OHLCV данных
- Симуляция торговли
- Расчёт метрик производительности
- Генерация отчётов
"""

from .backtester import Backtester
from .data_loader import HistoricalDataLoader
from .metrics import PerformanceMetrics
from .report_generator import ReportGenerator

__all__ = [
    'Backtester',
    'HistoricalDataLoader',
    'PerformanceMetrics',
    'ReportGenerator',
]

"""
Monte Carlo Simulation для стресс-тестирования торговых стратегий.

Рандомизирует порядок сделок N раз для проверки стабильности стратегии
и оценки распределения результатов при различных последовательностях.
"""

import random
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger

from .metrics import TradeResult, PerformanceMetrics


@dataclass
class MonteCarloResult:
    """Результат одной симуляции Monte Carlo"""
    simulation_id: int
    final_equity: float
    total_return: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int


class MonteCarloSimulator:
    """
    Monte Carlo симулятор для оценки стабильности торговой стратегии.
    
    Метод:
    1. Берём все сделки из бэктеста
    2. Рандомизируем порядок сделок N раз
    3. Для каждой перестановки рассчитываем метрики
    4. Анализируем распределение результатов
    
    Это позволяет оценить:
    - Насколько результаты зависят от порядка сделок
    - Какова вероятность убытков
    - Каков диапазон возможных drawdown
    """
    
    def __init__(self, initial_capital: float = 100000.0, seed: Optional[int] = None):
        """
        Args:
            initial_capital: Начальный капитал
            seed: Seed для генератора случайных чисел (для воспроизводимости)
        """
        self.initial_capital = initial_capital
        self.seed = seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
    
    def run_simulation(
        self,
        trades: List[TradeResult],
        num_simulations: int = 1000
    ) -> List[MonteCarloResult]:
        """
        Запустить Monte Carlo симуляцию.
        
        Args:
            trades: Список всех сделок из бэктеста
            num_simulations: Количество симуляций (по умолчанию 1000)
            
        Returns:
            Список результатов симуляций
        """
        if not trades:
            logger.error("No trades provided for Monte Carlo simulation")
            return []
        
        if len(trades) < 10:
            logger.warning(f"Too few trades ({len(trades)}) for meaningful Monte Carlo")
        
        logger.info(f"Starting Monte Carlo simulation: {num_simulations} runs, {len(trades)} trades")
        
        results = []
        
        for i in range(num_simulations):
            # Рандомизируем порядок сделок
            shuffled_trades = random.sample(trades, len(trades))
            
            # Рассчитываем метрики для этой последовательности
            metrics = self._calculate_metrics_for_sequence(shuffled_trades)
            
            result = MonteCarloResult(
                simulation_id=i,
                final_equity=metrics['final_equity'],
                total_return=metrics['total_return'],
                max_drawdown=metrics['max_drawdown'],
                max_drawdown_pct=metrics['max_drawdown_pct'],
                sharpe_ratio=metrics['sharpe_ratio'],
                win_rate=metrics['win_rate'],
                profit_factor=metrics['profit_factor'],
                total_trades=metrics['total_trades']
            )
            
            results.append(result)
            
            if (i + 1) % 100 == 0:
                logger.debug(f"Completed {i + 1}/{num_simulations} simulations")
        
        logger.info(f"Monte Carlo simulation complete: {num_simulations} runs")
        
        return results
    
    def _calculate_metrics_for_sequence(
        self,
        trades: List[TradeResult]
    ) -> Dict[str, float]:
        """
        Рассчитать метрики для конкретной последовательности сделок.
        
        Args:
            trades: Последовательность сделок
            
        Returns:
            Dict с метриками
        """
        metrics_calc = PerformanceMetrics(self.initial_capital)
        
        for trade in trades:
            metrics_calc.add_trade(trade)
        
        return metrics_calc.calculate_metrics(self.initial_capital)
    
    def analyze_results(
        self,
        results: List[MonteCarloResult]
    ) -> Dict[str, Any]:
        """
        Анализ результатов Monte Carlo симуляции.
        
        Args:
            results: Список результатов симуляций
            
        Returns:
            Dict с аналитикой:
            - Процент прибыльных симуляций
            - Средние, медианные, min/max значения метрик
            - Percentiles (5%, 25%, 75%, 95%)
            - Probability of ruin
        """
        if not results:
            return self._empty_analysis()
        
        # Собираем все значения
        returns = [r.total_return for r in results]
        drawdowns = [r.max_drawdown_pct for r in results]
        sharpes = [r.sharpe_ratio for r in results]
        win_rates = [r.win_rate for r in results]
        profit_factors = [r.profit_factor for r in results]
        
        # Процент прибыльных симуляций
        profitable_count = sum(1 for r in returns if r > 0)
        profitable_pct = (profitable_count / len(results)) * 100
        
        # Percentiles
        return_percentiles = {
            '5%': np.percentile(returns, 5),
            '25%': np.percentile(returns, 25),
            '50%': np.percentile(returns, 50),
            '75%': np.percentile(returns, 75),
            '95%': np.percentile(returns, 95),
        }
        
        dd_percentiles = {
            '5%': np.percentile(drawdowns, 5),
            '25%': np.percentile(drawdowns, 25),
            '50%': np.percentile(drawdowns, 50),
            '75%': np.percentile(drawdowns, 75),
            '95%': np.percentile(drawdowns, 95),
        }
        
        # Probability of ruin (loss > 20%)
        ruin_threshold = -20.0
        ruin_count = sum(1 for r in returns if r < ruin_threshold)
        ruin_probability = (ruin_count / len(results)) * 100
        
        analysis = {
            # Summary stats
            'num_simulations': len(results),
            'profitable_simulations': profitable_count,
            'profitable_pct': profitable_pct,
            'unprofitable_simulations': len(results) - profitable_count,
            
            # Returns
            'return_mean': np.mean(returns),
            'return_median': np.median(returns),
            'return_std': np.std(returns),
            'return_min': np.min(returns),
            'return_max': np.max(returns),
            'return_percentiles': return_percentiles,
            
            # Drawdown
            'drawdown_mean': np.mean(drawdowns),
            'drawdown_median': np.median(drawdowns),
            'drawdown_std': np.std(drawdowns),
            'drawdown_min': np.min(drawdowns),
            'drawdown_max': np.max(drawdowns),
            'drawdown_percentiles': dd_percentiles,
            
            # Sharpe
            'sharpe_mean': np.mean(sharpes),
            'sharpe_median': np.median(sharpes),
            'sharpe_std': np.std(sharpes),
            'sharpe_min': np.min(sharpes),
            'sharpe_max': np.max(sharpes),
            
            # Win Rate
            'win_rate_mean': np.mean(win_rates),
            'win_rate_median': np.median(win_rates),
            'win_rate_std': np.std(win_rates),
            'win_rate_min': np.min(win_rates),
            'win_rate_max': np.max(win_rates),
            
            # Profit Factor
            'profit_factor_mean': np.mean(profit_factors),
            'profit_factor_median': np.median(profit_factors),
            'profit_factor_std': np.std(profit_factors),
            'profit_factor_min': np.min(profit_factors),
            'profit_factor_max': np.max(profit_factors),
            
            # Risk metrics
            'ruin_probability': ruin_probability,
            'ruin_count': ruin_count,
        }
        
        return analysis
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Пустой результат анализа"""
        return {
            'num_simulations': 0,
            'profitable_simulations': 0,
            'profitable_pct': 0.0,
            'unprofitable_simulations': 0,
            'return_mean': 0.0,
            'return_median': 0.0,
            'return_std': 0.0,
            'return_min': 0.0,
            'return_max': 0.0,
            'return_percentiles': {},
            'drawdown_mean': 0.0,
            'drawdown_median': 0.0,
            'drawdown_std': 0.0,
            'drawdown_min': 0.0,
            'drawdown_max': 0.0,
            'drawdown_percentiles': {},
            'sharpe_mean': 0.0,
            'sharpe_median': 0.0,
            'sharpe_std': 0.0,
            'sharpe_min': 0.0,
            'sharpe_max': 0.0,
            'win_rate_mean': 0.0,
            'win_rate_median': 0.0,
            'win_rate_std': 0.0,
            'win_rate_min': 0.0,
            'win_rate_max': 0.0,
            'profit_factor_mean': 0.0,
            'profit_factor_median': 0.0,
            'profit_factor_std': 0.0,
            'profit_factor_min': 0.0,
            'profit_factor_max': 0.0,
            'ruin_probability': 0.0,
            'ruin_count': 0,
        }
    
    def get_results_dataframe(
        self,
        results: List[MonteCarloResult]
    ) -> pd.DataFrame:
        """
        Конвертировать результаты в DataFrame для анализа.
        
        Args:
            results: Список результатов симуляций
            
        Returns:
            DataFrame с результатами
        """
        if not results:
            return pd.DataFrame()
        
        data = [{
            'simulation_id': r.simulation_id,
            'final_equity': r.final_equity,
            'total_return': r.total_return,
            'max_drawdown': r.max_drawdown,
            'max_drawdown_pct': r.max_drawdown_pct,
            'sharpe_ratio': r.sharpe_ratio,
            'win_rate': r.win_rate,
            'profit_factor': r.profit_factor,
            'total_trades': r.total_trades,
        } for r in results]
        
        return pd.DataFrame(data)
    
    def check_criteria(
        self,
        analysis: Dict[str, Any],
        min_profitable_pct: float = 95.0,
        max_drawdown_pct: float = 20.0
    ) -> Dict[str, Any]:
        """
        Проверить, соответствуют ли результаты критериям.
        
        Args:
            analysis: Результаты анализа
            min_profitable_pct: Минимальный процент прибыльных симуляций
            max_drawdown_pct: Максимальный допустимый drawdown
            
        Returns:
            Dict со статусом проверки:
            {
                'passed': bool,
                'criteria': {
                    'profitable_pct': {'required': 95, 'actual': 98, 'passed': True},
                    'max_drawdown': {'required': 20, 'actual': 18, 'passed': True},
                }
            }
        """
        criteria = {
            'profitable_pct': {
                'required': min_profitable_pct,
                'actual': analysis.get('profitable_pct', 0),
                'passed': analysis.get('profitable_pct', 0) >= min_profitable_pct,
            },
            'max_drawdown': {
                'required': max_drawdown_pct,
                'actual': analysis.get('drawdown_max', 100),
                'passed': analysis.get('drawdown_max', 100) <= max_drawdown_pct,
            }
        }
        
        all_passed = all(c['passed'] for c in criteria.values())
        
        return {
            'passed': all_passed,
            'criteria': criteria,
        }

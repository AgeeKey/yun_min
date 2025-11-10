"""
Walk-Forward Analysis для валидации торговых стратегий.

Разбивает данные на обучающие и тестовые периоды:
1. Обучить на in-sample данных
2. Тестировать на out-of-sample данных
3. Переходить к следующему периоду

Это позволяет оценить стабильность стратегии на невиданных данных.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger

from .backtester import Backtester
from .metrics import PerformanceMetrics
from yunmin.strategy.base import BaseStrategy


@dataclass
class WalkForwardWindow:
    """Одно окно walk-forward анализа"""
    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    train_size: int
    test_size: int


@dataclass
class WalkForwardResult:
    """Результат одного окна walk-forward"""
    window: WalkForwardWindow
    train_metrics: Dict[str, float]
    test_metrics: Dict[str, float]
    efficiency_ratio: float  # test_return / train_return


class WalkForwardAnalyzer:
    """
    Walk-Forward Analysis для оценки out-of-sample производительности.
    
    Метод:
    1. Разбить данные на последовательные периоды
    2. Для каждого периода:
       - Train на N месяцев
       - Test на M месяцев
       - Сохранить метрики
    3. Проанализировать консистентность результатов
    
    Параметры:
    - train_period: Длина обучающего периода (в днях)
    - test_period: Длина тестового периода (в днях)
    - step: Шаг между окнами (в днях)
    """
    
    def __init__(
        self,
        strategy: BaseStrategy,
        train_period_days: int = 90,  # 3 месяца
        test_period_days: int = 90,   # 3 месяца
        step_days: int = 30,          # Шаг 1 месяц
        initial_capital: float = 100000.0,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005
    ):
        """
        Args:
            strategy: Торговая стратегия
            train_period_days: Длина обучающего периода (дни)
            test_period_days: Длина тестового периода (дни)
            step_days: Шаг между окнами (дни)
            initial_capital: Начальный капитал
            commission_rate: Комиссия
            slippage_rate: Проскальзывание
        """
        self.strategy = strategy
        self.train_period = train_period_days
        self.test_period = test_period_days
        self.step = step_days
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
    
    def generate_windows(
        self,
        data: pd.DataFrame,
        anchored: bool = False
    ) -> List[WalkForwardWindow]:
        """
        Сгенерировать окна walk-forward.
        
        Args:
            data: DataFrame с историческими данными (должен иметь колонку 'timestamp')
            anchored: Если True, использует anchored walk-forward (train всегда с начала)
            
        Returns:
            Список окон
        """
        if 'timestamp' not in data.columns:
            logger.error("Data must have 'timestamp' column")
            return []
        
        data_sorted = data.sort_values('timestamp')
        start_date = data_sorted['timestamp'].iloc[0]
        end_date = data_sorted['timestamp'].iloc[-1]
        
        windows = []
        window_id = 0
        
        current_date = start_date
        
        while True:
            # Определить границы train/test
            train_start = start_date if anchored else current_date
            train_end = current_date + timedelta(days=self.train_period)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_period)
            
            # Проверить, что есть достаточно данных
            if test_end > end_date:
                break
            
            # Подсчитать размеры
            train_data = data_sorted[
                (data_sorted['timestamp'] >= train_start) &
                (data_sorted['timestamp'] < train_end)
            ]
            test_data = data_sorted[
                (data_sorted['timestamp'] >= test_start) &
                (data_sorted['timestamp'] < test_end)
            ]
            
            if len(train_data) < 50 or len(test_data) < 10:
                logger.warning(f"Skipping window {window_id}: insufficient data")
                current_date += timedelta(days=self.step)
                continue
            
            window = WalkForwardWindow(
                window_id=window_id,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                train_size=len(train_data),
                test_size=len(test_data)
            )
            
            windows.append(window)
            window_id += 1
            
            # Следующее окно
            current_date += timedelta(days=self.step)
        
        logger.info(f"Generated {len(windows)} walk-forward windows")
        return windows
    
    def run_walk_forward(
        self,
        data: pd.DataFrame,
        symbol: str = 'BTC/USDT',
        position_size_pct: float = 0.1,
        anchored: bool = False,
        optimize_fn: Optional[Callable] = None
    ) -> List[WalkForwardResult]:
        """
        Запустить walk-forward analysis.
        
        Args:
            data: DataFrame с историческими данными
            symbol: Торговая пара
            position_size_pct: Размер позиции (доля капитала)
            anchored: Использовать anchored walk-forward
            optimize_fn: Опциональная функция оптимизации параметров на train периоде
            
        Returns:
            Список результатов для каждого окна
        """
        windows = self.generate_windows(data, anchored=anchored)
        
        if not windows:
            logger.error("No windows generated for walk-forward analysis")
            return []
        
        logger.info(f"Starting walk-forward analysis: {len(windows)} windows")
        
        results = []
        
        for window in windows:
            logger.info(f"Processing window {window.window_id}/{len(windows)}")
            
            # Получить данные для train и test
            train_data = data[
                (data['timestamp'] >= window.train_start) &
                (data['timestamp'] < window.train_end)
            ].copy()
            
            test_data = data[
                (data['timestamp'] >= window.test_start) &
                (data['timestamp'] < window.test_end)
            ].copy()
            
            # Опционально: оптимизировать параметры на train
            if optimize_fn:
                try:
                    optimized_params = optimize_fn(train_data, self.strategy)
                    logger.info(f"Optimized params for window {window.window_id}: {optimized_params}")
                except Exception as e:
                    logger.warning(f"Optimization failed for window {window.window_id}: {e}")
            
            # Бэктест на train данных
            train_backtester = Backtester(
                strategy=self.strategy,
                initial_capital=self.initial_capital,
                commission_rate=self.commission_rate,
                slippage_rate=self.slippage_rate,
                use_risk_manager=False
            )
            
            train_metrics = train_backtester.run(
                data=train_data,
                symbol=symbol,
                position_size_pct=position_size_pct
            )
            
            # Бэктест на test данных (out-of-sample)
            test_backtester = Backtester(
                strategy=self.strategy,
                initial_capital=self.initial_capital,
                commission_rate=self.commission_rate,
                slippage_rate=self.slippage_rate,
                use_risk_manager=False
            )
            
            test_metrics = test_backtester.run(
                data=test_data,
                symbol=symbol,
                position_size_pct=position_size_pct
            )
            
            # Рассчитать efficiency ratio
            train_return = train_metrics.get('total_return', 0)
            test_return = test_metrics.get('total_return', 0)
            
            if train_return != 0:
                efficiency = test_return / train_return
            else:
                efficiency = 0.0
            
            result = WalkForwardResult(
                window=window,
                train_metrics=train_metrics,
                test_metrics=test_metrics,
                efficiency_ratio=efficiency
            )
            
            results.append(result)
            
            logger.info(
                f"Window {window.window_id}: "
                f"Train Return={train_return:.2f}%, "
                f"Test Return={test_return:.2f}%, "
                f"Efficiency={efficiency:.2f}"
            )
        
        logger.info("Walk-forward analysis complete")
        
        return results
    
    def analyze_results(
        self,
        results: List[WalkForwardResult]
    ) -> Dict[str, Any]:
        """
        Анализ результатов walk-forward.
        
        Args:
            results: Список результатов окон
            
        Returns:
            Dict с аналитикой:
            - Средние метрики для train и test
            - Консистентность (std, min, max)
            - Efficiency ratio
            - Degradation (насколько хуже на test vs train)
        """
        if not results:
            return self._empty_analysis()
        
        # Собрать метрики
        train_returns = [r.train_metrics.get('total_return', 0) for r in results]
        test_returns = [r.test_metrics.get('total_return', 0) for r in results]
        
        train_sharpes = [r.train_metrics.get('sharpe_ratio', 0) for r in results]
        test_sharpes = [r.test_metrics.get('sharpe_ratio', 0) for r in results]
        
        train_win_rates = [r.train_metrics.get('win_rate', 0) for r in results]
        test_win_rates = [r.test_metrics.get('win_rate', 0) for r in results]
        
        train_profit_factors = [r.train_metrics.get('profit_factor', 0) for r in results]
        test_profit_factors = [r.test_metrics.get('profit_factor', 0) for r in results]
        
        train_max_dds = [r.train_metrics.get('max_drawdown_pct', 0) for r in results]
        test_max_dds = [r.test_metrics.get('max_drawdown_pct', 0) for r in results]
        
        efficiency_ratios = [r.efficiency_ratio for r in results]
        
        # Подсчитать прибыльные окна
        profitable_train = sum(1 for r in train_returns if r > 0)
        profitable_test = sum(1 for r in test_returns if r > 0)
        
        # Degradation (среднее ухудшение от train к test)
        avg_train_return = np.mean(train_returns) if train_returns else 0
        avg_test_return = np.mean(test_returns) if test_returns else 0
        
        if avg_train_return != 0:
            degradation_pct = ((avg_test_return - avg_train_return) / abs(avg_train_return)) * 100
        else:
            degradation_pct = 0
        
        analysis = {
            'num_windows': len(results),
            
            # Train period stats
            'train': {
                'avg_return': np.mean(train_returns),
                'median_return': np.median(train_returns),
                'std_return': np.std(train_returns),
                'min_return': np.min(train_returns),
                'max_return': np.max(train_returns),
                'avg_sharpe': np.mean(train_sharpes),
                'avg_win_rate': np.mean(train_win_rates),
                'avg_profit_factor': np.mean(train_profit_factors),
                'avg_max_dd': np.mean(train_max_dds),
                'profitable_windows': profitable_train,
            },
            
            # Test period stats (out-of-sample)
            'test': {
                'avg_return': avg_test_return,
                'median_return': np.median(test_returns),
                'std_return': np.std(test_returns),
                'min_return': np.min(test_returns),
                'max_return': np.max(test_returns),
                'avg_sharpe': np.mean(test_sharpes),
                'avg_win_rate': np.mean(test_win_rates),
                'avg_profit_factor': np.mean(test_profit_factors),
                'avg_max_dd': np.mean(test_max_dds),
                'profitable_windows': profitable_test,
            },
            
            # Consistency metrics
            'consistency': {
                'avg_efficiency_ratio': np.mean(efficiency_ratios),
                'median_efficiency_ratio': np.median(efficiency_ratios),
                'std_efficiency_ratio': np.std(efficiency_ratios),
                'degradation_pct': degradation_pct,
                'test_profitable_pct': (profitable_test / len(results)) * 100,
            },
            
            # All windows data for detailed analysis
            'windows': [
                {
                    'window_id': r.window.window_id,
                    'train_return': r.train_metrics.get('total_return', 0),
                    'test_return': r.test_metrics.get('total_return', 0),
                    'efficiency': r.efficiency_ratio,
                } for r in results
            ]
        }
        
        return analysis
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Пустой результат анализа"""
        return {
            'num_windows': 0,
            'train': {},
            'test': {},
            'consistency': {},
            'windows': []
        }
    
    def get_results_dataframe(
        self,
        results: List[WalkForwardResult]
    ) -> pd.DataFrame:
        """
        Конвертировать результаты в DataFrame.
        
        Args:
            results: Список результатов окон
            
        Returns:
            DataFrame с результатами каждого окна
        """
        if not results:
            return pd.DataFrame()
        
        data = []
        for r in results:
            row = {
                'window_id': r.window.window_id,
                'train_start': r.window.train_start,
                'train_end': r.window.train_end,
                'test_start': r.window.test_start,
                'test_end': r.window.test_end,
                'train_size': r.window.train_size,
                'test_size': r.window.test_size,
                
                # Train metrics
                'train_return': r.train_metrics.get('total_return', 0),
                'train_sharpe': r.train_metrics.get('sharpe_ratio', 0),
                'train_win_rate': r.train_metrics.get('win_rate', 0),
                'train_profit_factor': r.train_metrics.get('profit_factor', 0),
                'train_max_dd': r.train_metrics.get('max_drawdown_pct', 0),
                'train_trades': r.train_metrics.get('total_trades', 0),
                
                # Test metrics
                'test_return': r.test_metrics.get('total_return', 0),
                'test_sharpe': r.test_metrics.get('sharpe_ratio', 0),
                'test_win_rate': r.test_metrics.get('win_rate', 0),
                'test_profit_factor': r.test_metrics.get('profit_factor', 0),
                'test_max_dd': r.test_metrics.get('max_drawdown_pct', 0),
                'test_trades': r.test_metrics.get('total_trades', 0),
                
                # Efficiency
                'efficiency_ratio': r.efficiency_ratio,
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def check_criteria(
        self,
        analysis: Dict[str, Any],
        min_test_win_rate: float = 42.0,
        min_test_profit_factor: float = 1.5,
        max_test_drawdown: float = 15.0,
        max_degradation_pct: float = -30.0
    ) -> Dict[str, Any]:
        """
        Проверить критерии успешности walk-forward.
        
        Args:
            analysis: Результаты анализа
            min_test_win_rate: Минимальный win rate на test
            min_test_profit_factor: Минимальный profit factor на test
            max_test_drawdown: Максимальный drawdown на test
            max_degradation_pct: Максимальная допустимая деградация (%)
            
        Returns:
            Dict со статусом проверки
        """
        test_data = analysis.get('test', {})
        consistency = analysis.get('consistency', {})
        
        criteria = {
            'test_win_rate': {
                'required': min_test_win_rate,
                'actual': test_data.get('avg_win_rate', 0),
                'passed': test_data.get('avg_win_rate', 0) >= min_test_win_rate,
            },
            'test_profit_factor': {
                'required': min_test_profit_factor,
                'actual': test_data.get('avg_profit_factor', 0),
                'passed': test_data.get('avg_profit_factor', 0) >= min_test_profit_factor,
            },
            'test_max_drawdown': {
                'required': max_test_drawdown,
                'actual': test_data.get('avg_max_dd', 100),
                'passed': test_data.get('avg_max_dd', 100) <= max_test_drawdown,
            },
            'degradation': {
                'required': max_degradation_pct,
                'actual': consistency.get('degradation_pct', -100),
                'passed': consistency.get('degradation_pct', -100) >= max_degradation_pct,
            }
        }
        
        all_passed = all(c['passed'] for c in criteria.values())
        
        return {
            'passed': all_passed,
            'criteria': criteria,
        }

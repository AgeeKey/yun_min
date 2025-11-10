"""
Performance Metrics - расчёт метрик эффективности стратегии
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TradeResult:
    """Результат одной сделки"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    side: str  # 'LONG' or 'SHORT'
    amount: float
    pnl: float
    pnl_pct: float
    fees: float


class PerformanceMetrics:
    """
    Расчёт метрик производительности стратегии.
    
    Метрики:
    - Total Return
    - Sharpe Ratio
    - Max Drawdown
    - Win Rate
    - Profit Factor
    - Average Trade
    - Recovery Factor
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.trades: List[TradeResult] = []
        self.equity_curve: List[float] = [initial_capital]
        self.initial_capital = initial_capital
        self.current_equity = initial_capital
        
    def add_trade(self, trade: TradeResult):
        """Добавить сделку"""
        self.trades.append(trade)
        # Update equity curve immediately
        self.current_equity += (trade.pnl - trade.fees)
        self.equity_curve.append(self.current_equity)
    
    def calculate_metrics(
        self,
        initial_capital: float = 100000.0
    ) -> Dict[str, float]:
        """
        Рассчитать все метрики.
        
        Args:
            initial_capital: Начальный капитал
            
        Returns:
            Dictionary с метриками
        """
        if not self.trades:
            return self._empty_metrics()
        
        # Базовые метрики
        total_pnl = sum(t.pnl for t in self.trades)
        total_fees = sum(t.fees for t in self.trades)
        net_pnl = total_pnl - total_fees
        
        total_return = (net_pnl / initial_capital) * 100
        
        # Win/Loss stats
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]
        
        win_rate = (len(winning_trades) / len(self.trades)) * 100 if self.trades else 0
        
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        
        # Profit Factor
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Equity curve
        equity = initial_capital
        equity_curve = [equity]
        
        for trade in self.trades:
            equity += (trade.pnl - trade.fees)
            equity_curve.append(equity)
        
        self.equity_curve = equity_curve
        
        # Max Drawdown
        max_dd, max_dd_pct = self._calculate_max_drawdown(equity_curve)
        
        # Sharpe Ratio (annualized)
        sharpe = self._calculate_sharpe_ratio(equity_curve, initial_capital)
        
        # Sortino Ratio (annualized)
        sortino = self._calculate_sortino_ratio(equity_curve, initial_capital)
        
        # Trading stats
        avg_trade = net_pnl / len(self.trades) if self.trades else 0
        
        # Лучшая и худшая сделки
        best_trade = max([t.pnl for t in self.trades]) if self.trades else 0
        worst_trade = min([t.pnl for t in self.trades]) if self.trades else 0
        
        # Recovery Factor
        recovery_factor = net_pnl / abs(max_dd) if max_dd != 0 else 0
        
        # Trade duration
        trade_durations = [
            (t.exit_time - t.entry_time).total_seconds() / 3600  # hours
            for t in self.trades
        ]
        avg_duration = np.mean(trade_durations) if trade_durations else 0
        
        return {
            # P&L
            'total_pnl': total_pnl,
            'total_fees': total_fees,
            'net_pnl': net_pnl,
            'total_return': total_return,
            
            # Win/Loss
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            
            # Risk metrics
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown': max_dd,
            'max_drawdown_pct': max_dd_pct,
            'recovery_factor': recovery_factor,
            
            # Trading
            'avg_trade': avg_trade,
            'avg_duration_hours': avg_duration,
            
            # Final
            'final_equity': equity_curve[-1] if equity_curve else initial_capital
        }
    
    def _calculate_max_drawdown(
        self,
        equity_curve: List[float]
    ) -> tuple[float, float]:
        """
        Рассчитать максимальную просадку.
        
        Returns:
            (max_drawdown_absolute, max_drawdown_percent)
        """
        if len(equity_curve) < 2:
            return 0.0, 0.0
        
        peak = equity_curve[0]
        max_dd = 0.0
        max_dd_pct = 0.0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            
            dd = peak - equity
            dd_pct = (dd / peak) * 100 if peak > 0 else 0
            
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
        
        return max_dd, max_dd_pct
    
    def _calculate_sharpe_ratio(
        self,
        equity_curve: List[float],
        initial_capital: float,
        risk_free_rate: float = 0.02  # 2% годовых
    ) -> float:
        """
        Рассчитать Sharpe Ratio (annualized).
        
        Sharpe Ratio = (Return - Risk Free Rate) / Volatility
        """
        if len(equity_curve) < 2:
            return 0.0
        
        # Рассчитать returns
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Среднее и стандартное отклонение
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualize (предполагаем дневные returns)
        # 252 торговых дня в году
        annualized_return = mean_return * 252
        annualized_std = std_return * np.sqrt(252)
        
        sharpe = (annualized_return - risk_free_rate) / annualized_std
        
        return sharpe
    
    def _calculate_sortino_ratio(
        self,
        equity_curve: List[float],
        initial_capital: float,
        risk_free_rate: float = 0.02  # 2% годовых
    ) -> float:
        """
        Рассчитать Sortino Ratio (annualized).
        
        Sortino Ratio похож на Sharpe Ratio, но использует только downside volatility
        (учитывает только отрицательные returns).
        
        Sortino Ratio = (Return - Risk Free Rate) / Downside Deviation
        """
        if len(equity_curve) < 2:
            return 0.0
        
        # Рассчитать returns
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Среднее
        mean_return = np.mean(returns)
        
        # Downside returns (только отрицательные)
        downside_returns = [r for r in returns if r < 0]
        
        if not downside_returns:
            # Нет отрицательных returns - бесконечный Sortino
            return float('inf') if mean_return > 0 else 0.0
        
        # Downside deviation
        downside_std = np.std(downside_returns)
        
        if downside_std == 0:
            return 0.0
        
        # Annualize (предполагаем дневные returns)
        # 252 торговых дня в году
        annualized_return = mean_return * 252
        annualized_downside_std = downside_std * np.sqrt(252)
        
        sortino = (annualized_return - risk_free_rate) / annualized_downside_std
        
        return sortino
    
    def _empty_metrics(self) -> Dict[str, float]:
        """Метрики для пустого бэктеста"""
        return {
            'total_pnl': 0.0,
            'total_fees': 0.0,
            'net_pnl': 0.0,
            'total_return': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
            'profit_factor': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'max_drawdown_pct': 0.0,
            'recovery_factor': 0.0,
            'avg_trade': 0.0,
            'avg_duration_hours': 0.0,
            'final_equity': 0.0
        }
    
    def get_monthly_returns(self) -> pd.DataFrame:
        """
        Рассчитать помесячные returns.
        
        Returns:
            DataFrame с колонками: month, return_pct, trades
        """
        if not self.trades:
            return pd.DataFrame()
        
        # Группировка по месяцам
        monthly_data = {}
        
        for trade in self.trades:
            month_key = trade.exit_time.strftime('%Y-%m')
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'pnl': 0.0,
                    'fees': 0.0,
                    'trades': 0
                }
            
            monthly_data[month_key]['pnl'] += trade.pnl
            monthly_data[month_key]['fees'] += trade.fees
            monthly_data[month_key]['trades'] += 1
        
        # Конвертировать в DataFrame
        rows = []
        for month, data in sorted(monthly_data.items()):
            rows.append({
                'month': month,
                'net_pnl': data['pnl'] - data['fees'],
                'trades': data['trades']
            })
        
        return pd.DataFrame(rows)
    
    def get_trade_distribution(self) -> Dict[str, int]:
        """
        Распределение сделок по результатам.
        
        Returns:
            {
                'big_win': count (>5% profit),
                'small_win': count (0-5% profit),
                'small_loss': count (0 to -5% loss),
                'big_loss': count (< -5% loss)
            }
        """
        distribution = {
            'big_win': 0,      # > 5%
            'small_win': 0,    # 0-5%
            'small_loss': 0,   # 0 to -5%
            'big_loss': 0      # < -5%
        }
        
        for trade in self.trades:
            pnl_pct = trade.pnl_pct
            
            if pnl_pct > 5.0:
                distribution['big_win'] += 1
            elif pnl_pct > 0:
                distribution['small_win'] += 1
            elif pnl_pct > -5.0:
                distribution['small_loss'] += 1
            else:
                distribution['big_loss'] += 1
        
        return distribution

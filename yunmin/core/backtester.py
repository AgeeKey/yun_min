"""
Advanced Backtester module for historical data analysis and strategy validation.

Features:
- Walk-forward validation
- Monte Carlo simulations
- Out-of-sample testing
- Parametric optimization (grid search, genetic algorithms)
- Comprehensive performance metrics
- HTML report generation
"""

from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import pandas as pd
import numpy as np
from datetime import datetime
import itertools
import json

logger = logging.getLogger(__name__)


class TradeType(Enum):
    """Trade types."""
    LONG = "long"
    SHORT = "short"


class OptimizationMethod(Enum):
    """Optimization methods."""
    GRID_SEARCH = "grid_search"
    GENETIC_ALGORITHM = "genetic_algorithm"
    RANDOM_SEARCH = "random_search"


@dataclass
class BacktestResult:
    """Backtest result dataclass with comprehensive metrics."""
    trades: List[Dict]
    total_profit: float
    win_rate: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    
    # Additional metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    calmar_ratio: Optional[float] = None
    recovery_factor: Optional[float] = None
    
    # Equity curve
    equity_curve: List[float] = field(default_factory=list)
    
    # Validation results
    is_out_of_sample: bool = False
    validation_period: Optional[str] = None


@dataclass
class OptimizationResult:
    """Optimization result."""
    best_params: Dict[str, Any]
    best_score: float
    all_results: List[Dict[str, Any]]
    optimization_method: str
    metric_optimized: str


class AdvancedBacktester:
    """
    Advanced backtester with walk-forward validation, Monte Carlo, and optimization.
    
    Usage:
        backtester = AdvancedBacktester(symbol="BTC/USDT", timeframe="5m")
        
        # Simple backtest
        result = backtester.run(strategy, data, initial_capital=10000)
        
        # Walk-forward validation
        results = backtester.walk_forward_validation(strategy, data, train_period=0.7)
        
        # Monte Carlo simulation
        mc_results = backtester.monte_carlo_simulation(strategy, data, n_simulations=1000)
        
        # Parameter optimization
        best_params = backtester.optimize_parameters(
            strategy_class, 
            data,
            param_grid={'fast_period': [9, 12], 'slow_period': [21, 26]}
        )
    """
    
    def __init__(self, symbol: str = "BTC/USDT", timeframe: str = "5m"):
        """Initialize advanced backtester."""
        self.symbol = symbol
        self.timeframe = timeframe
        self.trades: List[Dict] = []
        
    def run(
        self,
        strategy,
        data: pd.DataFrame,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005
    ) -> BacktestResult:
        """
        Run backtest on strategy.
        
        Args:
            strategy: Strategy instance with analyze() method
            data: DataFrame with OHLCV data
            initial_capital: Starting capital
            commission: Commission rate (0.001 = 0.1%)
            slippage: Slippage rate (0.0005 = 0.05%)
            
        Returns:
            BacktestResult with comprehensive metrics
        """
        logger.info(f"Starting backtest for {self.symbol}")
        
        capital = initial_capital
        position = None
        trades = []
        equity_curve = [initial_capital]
        
        for i in range(len(data)):
            if i < 50:  # Need minimum data for indicators
                equity_curve.append(capital)
                continue
            
            window = data.iloc[:i+1]
            signal = strategy.analyze(window)
            current_price = data.iloc[i]['close']
            
            # Execute trades based on signals
            if position is None and signal.type.value in ['buy', 'sell']:
                # Open position
                position_size = capital * 0.95  # Use 95% of capital
                position = {
                    'type': signal.type.value,
                    'entry_price': current_price * (1 + slippage),
                    'entry_time': i,
                    'size': position_size / current_price,
                    'signal': signal
                }
                
            elif position is not None and signal.type.value == 'hold':
                # Close position
                exit_price = current_price * (1 - slippage)
                
                if position['type'] == 'buy':
                    pnl = (exit_price - position['entry_price']) * position['size']
                else:  # sell/short
                    pnl = (position['entry_price'] - exit_price) * position['size']
                
                # Apply commission
                pnl -= (position['entry_price'] * position['size'] + exit_price * position['size']) * commission
                
                capital += pnl
                
                trades.append({
                    'type': position['type'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'entry_time': position['entry_time'],
                    'exit_time': i,
                    'pnl': pnl,
                    'return': pnl / (position['entry_price'] * position['size']),
                    'signal_confidence': position['signal'].confidence
                })
                
                position = None
            
            equity_curve.append(capital)
        
        # Calculate metrics
        return self._calculate_metrics(trades, equity_curve, initial_capital)
    
    def _calculate_metrics(
        self, 
        trades: List[Dict], 
        equity_curve: List[float],
        initial_capital: float
    ) -> BacktestResult:
        """Calculate comprehensive performance metrics."""
        
        if not trades:
            return BacktestResult(
                trades=[],
                total_profit=0.0,
                win_rate=0.0,
                max_drawdown=0.0,
                equity_curve=equity_curve
            )
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0.0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0.0
        
        total_profit = sum(t['pnl'] for t in trades)
        
        # Profit factor
        gross_profit = sum(t['pnl'] for t in winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        # Expectancy
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))
        
        # Drawdown
        peak = initial_capital
        max_drawdown = 0.0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Returns for Sharpe/Sortino
        returns = pd.Series(equity_curve).pct_change().dropna()
        
        # Sharpe ratio (annualized, assuming 365 days of 5-min bars)
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(365 * 288)
        else:
            sharpe_ratio = 0.0
        
        # Sortino ratio (using downside deviation)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0 and downside_returns.std() > 0:
            sortino_ratio = (returns.mean() / downside_returns.std()) * np.sqrt(365 * 288)
        else:
            sortino_ratio = 0.0
        
        # Calmar ratio (return / max drawdown)
        annual_return = (equity_curve[-1] / initial_capital - 1) * (365 / (len(equity_curve) / 288))
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0.0
        
        # Recovery factor
        recovery_factor = total_profit / (initial_capital * max_drawdown) if max_drawdown > 0 else 0.0
        
        return BacktestResult(
            trades=trades,
            total_profit=total_profit,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            calmar_ratio=calmar_ratio,
            recovery_factor=recovery_factor,
            equity_curve=equity_curve
        )
    
    def walk_forward_validation(
        self,
        strategy_class,
        data: pd.DataFrame,
        train_ratio: float = 0.7,
        n_splits: int = 3,
        initial_capital: float = 10000.0
    ) -> List[BacktestResult]:
        """
        Perform walk-forward validation.
        
        Args:
            strategy_class: Strategy class (not instance)
            data: Full dataset
            train_ratio: Ratio of data for training (0.7 = 70%)
            n_splits: Number of walk-forward windows
            initial_capital: Starting capital
            
        Returns:
            List of BacktestResult for each out-of-sample period
        """
        logger.info(f"Walk-forward validation with {n_splits} splits, train ratio {train_ratio}")
        
        results = []
        window_size = len(data) // n_splits
        
        for i in range(n_splits):
            start_idx = i * window_size
            end_idx = min((i + 1) * window_size, len(data))
            
            window_data = data.iloc[start_idx:end_idx]
            train_size = int(len(window_data) * train_ratio)
            
            train_data = window_data.iloc[:train_size]
            test_data = window_data.iloc[train_size:]
            
            # Create strategy instance (could be optimized on train_data)
            strategy = strategy_class()
            
            # Backtest on out-of-sample data
            result = self.run(strategy, test_data, initial_capital)
            result.is_out_of_sample = True
            result.validation_period = f"Split {i+1}/{n_splits}"
            
            results.append(result)
            logger.info(
                f"Split {i+1}: Profit={result.total_profit:.2f}, "
                f"Win Rate={result.win_rate*100:.1f}%, Sharpe={result.sharpe_ratio:.2f}"
            )
        
        return results
    
    def monte_carlo_simulation(
        self,
        trades: List[Dict],
        n_simulations: int = 1000,
        initial_capital: float = 10000.0
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation on trade results.
        
        Args:
            trades: List of historical trades
            n_simulations: Number of simulations to run
            initial_capital: Starting capital
            
        Returns:
            Dictionary with simulation statistics
        """
        logger.info(f"Running Monte Carlo simulation with {n_simulations} iterations")
        
        if not trades:
            return {'error': 'No trades to simulate'}
        
        final_capitals = []
        max_drawdowns = []
        
        for _ in range(n_simulations):
            # Randomly sample trades with replacement
            sampled_trades = np.random.choice(trades, size=len(trades), replace=True)
            
            capital = initial_capital
            peak = initial_capital
            max_dd = 0.0
            
            for trade in sampled_trades:
                capital += trade['pnl']
                
                if capital > peak:
                    peak = capital
                drawdown = (peak - capital) / peak if peak > 0 else 0.0
                if drawdown > max_dd:
                    max_dd = drawdown
            
            final_capitals.append(capital)
            max_drawdowns.append(max_dd)
        
        final_capitals = np.array(final_capitals)
        max_drawdowns = np.array(max_drawdowns)
        
        return {
            'final_capital_mean': float(final_capitals.mean()),
            'final_capital_median': float(np.median(final_capitals)),
            'final_capital_std': float(final_capitals.std()),
            'final_capital_min': float(final_capitals.min()),
            'final_capital_max': float(final_capitals.max()),
            'percentile_5': float(np.percentile(final_capitals, 5)),
            'percentile_95': float(np.percentile(final_capitals, 95)),
            'max_dd_mean': float(max_drawdowns.mean()),
            'max_dd_median': float(np.median(max_drawdowns)),
            'max_dd_worst': float(max_drawdowns.max()),
            'n_simulations': n_simulations
        }
    
    def optimize_parameters(
        self,
        strategy_class,
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        optimization_metric: str = 'sharpe_ratio',
        method: OptimizationMethod = OptimizationMethod.GRID_SEARCH,
        initial_capital: float = 10000.0
    ) -> OptimizationResult:
        """
        Optimize strategy parameters.
        
        Args:
            strategy_class: Strategy class
            data: Historical data
            param_grid: Dictionary of parameter names and values to test
            optimization_metric: Metric to optimize ('sharpe_ratio', 'total_profit', etc.)
            method: Optimization method
            initial_capital: Starting capital
            
        Returns:
            OptimizationResult with best parameters
        """
        logger.info(f"Parameter optimization using {method.value}")
        
        if method == OptimizationMethod.GRID_SEARCH:
            return self._grid_search(
                strategy_class, data, param_grid, optimization_metric, initial_capital
            )
        else:
            raise NotImplementedError(f"Method {method.value} not implemented yet")
    
    def _grid_search(
        self,
        strategy_class,
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        metric: str,
        initial_capital: float
    ) -> OptimizationResult:
        """Perform grid search optimization."""
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))
        
        logger.info(f"Testing {len(combinations)} parameter combinations")
        
        results = []
        best_score = float('-inf')
        best_params = None
        
        for combo in combinations:
            params = dict(zip(param_names, combo))
            
            try:
                # Create strategy with these parameters
                strategy = strategy_class(**params)
                
                # Run backtest
                result = self.run(strategy, data, initial_capital)
                
                # Get metric value
                score = getattr(result, metric, 0.0)
                
                results.append({
                    'params': params,
                    'score': score,
                    'total_profit': result.total_profit,
                    'win_rate': result.win_rate,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown
                })
                
                if score > best_score:
                    best_score = score
                    best_params = params
                    
                logger.debug(f"Params: {params} -> {metric}={score:.3f}")
                
            except Exception as e:
                logger.error(f"Error testing params {params}: {e}")
                continue
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_results=results,
            optimization_method=OptimizationMethod.GRID_SEARCH.value,
            metric_optimized=metric
        )
    
    def generate_html_report(
        self, 
        result: BacktestResult, 
        strategy_name: str = "Strategy",
        output_path: str = "backtest_report.html"
    ) -> str:
        """
        Generate HTML report for backtest results.
        
        Args:
            result: Backtest result
            strategy_name: Name of strategy
            output_path: Path to save HTML file
            
        Returns:
            Path to generated HTML file
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Backtest Report - {strategy_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .metric {{ margin: 10px 0; }}
                .metric-name {{ font-weight: bold; display: inline-block; width: 200px; }}
                .metric-value {{ color: #0066cc; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
            </style>
        </head>
        <body>
            <h1>Backtest Report: {strategy_name}</h1>
            <h2>Performance Metrics</h2>
            
            <div class="metric">
                <span class="metric-name">Total Profit:</span>
                <span class="metric-value {'positive' if result.total_profit > 0 else 'negative'}">
                    ${result.total_profit:.2f}
                </span>
            </div>
            
            <div class="metric">
                <span class="metric-name">Total Trades:</span>
                <span class="metric-value">{result.total_trades}</span>
            </div>
            
            <div class="metric">
                <span class="metric-name">Win Rate:</span>
                <span class="metric-value">{result.win_rate*100:.2f}%</span>
            </div>
            
            <div class="metric">
                <span class="metric-name">Winning Trades:</span>
                <span class="metric-value positive">{result.winning_trades}</span>
            </div>
            
            <div class="metric">
                <span class="metric-name">Losing Trades:</span>
                <span class="metric-value negative">{result.losing_trades}</span>
            </div>
            
            <div class="metric">
                <span class="metric-name">Average Win:</span>
                <span class="metric-value positive">${result.avg_win:.2f}</span>
            </div>
            
            <div class="metric">
                <span class="metric-name">Average Loss:</span>
                <span class="metric-value negative">${result.avg_loss:.2f}</span>
            </div>
            
            <div class="metric">
                <span class="metric-name">Profit Factor:</span>
                <span class="metric-value">{result.profit_factor:.2f}</span>
            </div>
            
            <div class="metric">
                <span class="metric-name">Expectancy:</span>
                <span class="metric-value">${result.expectancy:.2f}</span>
            </div>
            
            <div class="metric">
                <span class="metric-name">Max Drawdown:</span>
                <span class="metric-value negative">{result.max_drawdown*100:.2f}%</span>
            </div>
            
            <div class="metric">
                <span class="metric-name">Sharpe Ratio:</span>
                <span class="metric-value">{result.sharpe_ratio:.2f}</span>
            </div>
            
            <div class="metric">
                <span class="metric-name">Sortino Ratio:</span>
                <span class="metric-value">{result.sortino_ratio:.2f}</span>
            </div>
            
            <div class="metric">
                <span class="metric-name">Calmar Ratio:</span>
                <span class="metric-value">{result.calmar_ratio:.2f}</span>
            </div>
            
            <h2>Trade History</h2>
            <table>
                <tr>
                    <th>Type</th>
                    <th>Entry Price</th>
                    <th>Exit Price</th>
                    <th>P&L</th>
                    <th>Return %</th>
                </tr>
        """
        
        for trade in result.trades[:50]:  # Show first 50 trades
            pnl_class = 'positive' if trade['pnl'] > 0 else 'negative'
            html += f"""
                <tr>
                    <td>{trade['type']}</td>
                    <td>${trade['entry_price']:.2f}</td>
                    <td>${trade['exit_price']:.2f}</td>
                    <td class="{pnl_class}">${trade['pnl']:.2f}</td>
                    <td class="{pnl_class}">{trade['return']*100:.2f}%</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"HTML report generated: {output_path}")
        return output_path


# Keep original Backtester for backward compatibility
Backtester = AdvancedBacktester

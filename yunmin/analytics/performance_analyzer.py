"""
Performance Analytics Engine for YunMin Trading Bot
Provides deep performance analysis, attribution, risk metrics, and benchmarking
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, UTC
from pathlib import Path
from loguru import logger


@dataclass
class Trade:
    """Individual trade record"""
    symbol: str
    side: str  # LONG/SHORT
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    amount: float
    pnl: float
    pnl_pct: float
    strategy: str = "unknown"
    fees: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> timedelta:
        """Trade duration"""
        return self.exit_time - self.entry_time
    
    @property
    def is_win(self) -> bool:
        """Check if trade is a winner"""
        return self.pnl > 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['entry_time'] = self.entry_time.isoformat()
        data['exit_time'] = self.exit_time.isoformat()
        data['duration_hours'] = self.duration.total_seconds() / 3600
        return data


@dataclass
class PerformanceMetrics:
    """Performance metrics summary"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    total_pnl: float
    total_pnl_pct: float
    gross_profit: float
    gross_loss: float
    
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float
    
    max_drawdown: float
    max_drawdown_pct: float
    avg_drawdown: float
    
    var_95: float  # Value at Risk 95%
    cvar_95: float  # Conditional VaR 95%
    
    avg_trade_duration_hours: float
    avg_win_duration_hours: float
    avg_loss_duration_hours: float
    
    best_day: float
    worst_day: float
    avg_daily_pnl: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class AttributionMetrics:
    """Attribution analysis metrics"""
    by_strategy: Dict[str, float]
    by_symbol: Dict[str, float]
    by_hour: Dict[int, float]
    by_day_of_week: Dict[str, float]
    by_market_condition: Dict[str, float]


class PerformanceAnalyzer:
    """
    Deep performance analytics engine.
    
    Features:
    - Trade-by-trade analysis
    - Win/Loss distribution
    - Attribution analysis (strategy, time, market conditions)
    - Advanced risk metrics (VaR, CVaR, Sharpe, Sortino)
    - Benchmarking against Buy & Hold and market index
    - Export to Excel/CSV
    """
    
    def __init__(self):
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.initial_capital: float = 15000.0
    
    def add_trade(self, trade: Trade):
        """
        Add a trade to the analyzer.
        
        Args:
            trade: Trade object
        """
        self.trades.append(trade)
        logger.debug(f"Added trade: {trade.symbol} {trade.side} P&L: ${trade.pnl:.2f}")
    
    def add_equity_point(self, timestamp: datetime, equity: float):
        """
        Add an equity curve data point.
        
        Args:
            timestamp: Timestamp
            equity: Equity value
        """
        self.equity_curve.append((timestamp, equity))
    
    def analyze_trades(self) -> PerformanceMetrics:
        """
        Perform comprehensive trade analysis.
        
        Returns:
            PerformanceMetrics object
        """
        if not self.trades:
            logger.warning("No trades to analyze")
            return self._empty_metrics()
        
        # Basic stats
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.is_win)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        # P&L stats
        total_pnl = sum(t.pnl for t in self.trades)
        gross_profit = sum(t.pnl for t in self.trades if t.is_win)
        gross_loss = abs(sum(t.pnl for t in self.trades if not t.is_win))
        
        wins = [t.pnl for t in self.trades if t.is_win]
        losses = [abs(t.pnl) for t in self.trades if not t.is_win]
        
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0
        largest_win = max(wins) if wins else 0.0
        largest_loss = max(losses) if losses else 0.0
        
        # Profit factor
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        # Calculate returns series
        returns = pd.Series([t.pnl_pct / 100 for t in self.trades])
        
        # Sharpe ratio (annualized, assuming 252 trading days)
        if len(returns) > 1 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0
        
        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 1 and downside_returns.std() > 0:
            sortino_ratio = (returns.mean() / downside_returns.std()) * np.sqrt(252)
        else:
            sortino_ratio = 0.0
        
        # Drawdown analysis
        equity_series = self._calculate_equity_series()
        max_dd, max_dd_pct, avg_dd = self._calculate_drawdowns(equity_series)
        
        # Value at Risk (VaR) and Conditional VaR (CVaR)
        var_95 = self._calculate_var(returns, 0.95)
        cvar_95 = self._calculate_cvar(returns, 0.95)
        
        # Duration analysis
        durations = [t.duration.total_seconds() / 3600 for t in self.trades]
        win_durations = [t.duration.total_seconds() / 3600 for t in self.trades if t.is_win]
        loss_durations = [t.duration.total_seconds() / 3600 for t in self.trades if not t.is_win]
        
        avg_trade_duration = np.mean(durations) if durations else 0.0
        avg_win_duration = np.mean(win_durations) if win_durations else 0.0
        avg_loss_duration = np.mean(loss_durations) if loss_durations else 0.0
        
        # Daily P&L analysis
        daily_pnl = self._group_by_day()
        best_day = max(daily_pnl.values()) if daily_pnl else 0.0
        worst_day = min(daily_pnl.values()) if daily_pnl else 0.0
        avg_daily_pnl = np.mean(list(daily_pnl.values())) if daily_pnl else 0.0
        
        # Calculate total P&L percentage
        current_equity = self.initial_capital + total_pnl
        total_pnl_pct = (total_pnl / self.initial_capital * 100) if self.initial_capital > 0 else 0.0
        
        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            avg_drawdown=avg_dd,
            var_95=var_95,
            cvar_95=cvar_95,
            avg_trade_duration_hours=avg_trade_duration,
            avg_win_duration_hours=avg_win_duration,
            avg_loss_duration_hours=avg_loss_duration,
            best_day=best_day,
            worst_day=worst_day,
            avg_daily_pnl=avg_daily_pnl
        )
    
    def attribution_analysis(self) -> AttributionMetrics:
        """
        Perform attribution analysis.
        
        Returns:
            AttributionMetrics object
        """
        if not self.trades:
            return AttributionMetrics(
                by_strategy={},
                by_symbol={},
                by_hour={},
                by_day_of_week={},
                by_market_condition={}
            )
        
        # By strategy
        by_strategy = {}
        for trade in self.trades:
            strategy = trade.strategy
            by_strategy[strategy] = by_strategy.get(strategy, 0.0) + trade.pnl
        
        # By symbol
        by_symbol = {}
        for trade in self.trades:
            symbol = trade.symbol
            by_symbol[symbol] = by_symbol.get(symbol, 0.0) + trade.pnl
        
        # By hour of day
        by_hour = {}
        for trade in self.trades:
            hour = trade.entry_time.hour
            by_hour[hour] = by_hour.get(hour, 0.0) + trade.pnl
        
        # By day of week
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        by_day_of_week = {}
        for trade in self.trades:
            day = day_names[trade.entry_time.weekday()]
            by_day_of_week[day] = by_day_of_week.get(day, 0.0) + trade.pnl
        
        # By market condition (from metadata)
        by_market_condition = {}
        for trade in self.trades:
            condition = trade.metadata.get('market_condition', 'unknown')
            by_market_condition[condition] = by_market_condition.get(condition, 0.0) + trade.pnl
        
        return AttributionMetrics(
            by_strategy=by_strategy,
            by_symbol=by_symbol,
            by_hour=by_hour,
            by_day_of_week=by_day_of_week,
            by_market_condition=by_market_condition
        )
    
    def get_best_worst_performers(self, top_n: int = 5) -> Dict[str, List[Trade]]:
        """
        Get best and worst performing trades.
        
        Args:
            top_n: Number of trades to return
        
        Returns:
            Dictionary with 'best' and 'worst' trade lists
        """
        sorted_trades = sorted(self.trades, key=lambda t: t.pnl, reverse=True)
        
        return {
            'best': sorted_trades[:top_n],
            'worst': sorted_trades[-top_n:][::-1]  # Reverse to show worst first
        }
    
    def get_win_loss_distribution(self, bins: int = 20) -> Dict[str, Any]:
        """
        Get win/loss distribution histogram.
        
        Args:
            bins: Number of histogram bins
        
        Returns:
            Dictionary with histogram data
        """
        if not self.trades:
            return {'wins': {}, 'losses': {}}
        
        wins = [t.pnl for t in self.trades if t.is_win]
        losses = [t.pnl for t in self.trades if not t.is_win]
        
        win_hist = {}
        loss_hist = {}
        
        if wins:
            win_counts, win_bins = np.histogram(wins, bins=bins)
            win_hist = {f"${win_bins[i]:.0f}-${win_bins[i+1]:.0f}": int(win_counts[i]) 
                       for i in range(len(win_counts))}
        
        if losses:
            loss_counts, loss_bins = np.histogram(losses, bins=bins)
            loss_hist = {f"${loss_bins[i]:.0f}-${loss_bins[i+1]:.0f}": int(loss_counts[i]) 
                        for i in range(len(loss_counts))}
        
        return {
            'wins': win_hist,
            'losses': loss_hist
        }
    
    def benchmark_vs_buy_hold(self, symbol: str, start_price: float, end_price: float) -> Dict[str, float]:
        """
        Compare performance against buy & hold strategy.
        
        Args:
            symbol: Symbol to compare
            start_price: Starting price
            end_price: Ending price
        
        Returns:
            Dictionary with comparison metrics
        """
        metrics = self.analyze_trades()
        
        # Calculate buy & hold return
        buy_hold_return = ((end_price - start_price) / start_price) * 100
        buy_hold_pnl = (buy_hold_return / 100) * self.initial_capital
        
        # Our strategy performance
        strategy_return = metrics.total_pnl_pct
        strategy_pnl = metrics.total_pnl
        
        # Comparison
        outperformance = strategy_return - buy_hold_return
        
        return {
            'strategy_return_pct': strategy_return,
            'strategy_pnl': strategy_pnl,
            'buy_hold_return_pct': buy_hold_return,
            'buy_hold_pnl': buy_hold_pnl,
            'outperformance_pct': outperformance,
            'win_rate': metrics.win_rate,
            'sharpe_ratio': metrics.sharpe_ratio,
            'max_drawdown': metrics.max_drawdown_pct
        }
    
    def export_to_csv(self, filepath: str):
        """
        Export trades to CSV file.
        
        Args:
            filepath: Output file path
        """
        if not self.trades:
            logger.warning("No trades to export")
            return
        
        # Validate and sanitize filepath
        path = Path(filepath).resolve()
        
        # Ensure it's within a safe directory (data, exports, /tmp, or current)
        allowed_dirs = [
            Path('data').resolve(), 
            Path('exports').resolve(), 
            Path('.').resolve(),
            Path('/tmp').resolve()
        ]
        is_safe = any(
            str(path).startswith(str(allowed_dir))
            for allowed_dir in allowed_dirs
        )
        
        if not is_safe:
            logger.error(f"❌ Invalid export path: must be within data/, exports/, /tmp, or current directory")
            return
        
        if not str(path).endswith('.csv'):
            path = path.with_suffix('.csv')
        
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        df = pd.DataFrame([t.to_dict() for t in self.trades])
        df.to_csv(str(path), index=False)
        logger.success(f"✅ Exported {len(self.trades)} trades to {path}")
    
    def export_to_excel(self, filepath: str):
        """
        Export comprehensive report to Excel.
        
        Args:
            filepath: Output file path
        """
        if not self.trades:
            logger.warning("No trades to export")
            return
        
        # Validate and sanitize filepath
        path = Path(filepath).resolve()
        
        # Ensure it's within a safe directory (data, exports, /tmp, or current)
        allowed_dirs = [
            Path('data').resolve(), 
            Path('exports').resolve(), 
            Path('.').resolve(),
            Path('/tmp').resolve()
        ]
        is_safe = any(
            str(path).startswith(str(allowed_dir))
            for allowed_dir in allowed_dirs
        )
        
        if not is_safe:
            logger.error(f"❌ Invalid export path: must be within data/, exports/, /tmp, or current directory")
            return
        
        if not str(path).endswith('.xlsx'):
            path = path.with_suffix('.xlsx')
        
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with pd.ExcelWriter(str(path), engine='openpyxl') as writer:
                # Trades sheet
                trades_df = pd.DataFrame([t.to_dict() for t in self.trades])
                trades_df.to_excel(writer, sheet_name='Trades', index=False)
                
                # Metrics sheet
                metrics = self.analyze_trades()
                metrics_df = pd.DataFrame([metrics.to_dict()])
                metrics_df.to_excel(writer, sheet_name='Metrics', index=False)
                
                # Attribution sheet
                attribution = self.attribution_analysis()
                
                # Strategy attribution
                strategy_df = pd.DataFrame([
                    {'Strategy': k, 'P&L': v} 
                    for k, v in attribution.by_strategy.items()
                ])
                strategy_df.to_excel(writer, sheet_name='Attribution_Strategy', index=False)
                
                # Symbol attribution
                symbol_df = pd.DataFrame([
                    {'Symbol': k, 'P&L': v} 
                    for k, v in attribution.by_symbol.items()
                ])
                symbol_df.to_excel(writer, sheet_name='Attribution_Symbol', index=False)
                
                # Time attribution
                hour_df = pd.DataFrame([
                    {'Hour': k, 'P&L': v} 
                    for k, v in sorted(attribution.by_hour.items())
                ])
                hour_df.to_excel(writer, sheet_name='Attribution_Hour', index=False)
                
                day_df = pd.DataFrame([
                    {'Day': k, 'P&L': v} 
                    for k, v in attribution.by_day_of_week.items()
                ])
                day_df.to_excel(writer, sheet_name='Attribution_Day', index=False)
            
            logger.success(f"✅ Exported comprehensive report to {path}")
        
        except ImportError:
            logger.error("❌ openpyxl not installed. Install with: pip install openpyxl")
        except Exception as e:
            logger.error(f"❌ Failed to export to Excel: {e}")
    
    def generate_text_report(self) -> str:
        """
        Generate comprehensive text report.
        
        Returns:
            Formatted text report
        """
        metrics = self.analyze_trades()
        attribution = self.attribution_analysis()
        performers = self.get_best_worst_performers(top_n=3)
        
        report = []
        report.append("=" * 80)
        report.append("YUN MIN TRADING BOT - PERFORMANCE REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Overall Performance
        report.append("OVERALL PERFORMANCE")
        report.append("-" * 80)
        report.append(f"Total Trades:        {metrics.total_trades}")
        report.append(f"Winning Trades:      {metrics.winning_trades} ({metrics.win_rate:.1f}%)")
        report.append(f"Losing Trades:       {metrics.losing_trades}")
        report.append(f"")
        report.append(f"Total P&L:           ${metrics.total_pnl:,.2f} ({metrics.total_pnl_pct:+.2f}%)")
        report.append(f"Gross Profit:        ${metrics.gross_profit:,.2f}")
        report.append(f"Gross Loss:          ${metrics.gross_loss:,.2f}")
        report.append(f"Profit Factor:       {metrics.profit_factor:.2f}")
        report.append("")
        
        # Risk Metrics
        report.append("RISK METRICS")
        report.append("-" * 80)
        report.append(f"Sharpe Ratio:        {metrics.sharpe_ratio:.2f}")
        report.append(f"Sortino Ratio:       {metrics.sortino_ratio:.2f}")
        report.append(f"Max Drawdown:        ${metrics.max_drawdown:,.2f} ({metrics.max_drawdown_pct:.2f}%)")
        report.append(f"Value at Risk (95%): ${metrics.var_95:,.2f}")
        report.append(f"CVaR (95%):          ${metrics.cvar_95:,.2f}")
        report.append("")
        
        # Trade Statistics
        report.append("TRADE STATISTICS")
        report.append("-" * 80)
        report.append(f"Average Win:         ${metrics.avg_win:,.2f}")
        report.append(f"Average Loss:        ${metrics.avg_loss:,.2f}")
        report.append(f"Largest Win:         ${metrics.largest_win:,.2f}")
        report.append(f"Largest Loss:        ${metrics.largest_loss:,.2f}")
        report.append(f"")
        report.append(f"Avg Trade Duration:  {metrics.avg_trade_duration_hours:.1f}h")
        report.append(f"Avg Win Duration:    {metrics.avg_win_duration_hours:.1f}h")
        report.append(f"Avg Loss Duration:   {metrics.avg_loss_duration_hours:.1f}h")
        report.append("")
        
        # Daily Performance
        report.append("DAILY PERFORMANCE")
        report.append("-" * 80)
        report.append(f"Best Day:            ${metrics.best_day:,.2f}")
        report.append(f"Worst Day:           ${metrics.worst_day:,.2f}")
        report.append(f"Average Daily P&L:   ${metrics.avg_daily_pnl:,.2f}")
        report.append("")
        
        # Attribution Analysis
        report.append("ATTRIBUTION ANALYSIS")
        report.append("-" * 80)
        
        if attribution.by_strategy:
            report.append("By Strategy:")
            for strategy, pnl in sorted(attribution.by_strategy.items(), key=lambda x: x[1], reverse=True):
                report.append(f"  {strategy:20s} ${pnl:,.2f}")
            report.append("")
        
        if attribution.by_symbol:
            report.append("By Symbol:")
            for symbol, pnl in sorted(attribution.by_symbol.items(), key=lambda x: x[1], reverse=True):
                report.append(f"  {symbol:20s} ${pnl:,.2f}")
            report.append("")
        
        # Best/Worst Trades
        report.append("TOP PERFORMERS")
        report.append("-" * 80)
        report.append("Best Trades:")
        for i, trade in enumerate(performers['best'], 1):
            report.append(f"  {i}. {trade.symbol} {trade.side} ${trade.pnl:,.2f} ({trade.pnl_pct:+.1f}%)")
        report.append("")
        
        report.append("Worst Trades:")
        for i, trade in enumerate(performers['worst'], 1):
            report.append(f"  {i}. {trade.symbol} {trade.side} ${trade.pnl:,.2f} ({trade.pnl_pct:+.1f}%)")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    # Private helper methods
    
    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics"""
        return PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            total_pnl_pct=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            profit_factor=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            max_drawdown_pct=0.0,
            avg_drawdown=0.0,
            var_95=0.0,
            cvar_95=0.0,
            avg_trade_duration_hours=0.0,
            avg_win_duration_hours=0.0,
            avg_loss_duration_hours=0.0,
            best_day=0.0,
            worst_day=0.0,
            avg_daily_pnl=0.0
        )
    
    def _calculate_equity_series(self) -> pd.Series:
        """Calculate equity curve series"""
        if self.equity_curve:
            # Use provided equity curve
            timestamps, equities = zip(*self.equity_curve)
            return pd.Series(equities, index=timestamps)
        else:
            # Calculate from trades
            sorted_trades = sorted(self.trades, key=lambda t: t.exit_time)
            equity = self.initial_capital
            series_data = [(datetime.min, equity)]
            
            for trade in sorted_trades:
                equity += trade.pnl
                series_data.append((trade.exit_time, equity))
            
            timestamps, equities = zip(*series_data)
            return pd.Series(equities, index=timestamps)
    
    def _calculate_drawdowns(self, equity_series: pd.Series) -> Tuple[float, float, float]:
        """Calculate drawdown metrics"""
        if len(equity_series) < 2:
            return 0.0, 0.0, 0.0
        
        # Calculate running maximum
        running_max = equity_series.expanding().max()
        
        # Calculate drawdowns
        drawdowns = equity_series - running_max
        drawdown_pcts = (drawdowns / running_max) * 100
        
        max_dd = abs(drawdowns.min())
        max_dd_pct = abs(drawdown_pcts.min())
        avg_dd = abs(drawdowns[drawdowns < 0].mean()) if len(drawdowns[drawdowns < 0]) > 0 else 0.0
        
        return max_dd, max_dd_pct, avg_dd
    
    def _calculate_var(self, returns: pd.Series, confidence: float) -> float:
        """Calculate Value at Risk"""
        if len(returns) == 0:
            return 0.0
        
        var = np.percentile(returns, (1 - confidence) * 100)
        return var * self.initial_capital
    
    def _calculate_cvar(self, returns: pd.Series, confidence: float) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""
        if len(returns) == 0:
            return 0.0
        
        var_threshold = np.percentile(returns, (1 - confidence) * 100)
        tail_returns = returns[returns <= var_threshold]
        
        if len(tail_returns) == 0:
            return 0.0
        
        cvar = tail_returns.mean()
        return cvar * self.initial_capital
    
    def _group_by_day(self) -> Dict[str, float]:
        """Group trades by day"""
        daily_pnl = {}
        
        for trade in self.trades:
            day_key = trade.exit_time.strftime('%Y-%m-%d')
            daily_pnl[day_key] = daily_pnl.get(day_key, 0.0) + trade.pnl
        
        return daily_pnl


# Example usage
if __name__ == "__main__":
    # Create analyzer
    analyzer = PerformanceAnalyzer()
    
    # Add sample trades
    analyzer.add_trade(Trade(
        symbol="BTC/USDT",
        side="LONG",
        entry_time=datetime.now(UTC) - timedelta(hours=5),
        exit_time=datetime.now(UTC) - timedelta(hours=2),
        entry_price=50000.0,
        exit_price=51000.0,
        amount=0.1,
        pnl=100.0,
        pnl_pct=2.0,
        strategy="EMA_Crossover"
    ))
    
    analyzer.add_trade(Trade(
        symbol="ETH/USDT",
        side="SHORT",
        entry_time=datetime.now(UTC) - timedelta(hours=3),
        exit_time=datetime.now(UTC) - timedelta(hours=1),
        entry_price=3000.0,
        exit_price=2950.0,
        amount=1.0,
        pnl=50.0,
        pnl_pct=1.67,
        strategy="RSI_Mean_Reversion"
    ))
    
    # Analyze
    metrics = analyzer.analyze_trades()
    print(f"Total P&L: ${metrics.total_pnl:.2f}")
    print(f"Win Rate: {metrics.win_rate:.1f}%")
    print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    
    # Generate report
    print("\n" + analyzer.generate_text_report())

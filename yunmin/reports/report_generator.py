"""
Report generator for backtest results and trading performance.

Inspired by freqtrade/optimize patterns.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics dataclass."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float
    avg_profit_per_trade: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    profit_factor: Optional[float] = None
    recovery_factor: Optional[float] = None


class ReportGenerator:
    """
    Generates trading reports from backtest or live results.
    
    Usage:
        generator = ReportGenerator()
        metrics = generator.analyze_trades(trades)
        report = generator.generate_report(metrics, format="html")
    """
    
    def __init__(self):
        """Initialize report generator."""
        self.generated_reports: List[Dict] = []
        
    def analyze_trades(self, trades: List[Dict]) -> PerformanceMetrics:
        """
        Analyze trades and calculate metrics.
        
        Args:
            trades: List of trade dicts with entry_price, exit_price, entry_time, exit_time, etc.
            
        Returns:
            PerformanceMetrics object
        """
        if not trades:
            return PerformanceMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_profit=0.0,
                avg_profit_per_trade=0.0,
                max_drawdown=0.0
            )
            
        winning = [t for t in trades if t.get("profit", 0) > 0]
        losing = [t for t in trades if t.get("profit", 0) < 0]
        total_profit = sum(t.get("profit", 0) for t in trades)
        
        return PerformanceMetrics(
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=len(winning) / len(trades) if trades else 0.0,
            total_profit=total_profit,
            avg_profit_per_trade=total_profit / len(trades) if trades else 0.0,
            max_drawdown=self._calculate_max_drawdown(trades),
            sharpe_ratio=self._calculate_sharpe_ratio(trades),
            profit_factor=self._calculate_profit_factor(trades)
        )
        
    def generate_report(
        self,
        metrics: PerformanceMetrics,
        format: str = "text",
        output_file: Optional[str] = None
    ) -> str:
        """
        Generate formatted report.
        
        Args:
            metrics: PerformanceMetrics object
            format: "text", "html", or "json"
            output_file: Optional file path to save report
            
        Returns:
            Report string
        """
        if format == "text":
            report = self._generate_text_report(metrics)
        elif format == "html":
            report = self._generate_html_report(metrics)
        else:
            report = str(metrics)
            
        if output_file:
            with open(output_file, "w") as f:
                f.write(report)
            logger.info(f"Report saved to {output_file}")
            
        self.generated_reports.append({"metrics": metrics, "format": format, "timestamp": datetime.utcnow()})
        return report
        
    def _generate_text_report(self, metrics: PerformanceMetrics) -> str:
        """Generate text report."""
        lines = [
            "=" * 50,
            "TRADING PERFORMANCE REPORT",
            "=" * 50,
            f"Total Trades: {metrics.total_trades}",
            f"Winning Trades: {metrics.winning_trades}",
            f"Losing Trades: {metrics.losing_trades}",
            f"Win Rate: {metrics.win_rate:.2%}",
            f"Total Profit: ${metrics.total_profit:.2f}",
            f"Avg Profit/Trade: ${metrics.avg_profit_per_trade:.2f}",
            f"Max Drawdown: {metrics.max_drawdown:.2%}",
            "=" * 50,
        ]
        if metrics.sharpe_ratio:
            lines.insert(-1, f"Sharpe Ratio: {metrics.sharpe_ratio:.3f}")
        if metrics.sortino_ratio:
            lines.insert(-1, f"Sortino Ratio: {metrics.sortino_ratio:.3f}")
        if metrics.profit_factor:
            lines.insert(-1, f"Profit Factor: {metrics.profit_factor:.3f}")
            
        return "\n".join(lines)
        
    def _generate_html_report(self, metrics: PerformanceMetrics) -> str:
        """Generate HTML report."""
        html = f"""
        <html>
        <head><title>Trading Report</title></head>
        <body>
        <h1>Trading Performance Report</h1>
        <table border="1">
        <tr><td>Total Trades</td><td>{metrics.total_trades}</td></tr>
        <tr><td>Win Rate</td><td>{metrics.win_rate:.2%}</td></tr>
        <tr><td>Total Profit</td><td>${metrics.total_profit:.2f}</td></tr>
        <tr><td>Max Drawdown</td><td>{metrics.max_drawdown:.2%}</td></tr>
        </table>
        </body>
        </html>
        """
        return html
        
    @staticmethod
    def _calculate_max_drawdown(trades: List[Dict]) -> float:
        """Calculate maximum drawdown."""
        # TODO: Implement proper drawdown calculation
        return 0.0
        
    @staticmethod
    def _calculate_sharpe_ratio(trades: List[Dict]) -> Optional[float]:
        """Calculate Sharpe ratio."""
        # TODO: Implement Sharpe ratio calculation
        return None
        
    @staticmethod
    def _calculate_profit_factor(trades: List[Dict]) -> Optional[float]:
        """Calculate profit factor (gross profit / gross loss)."""
        if not trades:
            return None
        gains = sum(t.get("profit", 0) for t in trades if t.get("profit", 0) > 0)
        losses = abs(sum(t.get("profit", 0) for t in trades if t.get("profit", 0) < 0))
        return gains / losses if losses > 0 else None

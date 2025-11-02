"""
Report Generator: Performance metrics and analysis.

Generates:
  - JSON/CSV export with all metrics
  - HTML reports with charts (equity curve, drawdown, trades)
  - Daily/weekly P&L snapshots
  - Risk metrics summary
  - Trade-by-trade analysis

Usage:
  from yunmin.reporting.report_generator import ReportGenerator
  
  generator = ReportGenerator(
      output_dir="./reports",
      template_dir="./templates"
  )
  
  # From backtest result
  report = generator.generate_from_backtest(backtest_result)
  
  # From live trading stats
  report = generator.generate_from_live(daily_stats, equity_curve, trades)
  
  print(f"Report saved to {report.html_path}")
"""

import logging
import json
import csv
from typing import Dict, List
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import statistics

logger = logging.getLogger(__name__)


@dataclass
class ReportMetrics:
    """Summary metrics for report."""
    # Capital
    initial_capital: float
    final_capital: float
    pnl: float
    pnl_pct: float
    
    # Risk
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Trades
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    
    # Efficiency
    avg_trade_duration: str
    avg_win: float
    avg_loss: float
    best_trade: float
    worst_trade: float
    
    # Costs
    total_commission: float
    commission_pct: float
    
    # Daily stats
    avg_daily_pnl: float
    best_day: float
    worst_day: float


class ReportGenerator:
    """Generate performance reports."""
    
    def __init__(self, output_dir: str = "./reports"):
        """
        Initialize ReportGenerator.
        
        Args:
            output_dir: Directory for saving reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ReportGenerator initialized: output_dir={output_dir}")
    
    def generate_from_backtest(self, backtest_result) -> Dict:
        """
        Generate report from backtest result.
        
        Args:
            backtest_result: BacktestResult object
            
        Returns:
            Dict with report paths
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Build metrics
        metrics = ReportMetrics(
            initial_capital=backtest_result.initial_capital,
            final_capital=backtest_result.final_capital,
            pnl=backtest_result.final_pnl,
            pnl_pct=backtest_result.final_pnl_pct,
            max_drawdown=backtest_result.max_drawdown,
            max_drawdown_pct=backtest_result.max_drawdown_pct,
            sharpe_ratio=backtest_result.sharpe_ratio,
            sortino_ratio=backtest_result.sortino_ratio,
            calmar_ratio=backtest_result.calmar_ratio,
            total_trades=backtest_result.total_trades,
            winning_trades=backtest_result.winning_trades,
            losing_trades=backtest_result.losing_trades,
            win_rate=backtest_result.win_rate,
            profit_factor=backtest_result.profit_factor,
            avg_trade_duration="N/A",
            avg_win=backtest_result.avg_win,
            avg_loss=backtest_result.avg_loss,
            best_trade=max([t.pnl for t in backtest_result.trades]) if backtest_result.trades else 0,
            worst_trade=min([t.pnl for t in backtest_result.trades]) if backtest_result.trades else 0,
            total_commission=backtest_result.total_commission,
            commission_pct=backtest_result.commission_pct,
            avg_daily_pnl=0,
            best_day=0,
            worst_day=0
        )
        
        # Export formats
        json_path = self._export_json(metrics, timestamp)
        csv_path = self._export_trades_csv(backtest_result.trades, timestamp)
        html_path = self._generate_html(metrics, backtest_result, timestamp)
        
        logger.info(
            f"Report generated: JSON={json_path}, CSV={csv_path}, HTML={html_path}"
        )
        
        return {
            "json": str(json_path),
            "csv": str(csv_path),
            "html": str(html_path),
            "metrics": asdict(metrics)
        }
    
    def _export_json(self, metrics: ReportMetrics, timestamp: str) -> Path:
        """Export metrics to JSON."""
        path = self.output_dir / f"metrics_{timestamp}.json"
        
        data = {
            "timestamp": timestamp,
            "generated_at": datetime.now().isoformat(),
            "metrics": asdict(metrics)
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Metrics exported to {path}")
        return path
    
    def _export_trades_csv(self, trades, timestamp: str) -> Path:
        """Export trade-by-trade analysis to CSV."""
        if not trades:
            logger.warning("No trades to export")
            return self.output_dir / f"trades_{timestamp}.csv"
        
        path = self.output_dir / f"trades_{timestamp}.csv"
        
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "symbol", "entry_time", "entry_price", "exit_time", "exit_price",
                "qty", "side", "pnl", "pnl_pct", "commission"
            ])
            writer.writeheader()
            
            for trade in trades:
                writer.writerow({
                    "symbol": trade.symbol,
                    "entry_time": datetime.fromtimestamp(trade.entry_time / 1000).isoformat(),
                    "entry_price": f"{trade.entry_price:.2f}",
                    "exit_time": datetime.fromtimestamp(trade.exit_time / 1000).isoformat(),
                    "exit_price": f"{trade.exit_price:.2f}",
                    "qty": f"{trade.qty:.8f}",
                    "side": trade.side,
                    "pnl": f"{trade.pnl:.2f}",
                    "pnl_pct": f"{trade.pnl_pct:.2f}%",
                    "commission": f"{trade.commission:.2f}"
                })
        
        logger.info(f"Trades exported to {path}")
        return path
    
    def _generate_html(self, metrics: ReportMetrics, backtest_result, timestamp: str) -> Path:
        """Generate HTML report with summary."""
        path = self.output_dir / f"report_{timestamp}.html"
        
        # Simple HTML report (without external charting library)
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Trading Report {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: #f9f9f9; border-left: 4px solid #007bff; padding: 15px; border-radius: 4px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #007bff; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f9f9f9; }}
        .section {{ margin-top: 30px; }}
        .alert {{ padding: 15px; margin: 10px 0; border-radius: 4px; }}
        .alert-warning {{ background: #fff3cd; border-left: 4px solid #ffc107; }}
        .alert-info {{ background: #d1ecf1; border-left: 4px solid #17a2b8; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Trading Performance Report</h1>
        <p>Generated: {datetime.now().isoformat()}</p>
        
        <div class="section">
            <h2>Capital Summary</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Initial Capital</div>
                    <div class="metric-value">${metrics.initial_capital:,.2f}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Final Capital</div>
                    <div class="metric-value">${metrics.final_capital:,.2f}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Total P&L</div>
                    <div class="metric-value {'positive' if metrics.pnl >= 0 else 'negative'}">${metrics.pnl:,.2f} ({metrics.pnl_pct:.1f}%)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Total Commission</div>
                    <div class="metric-value">${metrics.total_commission:,.2f} ({metrics.commission_pct:.1f}%)</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Risk Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Max Drawdown</div>
                    <div class="metric-value negative">{metrics.max_drawdown_pct:.1f}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Sharpe Ratio</div>
                    <div class="metric-value">{metrics.sharpe_ratio:.2f}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Sortino Ratio</div>
                    <div class="metric-value">{metrics.sortino_ratio:.2f}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Calmar Ratio</div>
                    <div class="metric-value">{metrics.calmar_ratio:.2f}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Trade Statistics</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Total Trades</div>
                    <div class="metric-value">{metrics.total_trades}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value {'positive' if metrics.win_rate >= 50 else 'negative'}">{metrics.win_rate:.1f}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Profit Factor</div>
                    <div class="metric-value">{metrics.profit_factor:.2f}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Avg Win / Loss</div>
                    <div class="metric-value">${metrics.avg_win:.2f} / ${metrics.avg_loss:.2f}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Trade Details</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Winning Trades</td>
                    <td class="positive">{metrics.winning_trades}</td>
                </tr>
                <tr>
                    <td>Losing Trades</td>
                    <td class="negative">{metrics.losing_trades}</td>
                </tr>
                <tr>
                    <td>Best Trade</td>
                    <td class="positive">${metrics.best_trade:.2f}</td>
                </tr>
                <tr>
                    <td>Worst Trade</td>
                    <td class="negative">${metrics.worst_trade:.2f}</td>
                </tr>
            </table>
        </div>
        
        <div class="section alert alert-info">
            <strong>Note:</strong> This report was auto-generated. Verify all metrics independently.
        </div>
    </div>
</body>
</html>
        """
        
        with open(path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {path}")
        return path
    
    def generate_daily_summary(
        self,
        daily_stats: Dict,
        timestamp: str
    ) -> Path:
        """
        Generate daily P&L summary.
        
        Args:
            daily_stats: Dict with daily P&L/DD data
            timestamp: Report timestamp
            
        Returns:
            Path to generated CSV
        """
        path = self.output_dir / f"daily_summary_{timestamp}.csv"
        
        if not daily_stats:
            logger.warning("No daily stats to export")
            return path
        
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "date", "trades", "pnl", "dd", "balance", "win_rate"
            ])
            writer.writeheader()
            
            for date, stats in daily_stats.items():
                writer.writerow({
                    "date": date,
                    "trades": stats.get("trades_count", 0),
                    "pnl": f"{stats.get('net_pnl', 0):.2f}",
                    "dd": f"{stats.get('drawdown', 0):.2f}%",
                    "balance": f"{stats.get('balance', 0):.2f}",
                    "win_rate": f"{stats.get('win_rate', 0):.1f}%"
                })
        
        logger.info(f"Daily summary exported: {path}")
        return path
    
    def generate_risk_report(
        self,
        risk_violations: List[Dict],
        timestamp: str
    ) -> Path:
        """
        Generate risk violations report.
        
        Args:
            risk_violations: List of violation dicts
            timestamp: Report timestamp
            
        Returns:
            Path to generated CSV
        """
        path = self.output_dir / f"risk_violations_{timestamp}.csv"
        
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp", "violation_type", "severity", "details"
            ])
            writer.writeheader()
            
            for violation in risk_violations:
                writer.writerow({
                    "timestamp": violation.get("timestamp", datetime.now().isoformat()),
                    "violation_type": violation.get("type", "unknown"),
                    "severity": violation.get("severity", "warning"),
                    "details": violation.get("message", "")
                })
        
        logger.info(f"Risk report exported: {path}")
        return path


class ReportAggregator:
    """Aggregate multiple reports into summary."""
    
    @staticmethod
    def merge_reports(report_paths: List[str]) -> Dict:
        """
        Merge multiple report JSONs.
        
        Args:
            report_paths: List of JSON report paths
            
        Returns:
            Aggregated metrics dict
        """
        all_metrics = []
        
        for path in report_paths:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    all_metrics.append(data.get("metrics", {}))
            except Exception as e:
                logger.error(f"Failed to load report {path}: {e}")
        
        if not all_metrics:
            return {}
        
        # Aggregate
        avg_sharpe = statistics.mean([m.get("sharpe_ratio", 0) for m in all_metrics])
        avg_dd = statistics.mean([m.get("max_drawdown_pct", 0) for m in all_metrics])
        avg_pnl_pct = statistics.mean([m.get("pnl_pct", 0) for m in all_metrics])
        total_commission = sum([m.get("total_commission", 0) for m in all_metrics])
        
        return {
            "num_reports": len(all_metrics),
            "avg_sharpe": avg_sharpe,
            "avg_max_dd": avg_dd,
            "avg_pnl_pct": avg_pnl_pct,
            "total_commission": total_commission
        }

"""
Report Generator - генерация отчётов по результатам backtesting
"""

from typing import Dict
from datetime import datetime


class ReportGenerator:
    """Генератор отчётов о результатах backtesting"""
    
    @staticmethod
    def generate_text_report(results: Dict, strategy_name: str = "Strategy") -> str:
        """
        Генерация текстового отчёта.
        
        Args:
            results: Результаты backtesting
            strategy_name: Название стратегии
            
        Returns:
            Текстовый отчёт
        """
        report = []
        report.append("=" * 80)
        report.append(f"BACKTEST REPORT: {strategy_name}")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Performance Summary
        report.append("PERFORMANCE SUMMARY")
        report.append("-" * 80)
        report.append(f"Total Return:        {results.get('total_return', 0.0):>12.2f}%")
        report.append(f"Net P&L:            ${results.get('net_pnl', 0.0):>12,.2f}")
        report.append(f"Total Fees:         ${results.get('total_fees', 0.0):>12,.2f}")
        report.append(f"Final Equity:       ${results.get('final_equity', 0.0):>12,.2f}")
        report.append("")
        
        # Trade Statistics
        report.append("TRADE STATISTICS")
        report.append("-" * 80)
        report.append(f"Total Trades:        {results.get('total_trades', 0):>12}")
        report.append(f"Winning Trades:      {results.get('winning_trades', 0):>12}")
        report.append(f"Losing Trades:       {results.get('losing_trades', 0):>12}")
        report.append(f"Win Rate:            {results.get('win_rate', 0.0):>11.2f}%")
        report.append(f"Average Win:        ${results.get('avg_win', 0.0):>12,.2f}")
        report.append(f"Average Loss:       ${results.get('avg_loss', 0.0):>12,.2f}")
        report.append(f"Best Trade:         ${results.get('best_trade', 0.0):>12,.2f}")
        report.append(f"Worst Trade:        ${results.get('worst_trade', 0.0):>12,.2f}")
        report.append(f"Avg Trade:          ${results.get('avg_trade', 0.0):>12,.2f}")
        report.append(f"Avg Duration:        {results.get('avg_duration_hours', 0.0):>11.1f}h")
        report.append("")
        
        # Risk Metrics
        report.append("RISK METRICS")
        report.append("-" * 80)
        pf = results.get('profit_factor', 0.0)
        pf_str = f"{pf:.2f}" if pf != float('inf') else "INF"
        report.append(f"Profit Factor:       {pf_str:>12}")
        report.append(f"Sharpe Ratio:        {results.get('sharpe_ratio', 0.0):>12.2f}")
        report.append(f"Max Drawdown:       ${results.get('max_drawdown', 0.0):>12,.2f}")
        report.append(f"Max Drawdown %:      {results.get('max_drawdown_pct', 0.0):>11.2f}%")
        report.append(f"Recovery Factor:     {results.get('recovery_factor', 0.0):>12.2f}")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    @staticmethod
    def save_report(report: str, filename: str = "backtest_report.txt"):
        """
        Сохранить отчёт в файл.
        
        Args:
            report: Текст отчёта
            filename: Имя файла
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)

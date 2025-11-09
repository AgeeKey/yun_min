"""
Performance Tracker - отслеживание производительности торговой стратегии.
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class TradeRecord:
    """Запись о сделке"""
    timestamp: datetime
    pnl: float
    confidence: float
    duration: int
    
    @property
    def is_profitable(self) -> bool:
        return self.pnl > 0


class PerformanceTracker:
    """
    Отслеживает и анализирует производительность торговой стратегии.
    
    Метрики:
    - Total PnL
    - Win rate
    - Average confidence
    - Sharpe ratio (упрощенный)
    - Max drawdown
    """
    
    def __init__(self):
        """Инициализация трекера"""
        self.trades: List[TradeRecord] = []
        logger.info("📊 Performance Tracker initialized")
    
    def record_trade(
        self,
        pnl: float,
        confidence: float,
        duration: int,
        timestamp: datetime = None
    ):
        """
        Записывает результат сделки.
        
        Args:
            pnl: Profit/Loss
            confidence: Уверенность модели (0-1)
            duration: Длительность сделки в секундах
            timestamp: Время сделки (опционально)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        trade = TradeRecord(
            timestamp=timestamp,
            pnl=pnl,
            confidence=confidence,
            duration=duration
        )
        
        self.trades.append(trade)
        logger.debug(f"Trade recorded: PnL={pnl:.2f}, confidence={confidence:.2f}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Возвращает метрики производительности.
        
        Returns:
            Dict с метриками
        """
        if not self.trades:
            return {
                'total_pnl': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_confidence': 0.0,
                'avg_duration': 0.0
            }
        
        total_pnl = sum(t.pnl for t in self.trades)
        winning_trades = [t for t in self.trades if t.is_profitable]
        win_rate = len(winning_trades) / len(self.trades)
        avg_confidence = sum(t.confidence for t in self.trades) / len(self.trades)
        avg_duration = sum(t.duration for t in self.trades) / len(self.trades)
        
        return {
            'total_pnl': total_pnl,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'winning_trades': len(winning_trades),
            'losing_trades': len(self.trades) - len(winning_trades),
            'avg_confidence': avg_confidence,
            'avg_duration': avg_duration,
            'best_trade': max(self.trades, key=lambda t: t.pnl).pnl if self.trades else 0.0,
            'worst_trade': min(self.trades, key=lambda t: t.pnl).pnl if self.trades else 0.0
        }
    
    def get_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """
        Вычисляет упрощенный Sharpe ratio.
        
        Args:
            risk_free_rate: Безрисковая ставка
            
        Returns:
            Sharpe ratio
        """
        if len(self.trades) < 2:
            return 0.0
        
        returns = [t.pnl for t in self.trades]
        avg_return = sum(returns) / len(returns)
        
        # Стандартное отклонение
        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        return (avg_return - risk_free_rate) / std_dev
    
    def get_max_drawdown(self) -> float:
        """
        Вычисляет максимальную просадку.
        
        Returns:
            Max drawdown в процентах
        """
        if not self.trades:
            return 0.0
        
        cumulative_pnl = 0.0
        peak = 0.0
        max_dd = 0.0
        
        for trade in self.trades:
            cumulative_pnl += trade.pnl
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            
            drawdown = (peak - cumulative_pnl) / max(peak, 1.0)
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd * 100  # В процентах
    
    def get_report(self) -> str:
        """
        Генерирует текстовый отчет.
        
        Returns:
            Отформатированный отчет
        """
        metrics = self.get_metrics()
        sharpe = self.get_sharpe_ratio()
        max_dd = self.get_max_drawdown()
        
        report = f"""
Performance Report
{'='*50}
Total Trades:     {metrics['total_trades']}
Total PnL:        ${metrics['total_pnl']:.2f}
Win Rate:         {metrics['win_rate']:.1%}
Avg Confidence:   {metrics['avg_confidence']:.2f}
Avg Duration:     {metrics['avg_duration']:.0f}s
Sharpe Ratio:     {sharpe:.2f}
Max Drawdown:     {max_dd:.2f}%
Best Trade:       ${metrics['best_trade']:.2f}
Worst Trade:      ${metrics['worst_trade']:.2f}
{'='*50}
        """
        
        return report.strip()


if __name__ == "__main__":
    # Быстрый тест
    tracker = PerformanceTracker()
    
    # Симулируем сделки
    tracker.record_trade(pnl=100.0, confidence=0.8, duration=60)
    tracker.record_trade(pnl=-50.0, confidence=0.7, duration=30)
    tracker.record_trade(pnl=150.0, confidence=0.85, duration=120)
    tracker.record_trade(pnl=75.0, confidence=0.75, duration=90)
    
    print(tracker.get_report())

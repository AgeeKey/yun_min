"""
P&L Tracker - отслеживание прибыли и убытков
Формулы:
- LONG: P&L = (exit_price - entry_price) * amount - fees
- SHORT: P&L = (entry_price - exit_price) * amount - fees
- Unrealized: текущая цена вместо exit_price
- Win Rate: (выигрышных сделок / всего сделок) * 100
"""

from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Trade:
    """Закрытая сделка"""
    symbol: str
    side: str  # 'LONG' или 'SHORT'
    entry_price: float
    exit_price: float
    amount: float
    entry_fee: float
    exit_fee: float
    pnl: float  # Чистая прибыль/убыток
    pnl_pct: float  # P&L в процентах
    opened_at: datetime
    closed_at: datetime
    
    def __post_init__(self):
        """Автоматический расчет P&L если не указан"""
        if self.pnl == 0:
            if self.side == 'LONG':
                gross_pnl = (self.exit_price - self.entry_price) * self.amount
            else:  # SHORT
                gross_pnl = (self.entry_price - self.exit_price) * self.amount
            
            self.pnl = gross_pnl - self.entry_fee - self.exit_fee
            
            if self.entry_price > 0:
                self.pnl_pct = (self.pnl / (self.entry_price * self.amount)) * 100


class PnLTracker:
    """
    Трекер прибыли и убытков
    
    Отслеживает:
    - Realized P&L (закрытые позиции)
    - Unrealized P&L (открытые позиции)
    - Win Rate (процент прибыльных сделок)
    - Общие комиссии
    - История сделок
    """
    
    def __init__(self):
        self.trades: List[Trade] = []  # История закрытых сделок
        self.open_positions: Dict[str, dict] = {}  # Открытые позиции {symbol: {side, entry, amount, fees}}
        
        # Аккумулированная статистика
        self.total_realized_pnl: float = 0.0
        self.total_unrealized_pnl: float = 0.0
        self.total_fees: float = 0.0
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
    
    def open_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        amount: float,
        entry_fee: float = 0.0,
        opened_at: Optional[datetime] = None
    ):
        """
        Зарегистрировать открытие позиции
        
        Args:
            symbol: Торговая пара (BTC/USDT)
            side: LONG или SHORT
            entry_price: Цена входа
            amount: Размер позиции
            entry_fee: Комиссия за открытие
            opened_at: Время открытия (default: сейчас)
        """
        self.open_positions[symbol] = {
            'side': side,
            'entry_price': entry_price,
            'amount': amount,
            'entry_fee': entry_fee,
            'opened_at': opened_at or datetime.now()
        }
        
        self.total_fees += entry_fee
    
    def close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_fee: float = 0.0,
        closed_at: Optional[datetime] = None
    ) -> Optional[Trade]:
        """
        Закрыть позицию и записать сделку
        
        Args:
            symbol: Торговая пара
            exit_price: Цена выхода
            exit_fee: Комиссия за закрытие
            closed_at: Время закрытия (default: сейчас)
        
        Returns:
            Trade объект или None если позиция не найдена
        """
        if symbol not in self.open_positions:
            return None
        
        pos = self.open_positions.pop(symbol)
        
        # Создать сделку
        trade = Trade(
            symbol=symbol,
            side=pos['side'],
            entry_price=pos['entry_price'],
            exit_price=exit_price,
            amount=pos['amount'],
            entry_fee=pos['entry_fee'],
            exit_fee=exit_fee,
            pnl=0,  # Будет рассчитан автоматически
            pnl_pct=0,  # Будет рассчитан автоматически
            opened_at=pos['opened_at'],
            closed_at=closed_at or datetime.now()
        )
        
        # Добавить в историю
        self.trades.append(trade)
        
        # Обновить статистику
        self.total_fees += exit_fee
        self.total_realized_pnl += trade.pnl
        self.total_trades += 1
        
        if trade.pnl > 0:
            self.winning_trades += 1
        elif trade.pnl < 0:
            self.losing_trades += 1
        
        return trade
    
    def calculate_unrealized_pnl(
        self,
        symbol: str,
        current_price: float
    ) -> Optional[float]:
        """
        Рассчитать unrealized P&L для открытой позиции
        
        Args:
            symbol: Торговая пара
            current_price: Текущая цена
        
        Returns:
            Unrealized P&L или None если позиция не найдена
        """
        if symbol not in self.open_positions:
            return None
        
        pos = self.open_positions[symbol]
        
        if pos['side'] == 'LONG':
            gross_pnl = (current_price - pos['entry_price']) * pos['amount']
        else:  # SHORT
            gross_pnl = (pos['entry_price'] - current_price) * pos['amount']
        
        # Вычитаем только входную комиссию (выходная будет при закрытии)
        return gross_pnl - pos['entry_fee']
    
    def update_unrealized_pnl(self, prices: Dict[str, float]):
        """
        Обновить общий unrealized P&L для всех открытых позиций
        
        Args:
            prices: Словарь {symbol: current_price}
        """
        total = 0.0
        
        for symbol in self.open_positions:
            if symbol in prices:
                pnl = self.calculate_unrealized_pnl(symbol, prices[symbol])
                if pnl is not None:
                    total += pnl
        
        self.total_unrealized_pnl = total
    
    def get_win_rate(self) -> float:
        """
        Рассчитать процент выигрышных сделок
        
        Returns:
            Win Rate в процентах (0-100)
        """
        if self.total_trades == 0:
            return 0.0
        
        return (self.winning_trades / self.total_trades) * 100
    
    def get_summary(self) -> dict:
        """
        Получить полную сводку по P&L
        
        Returns:
            Словарь с ключевыми метриками
        """
        return {
            'total_realized_pnl': round(self.total_realized_pnl, 2),
            'total_unrealized_pnl': round(self.total_unrealized_pnl, 2),
            'total_pnl': round(self.total_realized_pnl + self.total_unrealized_pnl, 2),
            'total_fees': round(self.total_fees, 2),
            'net_pnl': round(self.total_realized_pnl + self.total_unrealized_pnl - self.total_fees, 2),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.get_win_rate(), 2),
            'open_positions': len(self.open_positions),
            'avg_win': round(self._get_avg_win(), 2),
            'avg_loss': round(self._get_avg_loss(), 2),
            'profit_factor': round(self._get_profit_factor(), 2)
        }
    
    def get_recent_trades(self, limit: int = 10) -> List[Trade]:
        """
        Получить последние N сделок
        
        Args:
            limit: Количество сделок
        
        Returns:
            Список последних сделок
        """
        return self.trades[-limit:]
    
    @property
    def closed_positions(self) -> List[Trade]:
        """
        Получить список всех закрытых позиций (сделок)
        
        Returns:
            Список всех Trade объектов
        """
        return self.trades
    
    def _get_avg_win(self) -> float:
        """Средняя прибыль на выигрышную сделку"""
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        return sum(wins) / len(wins) if wins else 0.0
    
    def _get_avg_loss(self) -> float:
        """Средний убыток на проигрышную сделку"""
        losses = [abs(t.pnl) for t in self.trades if t.pnl < 0]
        return sum(losses) / len(losses) if losses else 0.0
    
    def _get_profit_factor(self) -> float:
        """
        Profit Factor = Общая прибыль / Общий убыток
        Хорошо: > 2.0
        """
        total_wins = sum(t.pnl for t in self.trades if t.pnl > 0)
        total_losses = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        
        if total_losses == 0:
            return float('inf') if total_wins > 0 else 0.0
        
        return total_wins / total_losses
    
    def print_summary(self):
        """Вывести красивую сводку в консоль"""
        summary = self.get_summary()
        
        print("\n" + "=" * 80)
        print("📊 P&L СВОДКА")
        print("=" * 80)
        
        print(f"\n💰 ПРИБЫЛЬ/УБЫТОК:")
        print(f"   Realized P&L:   ${summary['total_realized_pnl']:+,.2f}")
        print(f"   Unrealized P&L: ${summary['total_unrealized_pnl']:+,.2f}")
        print(f"   Общий P&L:      ${summary['total_pnl']:+,.2f}")
        print(f"   Комиссии:       ${summary['total_fees']:,.2f}")
        print(f"   Чистый P&L:     ${summary['net_pnl']:+,.2f}")
        
        print(f"\n📈 СТАТИСТИКА СДЕЛОК:")
        print(f"   Всего сделок:     {summary['total_trades']}")
        print(f"   Прибыльных:       {summary['winning_trades']} ✅")
        print(f"   Убыточных:        {summary['losing_trades']} ❌")
        print(f"   Win Rate:         {summary['win_rate']:.1f}%")
        print(f"   Открытых позиций: {summary['open_positions']}")
        
        print(f"\n🎯 КАЧЕСТВО СДЕЛОК:")
        print(f"   Средняя прибыль:  ${summary['avg_win']:+,.2f}")
        print(f"   Средний убыток:   ${summary['avg_loss']:,.2f}")
        print(f"   Profit Factor:    {summary['profit_factor']:.2f}")
        
        if summary['profit_factor'] >= 2.0:
            print(f"   ✅ Отличный Profit Factor!")
        elif summary['profit_factor'] >= 1.5:
            print(f"   ⚠️ Хороший Profit Factor")
        else:
            print(f"   ❌ Низкий Profit Factor - нужна оптимизация")
        
        print("=" * 80)

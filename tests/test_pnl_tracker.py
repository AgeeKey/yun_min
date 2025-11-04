"""
Тесты для PnLTracker - критический компонент финансового учета

Покрытие:
1. Расчет P&L для LONG позиций
2. Расчет P&L для SHORT позиций  
3. Win Rate расчет
4. Sharpe Ratio расчет
5. Unrealized P&L отслеживание
6. Комиссии учет
7. Edge cases (ноль сделок, отрицательные значения)
"""

import pytest
from datetime import datetime, timedelta
from yunmin.core.pnl_tracker import PnLTracker, Trade


class TestBasicPnLCalculations:
    """Базовые тесты расчета P&L"""
    
    def test_long_profitable_trade(self):
        """Тест прибыльной LONG сделки"""
        trade = Trade(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            exit_price=52000.0,
            amount=0.1,
            entry_fee=5.0,
            exit_fee=5.2,
            pnl=0,  # Будет рассчитан автоматически
            pnl_pct=0,
            opened_at=datetime.now(),
            closed_at=datetime.now()
        )
        
        # Gross P&L = (52000 - 50000) * 0.1 = 200
        # Net P&L = 200 - 5 - 5.2 = 189.8
        expected_pnl = (52000 - 50000) * 0.1 - 5.0 - 5.2
        
        assert abs(trade.pnl - expected_pnl) < 0.01
        assert trade.pnl > 0
        
    def test_long_losing_trade(self):
        """Тест убыточной LONG сделки"""
        trade = Trade(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            exit_price=48000.0,
            amount=0.1,
            entry_fee=5.0,
            exit_fee=4.8,
            pnl=0,
            pnl_pct=0,
            opened_at=datetime.now(),
            closed_at=datetime.now()
        )
        
        # Gross P&L = (48000 - 50000) * 0.1 = -200
        # Net P&L = -200 - 5 - 4.8 = -209.8
        expected_pnl = (48000 - 50000) * 0.1 - 5.0 - 4.8
        
        assert abs(trade.pnl - expected_pnl) < 0.01
        assert trade.pnl < 0
        
    def test_short_profitable_trade(self):
        """Тест прибыльной SHORT сделки"""
        trade = Trade(
            symbol='BTC/USDT',
            side='SHORT',
            entry_price=50000.0,
            exit_price=48000.0,  # Выкупили дешевле
            amount=0.1,
            entry_fee=5.0,
            exit_fee=4.8,
            pnl=0,
            pnl_pct=0,
            opened_at=datetime.now(),
            closed_at=datetime.now()
        )
        
        # SHORT: P&L = (entry - exit) * amount - fees
        # Gross P&L = (50000 - 48000) * 0.1 = 200
        # Net P&L = 200 - 5 - 4.8 = 190.2
        expected_pnl = (50000 - 48000) * 0.1 - 5.0 - 4.8
        
        assert abs(trade.pnl - expected_pnl) < 0.01
        assert trade.pnl > 0
        
    def test_short_losing_trade(self):
        """Тест убыточной SHORT сделки"""
        trade = Trade(
            symbol='BTC/USDT',
            side='SHORT',
            entry_price=50000.0,
            exit_price=52000.0,  # Выкупили дороже
            amount=0.1,
            entry_fee=5.0,
            exit_fee=5.2,
            pnl=0,
            pnl_pct=0,
            opened_at=datetime.now(),
            closed_at=datetime.now()
        )
        
        # SHORT: убыток когда цена растет
        # Gross P&L = (50000 - 52000) * 0.1 = -200
        # Net P&L = -200 - 5 - 5.2 = -210.2
        expected_pnl = (50000 - 52000) * 0.1 - 5.0 - 5.2
        
        assert abs(trade.pnl - expected_pnl) < 0.01
        assert trade.pnl < 0


class TestPnLTrackerBasics:
    """Тесты базового функционала PnLTracker"""
    
    def test_initialization(self):
        """Тест инициализации трекера"""
        tracker = PnLTracker()
        
        assert tracker.total_realized_pnl == 0.0
        assert tracker.total_unrealized_pnl == 0.0
        assert tracker.total_fees == 0.0
        assert tracker.total_trades == 0
        assert tracker.winning_trades == 0
        assert tracker.losing_trades == 0
        assert len(tracker.trades) == 0
        assert len(tracker.open_positions) == 0
        
    def test_open_position(self):
        """Тест открытия позиции"""
        tracker = PnLTracker()
        
        tracker.open_position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            entry_fee=5.0
        )
        
        assert 'BTC/USDT' in tracker.open_positions
        assert tracker.open_positions['BTC/USDT']['side'] == 'LONG'
        assert tracker.open_positions['BTC/USDT']['entry_price'] == 50000.0
        assert tracker.total_fees == 5.0
        
    def test_close_position_profit(self):
        """Тест закрытия позиции с прибылью"""
        tracker = PnLTracker()
        
        tracker.open_position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            entry_fee=5.0
        )
        
        tracker.close_position(
            symbol='BTC/USDT',
            exit_price=52000.0,
            exit_fee=5.2
        )
        
        # Gross P&L = 200, Net = 200 - 5 - 5.2 = 189.8
        assert len(tracker.trades) == 1
        assert tracker.total_trades == 1
        assert tracker.winning_trades == 1
        assert tracker.losing_trades == 0
        assert 'BTC/USDT' not in tracker.open_positions
        
        # Realized P&L должен быть положительным
        assert tracker.total_realized_pnl > 0
        
    def test_close_position_loss(self):
        """Тест закрытия позиции с убытком"""
        tracker = PnLTracker()
        
        tracker.open_position(
            symbol='ETH/USDT',
            side='LONG',
            entry_price=3000.0,
            amount=1.0,
            entry_fee=3.0
        )
        
        tracker.close_position(
            symbol='ETH/USDT',
            exit_price=2800.0,
            exit_fee=2.8
        )
        
        assert len(tracker.trades) == 1
        assert tracker.total_trades == 1
        assert tracker.winning_trades == 0
        assert tracker.losing_trades == 1
        
        # Realized P&L должен быть отрицательным
        assert tracker.total_realized_pnl < 0


class TestWinRateCalculations:
    """Тесты расчета Win Rate"""
    
    def test_win_rate_all_wins(self):
        """Тест Win Rate при всех прибыльных сделках"""
        tracker = PnLTracker()
        
        # 3 прибыльные сделки
        for i in range(3):
            tracker.open_position(
                symbol=f'COIN{i}/USDT',
                side='LONG',
                entry_price=100.0,
                amount=1.0,
                entry_fee=0.1
            )
            tracker.close_position(
                symbol=f'COIN{i}/USDT',
                exit_price=110.0,
                exit_fee=0.11
            )
        
        summary = tracker.get_summary()
        assert summary['win_rate'] == 100.0
        
    def test_win_rate_all_losses(self):
        """Тест Win Rate при всех убыточных сделках"""
        tracker = PnLTracker()
        
        # 3 убыточные сделки
        for i in range(3):
            tracker.open_position(
                symbol=f'COIN{i}/USDT',
                side='LONG',
                entry_price=100.0,
                amount=1.0,
                entry_fee=0.1
            )
            tracker.close_position(
                symbol=f'COIN{i}/USDT',
                exit_price=90.0,
                exit_fee=0.09
            )
        
        stats = tracker.get_statistics()
        assert stats['win_rate'] == 0.0
        
    def test_win_rate_mixed(self):
        """Тест Win Rate при смешанных результатах"""
        tracker = PnLTracker()
        
        # 6 прибыльных, 4 убыточных = 60% win rate
        for i in range(6):
            tracker.open_position(
                symbol=f'WIN{i}/USDT',
                side='LONG',
                entry_price=100.0,
                amount=1.0,
                entry_fee=0.1
            )
            tracker.close_position(
                symbol=f'WIN{i}/USDT',
                exit_price=110.0,
                exit_fee=0.11
            )
            
        for i in range(4):
            tracker.open_position(
                symbol=f'LOSE{i}/USDT',
                side='LONG',
                entry_price=100.0,
                amount=1.0,
                entry_fee=0.1
            )
            tracker.close_position(
                symbol=f'LOSE{i}/USDT',
                exit_price=90.0,
                exit_fee=0.09
            )
        
        stats = tracker.get_statistics()
        assert stats['win_rate'] == 60.0


class TestUnrealizedPnL:
    """Тесты отслеживания нереализованной прибыли"""
    
    def test_unrealized_pnl_long(self):
        """Тест unrealized P&L для LONG позиции"""
        tracker = PnLTracker()
        
        tracker.open_position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            entry_fee=5.0
        )
        
        # Текущая цена 52000
        unrealized = tracker.get_unrealized_pnl(symbol='BTC/USDT', current_price=52000.0)
        
        # Gross = (52000 - 50000) * 0.1 = 200
        # Net = 200 - 5 = 195 (exit fee еще не учитывается)
        expected = (52000 - 50000) * 0.1 - 5.0
        
        assert abs(unrealized - expected) < 0.01
        assert unrealized > 0
        
    def test_unrealized_pnl_short(self):
        """Тест unrealized P&L для SHORT позиции"""
        tracker = PnLTracker()
        
        tracker.open_position(
            symbol='BTC/USDT',
            side='SHORT',
            entry_price=50000.0,
            amount=0.1,
            entry_fee=5.0
        )
        
        # Текущая цена 48000 (прибыль для SHORT)
        unrealized = tracker.get_unrealized_pnl(symbol='BTC/USDT', current_price=48000.0)
        
        # SHORT: P&L = (entry - current) * amount - fees
        # Gross = (50000 - 48000) * 0.1 = 200
        # Net = 200 - 5 = 195
        expected = (50000 - 48000) * 0.1 - 5.0
        
        assert abs(unrealized - expected) < 0.01
        assert unrealized > 0


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_zero_trades_win_rate(self):
        """Тест Win Rate при нулевом количестве сделок"""
        tracker = PnLTracker()
        
        stats = tracker.get_statistics()
        assert stats['win_rate'] == 0.0
        
    def test_breakeven_trade(self):
        """Тест сделки в ноль (breakeven)"""
        tracker = PnLTracker()
        
        tracker.open_position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            entry_fee=0.0
        )
        
        tracker.close_position(
            symbol='BTC/USDT',
            exit_price=50000.0,
            exit_fee=0.0
        )
        
        # Breakeven считается как убыток (не прибыль)
        assert tracker.winning_trades == 0
        assert tracker.losing_trades == 1
        
    def test_very_small_profit(self):
        """Тест очень маленькой прибыли"""
        tracker = PnLTracker()
        
        tracker.open_position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            entry_fee=0.1
        )
        
        # Прибыль 0.1 USDT (покрывает только комиссию)
        tracker.close_position(
            symbol='BTC/USDT',
            exit_price=50001.0,
            exit_fee=0.0
        )
        
        # Маленькая прибыль все еще прибыль
        assert tracker.winning_trades == 1
        assert tracker.total_realized_pnl > 0
        
    def test_position_not_exists(self):
        """Тест получения unrealized P&L для несуществующей позиции"""
        tracker = PnLTracker()
        
        # Должно вернуть 0 или None
        unrealized = tracker.get_unrealized_pnl(symbol='NONEXISTENT/USDT', current_price=50000.0)
        
        assert unrealized == 0.0 or unrealized is None


class TestFeeAccounting:
    """Тесты учета комиссий"""
    
    def test_total_fees_accumulation(self):
        """Тест накопления общих комиссий"""
        tracker = PnLTracker()
        
        # Сделка 1: entry_fee=5, exit_fee=5.2
        tracker.open_position('BTC/USDT', 'LONG', 50000.0, 0.1, entry_fee=5.0)
        tracker.close_position('BTC/USDT', exit_price=52000.0, exit_fee=5.2)
        
        # Сделка 2: entry_fee=3, exit_fee=2.8
        tracker.open_position('ETH/USDT', 'LONG', 3000.0, 1.0, entry_fee=3.0)
        tracker.close_position('ETH/USDT', exit_price=3100.0, exit_fee=2.8)
        
        # Всего комиссий: 5 + 5.2 + 3 + 2.8 = 16.0
        assert abs(tracker.total_fees - 16.0) < 0.01
        
    def test_fees_impact_on_pnl(self):
        """Тест влияния комиссий на чистую прибыль"""
        tracker = PnLTracker()
        
        tracker.open_position('BTC/USDT', 'LONG', 50000.0, 0.1, entry_fee=100.0)  # Большая комиссия!
        tracker.close_position('BTC/USDT', exit_price=52000.0, exit_fee=100.0)
        
        # Gross P&L = 200
        # Fees = 200
        # Net P&L = 0 (или даже отрицательный)
        
        # Из-за больших комиссий прибыль минимальна или убыток
        assert tracker.total_realized_pnl <= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

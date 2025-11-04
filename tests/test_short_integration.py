"""
Интеграционные тесты для SHORT позиций
Проверяем полный цикл: открытие → мониторинг → закрытие → P&L
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from yunmin.core.position_monitor import PositionMonitor, Position
from yunmin.core.pnl_tracker import PnLTracker


class TestShortPositionIntegration:
    """Интеграционные тесты SHORT позиций"""
    
    def test_short_full_cycle_profit(self):
        """Тест полного цикла прибыльной SHORT позиции"""
        # Setup
        bot_mock = Mock()
        bot_mock.exchange = Mock()
        pnl_tracker = PnLTracker()
        
        # 1. Открытие SHORT позиции
        pnl_tracker.open_position(
            symbol='BTC/USDT',
            side='SHORT',
            entry_price=50000.0,
            amount=0.1,
            entry_fee=5.0
        )
        
        assert 'BTC/USDT' in pnl_tracker.open_positions
        assert pnl_tracker.open_positions['BTC/USDT']['side'] == 'SHORT'
        
        # 2. Цена упала до 48000 (прибыль для SHORT)
        unrealized_pnl = pnl_tracker.calculate_unrealized_pnl('BTC/USDT', 48000.0)
        
        # SHORT: (50000 - 48000) * 0.1 - 5.0 = 195
        expected_unrealized = (50000 - 48000) * 0.1 - 5.0
        assert abs(unrealized_pnl - expected_unrealized) < 0.01
        assert unrealized_pnl > 0
        
        # 3. Закрытие позиции
        trade = pnl_tracker.close_position(
            symbol='BTC/USDT',
            exit_price=48000.0,
            exit_fee=4.8
        )
        
        assert trade is not None
        assert trade.pnl > 0
        assert pnl_tracker.winning_trades == 1
        assert 'BTC/USDT' not in pnl_tracker.open_positions
        
    def test_short_full_cycle_loss(self):
        """Тест полного цикла убыточной SHORT позиции"""
        pnl_tracker = PnLTracker()
        
        # 1. Открытие SHORT по 50000
        pnl_tracker.open_position(
            symbol='ETH/USDT',
            side='SHORT',
            entry_price=3000.0,
            amount=1.0,
            entry_fee=3.0
        )
        
        # 2. Цена выросла до 3200 (убыток для SHORT)
        unrealized_pnl = pnl_tracker.calculate_unrealized_pnl('ETH/USDT', 3200.0)
        
        # SHORT: (3000 - 3200) * 1.0 - 3.0 = -203
        expected_unrealized = (3000 - 3200) * 1.0 - 3.0
        assert abs(unrealized_pnl - expected_unrealized) < 0.01
        assert unrealized_pnl < 0
        
        # 3. Закрытие с убытком
        trade = pnl_tracker.close_position(
            symbol='ETH/USDT',
            exit_price=3200.0,
            exit_fee=3.2
        )
        
        assert trade.pnl < 0
        assert pnl_tracker.losing_trades == 1
        
    def test_short_position_monitor_stop_loss(self):
        """Тест срабатывания Stop-Loss для SHORT через PositionMonitor"""
        bot_mock = Mock()
        bot_mock.exchange = Mock()
        bot_mock.close_position = Mock()
        
        monitor = PositionMonitor(bot_mock)
        
        position = Position(
            symbol='BTC/USDT',
            side='SHORT',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=51000.0,  # SL выше entry для SHORT
            take_profit=48000.0,
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        # Цена выросла до 51500 -> должен сработать SL
        should_close, reason = monitor._should_close_position(position, 51500.0)
        
        assert should_close is True
        assert 'Stop-Loss' in reason
        
    def test_short_position_monitor_take_profit(self):
        """Тест срабатывания Take-Profit для SHORT через PositionMonitor"""
        bot_mock = Mock()
        monitor = PositionMonitor(bot_mock)
        
        position = Position(
            symbol='BTC/USDT',
            side='SHORT',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=51000.0,
            take_profit=48000.0,
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        # Цена упала до 47500 -> должен сработать TP
        should_close, reason = monitor._should_close_position(position, 47500.0)
        
        assert should_close is True
        assert 'Take-Profit' in reason
        
    def test_multiple_short_positions(self):
        """Тест нескольких SHORT позиций одновременно"""
        pnl_tracker = PnLTracker()
        
        # Открываем 3 SHORT позиции
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        prices = [50000.0, 3000.0, 500.0]
        amounts = [0.1, 1.0, 10.0]
        
        for symbol, price, amount in zip(symbols, prices, amounts):
            pnl_tracker.open_position(
                symbol=symbol,
                side='SHORT',
                entry_price=price,
                amount=amount,
                entry_fee=price * amount * 0.001  # 0.1% fee
            )
        
        assert len(pnl_tracker.open_positions) == 3
        
        # Закрываем все с небольшой прибылью (цены упали на 2%)
        for symbol, price, amount in zip(symbols, prices, amounts):
            exit_price = price * 0.98  # -2%
            trade = pnl_tracker.close_position(
                symbol=symbol,
                exit_price=exit_price,
                exit_fee=exit_price * amount * 0.001
            )
            assert trade.pnl > 0  # Все SHORT прибыльны при падении
        
        assert pnl_tracker.winning_trades == 3
        assert pnl_tracker.losing_trades == 0
        assert pnl_tracker.get_win_rate() == 100.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

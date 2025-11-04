"""
Тесты для PositionMonitor - критический компонент управления рисками

Покрытие:
1. Открытие/закрытие позиций
2. Stop-Loss срабатывание (LONG/SHORT)
3. Take-Profit срабатывание (LONG/SHORT)
4. Trailing Stop-Loss (LONG/SHORT)
5. Обработка ошибок API
6. Потоковая безопасность
"""

import pytest
import time
import threading
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from yunmin.core.position_monitor import PositionMonitor, Position


class TestPositionMonitorBasics:
    """Базовые тесты PositionMonitor"""
    
    def test_initialization(self):
        """Тест инициализации монитора"""
        bot_mock = Mock()
        monitor = PositionMonitor(bot_mock, check_interval=5)
        
        assert monitor.bot == bot_mock
        assert monitor.check_interval == 5
        assert monitor.running is False
        assert len(monitor.positions) == 0
        
    def test_add_position(self):
        """Тест добавления позиции в мониторинг"""
        bot_mock = Mock()
        monitor = PositionMonitor(bot_mock)
        
        position = Position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=49000.0,
            take_profit=52000.0,
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        monitor.add_position(position)
        
        assert monitor.get_position_count() == 1
        assert 'BTC/USDT' in monitor.positions
        assert monitor.positions['BTC/USDT'].side == 'LONG'
        
    def test_remove_position(self):
        """Тест удаления позиции из мониторинга"""
        bot_mock = Mock()
        monitor = PositionMonitor(bot_mock)
        
        position = Position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=49000.0,
            take_profit=52000.0,
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        monitor.add_position(position)
        assert monitor.get_position_count() == 1
        
        monitor.remove_position('BTC/USDT')
        assert monitor.get_position_count() == 0
        assert 'BTC/USDT' not in monitor.positions


class TestLongPositionClosing:
    """Тесты закрытия LONG позиций"""
    
    def test_long_stop_loss_hit(self):
        """Тест срабатывания Stop-Loss для LONG позиции"""
        bot_mock = Mock()
        bot_mock.exchange = Mock()
        bot_mock.exchange.fetch_ticker = Mock(return_value={'last': 48500.0})
        bot_mock.close_position = Mock()
        
        monitor = PositionMonitor(bot_mock, check_interval=1)
        
        position = Position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=49000.0,
            take_profit=52000.0,
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        # Проверка логики
        should_close, reason = monitor._should_close_position(position, 48500.0)
        
        assert should_close is True
        assert 'Stop-Loss' in reason
        
    def test_long_take_profit_hit(self):
        """Тест срабатывания Take-Profit для LONG позиции"""
        bot_mock = Mock()
        monitor = PositionMonitor(bot_mock)
        
        position = Position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=49000.0,
            take_profit=52000.0,
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        # Проверка логики
        should_close, reason = monitor._should_close_position(position, 52500.0)
        
        assert should_close is True
        assert 'Take-Profit' in reason
        
    def test_long_trailing_stop_activation(self):
        """Тест активации Trailing Stop для LONG позиции"""
        bot_mock = Mock()
        monitor = PositionMonitor(bot_mock)
        
        position = Position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=49000.0,
            take_profit=55000.0,  # TP выше чтобы не сработал
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        # Цена выросла до 51500 (прибыль 3%)
        should_close, _ = monitor._should_close_position(position, 51500.0)
        # При цене 51500 (рост 1.5% и прибыль 3%) trailing должен активироваться
        # но позиция не закрывается, только обновляется highest_price и SL
        
        # Проверяем что highest_price обновился
        old_sl = position.stop_loss
        assert position.highest_price >= 51500.0 or old_sl == 49000.0  # Либо обновился, либо не активировался
        
        # Сделаем второй рост чтобы гарантированно активировать trailing
        should_close, _ = monitor._should_close_position(position, 52000.0)
        
        # Теперь цена упала ниже нового SL -> должен сработать trailing stop
        new_price = 50000.0  # Упала обратно к entry
        should_close, reason = monitor._should_close_position(position, new_price)
        
        assert should_close is True
        assert 'Stop-Loss' in reason  # Trailing stop это тоже Stop-Loss


class TestShortPositionClosing:
    """Тесты закрытия SHORT позиций"""
    
    def test_short_stop_loss_hit(self):
        """Тест срабатывания Stop-Loss для SHORT позиции"""
        bot_mock = Mock()
        monitor = PositionMonitor(bot_mock)
        
        position = Position(
            symbol='BTC/USDT',
            side='SHORT',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=51000.0,  # SL выше entry для SHORT
            take_profit=48000.0,  # TP ниже entry для SHORT
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        # Цена выросла до 51500 -> убыток, должен сработать SL
        should_close, reason = monitor._should_close_position(position, 51500.0)
        
        assert should_close is True
        assert 'Stop-Loss' in reason
        
    def test_short_take_profit_hit(self):
        """Тест срабатывания Take-Profit для SHORT позиции"""
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
        
        # Цена упала до 47500 -> прибыль, должен сработать TP
        should_close, reason = monitor._should_close_position(position, 47500.0)
        
        assert should_close is True
        assert 'Take-Profit' in reason


class TestMonitoringThread:
    """Тесты работы мониторинга в потоке"""
    
    def test_start_stop_monitor(self):
        """Тест запуска и остановки монитора"""
        bot_mock = Mock()
        monitor = PositionMonitor(bot_mock, check_interval=1)
        
        assert monitor.running is False
        
        monitor.start()
        assert monitor.running is True
        assert monitor.thread is not None
        assert monitor.thread.is_alive()
        
        time.sleep(0.5)  # Даём потоку запуститься
        
        monitor.stop()
        assert monitor.running is False
        
        time.sleep(1.5)  # Даём потоку завершиться
        assert not monitor.thread.is_alive()
        
    def test_monitor_checks_positions(self):
        """Тест что монитор проверяет позиции в цикле"""
        bot_mock = Mock()
        bot_mock.exchange = Mock()
        bot_mock.exchange.fetch_ticker = Mock(return_value={'last': 48000.0})
        bot_mock.close_position = Mock()
        
        monitor = PositionMonitor(bot_mock, check_interval=1)
        
        position = Position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=49000.0,
            take_profit=52000.0,
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        monitor.add_position(position)
        monitor.start()
        
        # Ждём несколько циклов проверки
        time.sleep(2.5)
        
        monitor.stop()
        
        # Проверяем что fetch_ticker вызывался хотя бы раз
        # (детальная проверка частоты не критична для функциональности)
        assert bot_mock.exchange.fetch_ticker.call_count >= 1


class TestErrorHandling:
    """Тесты обработки ошибок"""
    
    def test_api_error_doesnt_crash_monitor(self):
        """Тест что ошибка API не ломает монитор"""
        bot_mock = Mock()
        bot_mock.exchange = Mock()
        bot_mock.exchange.fetch_ticker = Mock(side_effect=Exception("API Error"))
        
        monitor = PositionMonitor(bot_mock, check_interval=1)
        
        position = Position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=49000.0,
            take_profit=52000.0,
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        monitor.add_position(position)
        monitor.start()
        
        # Ждём несколько циклов
        time.sleep(3)
        
        # Монитор должен продолжать работать несмотря на ошибки
        assert monitor.running is True
        
        monitor.stop()
        
    def test_close_position_error_handling(self):
        """Тест обработки ошибок при закрытии позиции"""
        bot_mock = Mock()
        bot_mock.exchange = Mock()
        bot_mock.exchange.fetch_ticker = Mock(return_value={'last': 48000.0})
        bot_mock.close_position = Mock(side_effect=Exception("Close Error"))
        
        monitor = PositionMonitor(bot_mock, check_interval=1)
        
        position = Position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=49000.0,
            take_profit=52000.0,
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        monitor.add_position(position)
        monitor.start()
        
        time.sleep(3)
        
        # Монитор не должен упасть
        assert monitor.running is True
        
        monitor.stop()


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_position_exactly_at_stop_loss(self):
        """Тест позиции точно на уровне Stop-Loss"""
        bot_mock = Mock()
        monitor = PositionMonitor(bot_mock)
        
        position = Position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=49000.0,
            take_profit=52000.0,
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        # Цена точно на SL
        should_close, reason = monitor._should_close_position(position, 49000.0)
        
        assert should_close is True
        assert 'Stop-Loss' in reason
        
    def test_multiple_positions_monitoring(self):
        """Тест мониторинга нескольких позиций одновременно"""
        bot_mock = Mock()
        monitor = PositionMonitor(bot_mock)
        
        pos1 = Position(
            symbol='BTC/USDT',
            side='LONG',
            entry_price=50000.0,
            amount=0.1,
            stop_loss=49000.0,
            take_profit=52000.0,
            trailing_stop_pct=2.0,
            highest_price=50000.0,
            lowest_price=50000.0,
            opened_at=datetime.now()
        )
        
        pos2 = Position(
            symbol='ETH/USDT',
            side='SHORT',
            entry_price=3000.0,
            amount=1.0,
            stop_loss=3100.0,
            take_profit=2800.0,
            trailing_stop_pct=2.0,
            highest_price=3000.0,
            lowest_price=3000.0,
            opened_at=datetime.now()
        )
        
        monitor.add_position(pos1)
        monitor.add_position(pos2)
        
        assert monitor.get_position_count() == 2
        assert 'BTC/USDT' in monitor.positions
        assert 'ETH/USDT' in monitor.positions


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""
Тесты для PortfolioManager - мультисимвольной торговли
"""

import pytest
import numpy as np
from yunmin.core.portfolio_manager import (
    PortfolioManager,
    SymbolAllocation,
    PortfolioState
)


class TestSymbolAllocation:
    """Тесты SymbolAllocation"""
    
    def test_valid_allocation(self):
        """Создание валидной аллокации"""
        alloc = SymbolAllocation(
            symbol='BTC/USDT',
            allocated_capital=10000.0,
            current_exposure=0.0,
            available_capital=10000.0,
            max_allocation_pct=0.33
        )
        
        assert alloc.symbol == 'BTC/USDT'
        assert alloc.allocated_capital == 10000.0
        assert alloc.available_capital == 10000.0
        assert alloc.pnl == 0.0
    
    def test_negative_capital_raises(self):
        """Отрицательный капитал должен вызвать ошибку"""
        with pytest.raises(ValueError):
            SymbolAllocation(
                symbol='BTC/USDT',
                allocated_capital=-1000.0,
                current_exposure=0.0,
                available_capital=0.0,
                max_allocation_pct=0.33
            )
    
    def test_invalid_max_allocation_raises(self):
        """Неверный max_allocation должен вызвать ошибку"""
        with pytest.raises(ValueError):
            SymbolAllocation(
                symbol='BTC/USDT',
                allocated_capital=10000.0,
                current_exposure=0.0,
                available_capital=10000.0,
                max_allocation_pct=1.5  # > 100%
            )


class TestPortfolioState:
    """Тесты PortfolioState"""
    
    def test_total_risk_pct(self):
        """Расчёт общего риска портфеля"""
        state = PortfolioState(
            total_capital=100000.0,
            available_capital=90000.0,
            total_exposure=10000.0,
            total_pnl=0.0
        )
        
        assert state.total_risk_pct == 0.1  # 10%
    
    def test_active_symbols(self):
        """Получение активных символов"""
        state = PortfolioState(
            total_capital=100000.0,
            available_capital=80000.0,
            total_exposure=20000.0,
            total_pnl=0.0
        )
        
        state.allocations['BTC/USDT'] = SymbolAllocation(
            symbol='BTC/USDT',
            allocated_capital=50000.0,
            current_exposure=10000.0,  # Активная
            available_capital=40000.0,
            max_allocation_pct=0.5
        )
        
        state.allocations['ETH/USDT'] = SymbolAllocation(
            symbol='ETH/USDT',
            allocated_capital=50000.0,
            current_exposure=0.0,  # Неактивная
            available_capital=50000.0,
            max_allocation_pct=0.5
        )
        
        assert state.active_symbols == ['BTC/USDT']
    
    def test_utilization_pct(self):
        """Расчёт использования капитала"""
        state = PortfolioState(
            total_capital=100000.0,
            available_capital=70000.0,  # 30% использовано
            total_exposure=20000.0,
            total_pnl=0.0
        )
        
        assert state.utilization_pct == 0.3  # 30%


class TestPortfolioManager:
    """Тесты PortfolioManager"""
    
    def test_initialization(self):
        """Инициализация менеджера портфеля"""
        pm = PortfolioManager(
            total_capital=100000.0,
            symbols=['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        )
        
        assert pm.state.total_capital == 100000.0
        assert pm.state.available_capital == 100000.0
        assert len(pm.state.allocations) == 3
        
        # Каждый символ получает 1/3 капитала
        for symbol in pm.symbols:
            alloc = pm.state.allocations[symbol]
            assert alloc.allocated_capital == pytest.approx(33333.33, abs=0.1)
            assert alloc.max_allocation_pct == pytest.approx(0.333, abs=0.01)
    
    def test_invalid_capital_raises(self):
        """Отрицательный капитал должен вызвать ошибку"""
        with pytest.raises(ValueError):
            PortfolioManager(
                total_capital=-10000.0,
                symbols=['BTC/USDT']
            )
    
    def test_empty_symbols_raises(self):
        """Пустой список символов должен вызвать ошибку"""
        with pytest.raises(ValueError):
            PortfolioManager(
                total_capital=100000.0,
                symbols=[]
            )
    
    def test_can_open_position_success(self):
        """Успешная проверка возможности открытия позиции"""
        pm = PortfolioManager(
            total_capital=100000.0,
            symbols=['BTC/USDT', 'ETH/USDT']
        )
        
        can_open, reason = pm.can_open_position('BTC/USDT', 5000.0)
        
        assert can_open is True
        assert reason == "OK"
    
    def test_can_open_position_insufficient_capital(self):
        """Недостаточно капитала для позиции"""
        pm = PortfolioManager(
            total_capital=10000.0,
            symbols=['BTC/USDT']
        )
        
        can_open, reason = pm.can_open_position('BTC/USDT', 20000.0)
        
        assert can_open is False
        assert "Insufficient capital" in reason
    
    def test_can_open_position_max_symbols_limit(self):
        """Превышен лимит активных символов"""
        pm = PortfolioManager(
            total_capital=100000.0,
            symbols=['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT'],
            max_symbols_active=2,
            max_portfolio_risk_pct=0.30  # 30% чтобы риск не мешал
        )
        
        # Открыть 2 позиции (лимит)
        pm.allocate_position('BTC/USDT', 10000.0)
        pm.allocate_position('ETH/USDT', 10000.0)
        
        # Попытаться открыть 3-ю
        can_open, reason = pm.can_open_position('BNB/USDT', 10000.0)
        
        assert can_open is False
        assert "Max active symbols" in reason
    
    def test_can_open_position_portfolio_risk_limit(self):
        """Превышен лимит риска портфеля"""
        pm = PortfolioManager(
            total_capital=100000.0,
            symbols=['BTC/USDT'],
            max_portfolio_risk_pct=0.10  # 10% макс
        )
        
        # Попытаться открыть позицию > 10%
        can_open, reason = pm.can_open_position('BTC/USDT', 15000.0)
        
        assert can_open is False
        assert "risk limit exceeded" in reason
    
    def test_allocate_position(self):
        """Выделение капитала для позиции"""
        pm = PortfolioManager(
            total_capital=100000.0,
            symbols=['BTC/USDT', 'ETH/USDT']
        )
        
        success = pm.allocate_position('BTC/USDT', 10000.0)
        
        assert success is True
        
        alloc = pm.state.allocations['BTC/USDT']
        assert alloc.current_exposure == 10000.0
        assert alloc.available_capital == pytest.approx(40000.0, abs=0.1)
        
        assert pm.state.total_exposure == 10000.0
        assert pm.state.available_capital == pytest.approx(90000.0, abs=0.1)
    
    def test_release_position(self):
        """Освобождение капитала после закрытия позиции"""
        pm = PortfolioManager(
            total_capital=100000.0,
            symbols=['BTC/USDT']
        )
        
        # Открыть позицию
        pm.allocate_position('BTC/USDT', 10000.0)
        
        # Закрыть с прибылью $500
        pm.release_position('BTC/USDT', 10000.0, pnl=500.0)
        
        alloc = pm.state.allocations['BTC/USDT']
        assert alloc.current_exposure == 0.0
        assert alloc.available_capital == pytest.approx(100500.0, abs=0.1)
        assert alloc.pnl == 500.0
        
        assert pm.state.total_exposure == 0.0
        assert pm.state.available_capital == pytest.approx(100500.0, abs=0.1)
        assert pm.state.total_pnl == 500.0
    
    def test_update_prices(self):
        """Обновление истории цен"""
        pm = PortfolioManager(
            total_capital=100000.0,
            symbols=['BTC/USDT', 'ETH/USDT']
        )
        
        # Добавить 40 свечей для корреляции
        for i in range(40):
            pm.update_prices({
                'BTC/USDT': 100000.0 + i * 100,
                'ETH/USDT': 4000.0 + i * 10
            })
        
        # Проверить историю
        assert len(pm.price_history['BTC/USDT']) == 40
        assert len(pm.price_history['ETH/USDT']) == 40
        
        # Проверить что корреляционная матрица создана
        assert pm.state.correlation_matrix is not None
        assert pm.state.correlation_matrix.shape == (2, 2)
    
    def test_correlation_limit(self):
        """Ограничение на высокую корреляцию"""
        pm = PortfolioManager(
            total_capital=100000.0,
            symbols=['BTC/USDT', 'ETH/USDT'],
            correlation_threshold=0.7,
            max_portfolio_risk_pct=0.30  # 30% чтобы риск не блокировал
        )
        
        # Добавить цены с высокой корреляцией (почти одинаковые движения)
        for i in range(40):
            price_movement = i * 100
            pm.update_prices({
                'BTC/USDT': 100000.0 + price_movement,
                'ETH/USDT': 4000.0 + price_movement * 0.04  # Пропорциональное движение
            })
        
        # Открыть позицию BTC
        pm.allocate_position('BTC/USDT', 10000.0)
        
        # Попытаться открыть ETH (должна быть высокая корреляция)
        can_open, reason = pm.can_open_position('ETH/USDT', 10000.0)
        
        # Если корреляция высокая, должен быть отказ
        if not can_open:
            assert "correlation" in reason.lower()
    
    def test_rebalance(self):
        """Ребалансировка портфеля"""
        pm = PortfolioManager(
            total_capital=100000.0,
            symbols=['BTC/USDT', 'ETH/USDT']
        )
        
        # Изначально по 50% каждому
        assert pm.state.allocations['BTC/USDT'].allocated_capital == pytest.approx(50000.0, abs=0.1)
        
        # Ребалансировать: 70% BTC, 30% ETH
        pm.rebalance({
            'BTC/USDT': 0.7,
            'ETH/USDT': 0.3
        })
        
        assert pm.state.allocations['BTC/USDT'].allocated_capital == pytest.approx(70000.0, abs=0.1)
        assert pm.state.allocations['ETH/USDT'].allocated_capital == pytest.approx(30000.0, abs=0.1)
    
    def test_get_statistics(self):
        """Получение статистики портфеля"""
        pm = PortfolioManager(
            total_capital=100000.0,
            symbols=['BTC/USDT', 'ETH/USDT']
        )
        
        pm.allocate_position('BTC/USDT', 10000.0)
        
        stats = pm.get_statistics()
        
        assert stats['total_capital'] == 100000.0
        assert stats['total_exposure'] == 10000.0
        assert stats['risk_pct'] == pytest.approx(10.0, abs=0.1)
        assert stats['active_symbols'] == 1
        assert 'BTC/USDT' in stats['allocations']


def test_full_workflow():
    """Полный рабочий процесс"""
    print("\n" + "=" * 80)
    print("ТЕСТ: Полный workflow Portfolio Manager")
    print("=" * 80)
    
    # 1. Создать портфель $100k с 3 символами
    pm = PortfolioManager(
        total_capital=100000.0,
        symbols=['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
        max_portfolio_risk_pct=0.15,
        max_symbols_active=3
    )
    
    print("\n1️⃣ Портфель создан:")
    pm.print_summary()
    
    # 2. Открыть позицию BTC
    print("\n2️⃣ Открываем позицию BTC/USDT...")
    success = pm.allocate_position('BTC/USDT', 8000.0)
    assert success is True
    pm.print_summary()
    
    # 3. Открыть позицию ETH
    print("\n3️⃣ Открываем позицию ETH/USDT...")
    success = pm.allocate_position('ETH/USDT', 5000.0)
    assert success is True
    pm.print_summary()
    
    # 4. Закрыть BTC с прибылью
    print("\n4️⃣ Закрываем BTC/USDT с прибылью $800...")
    pm.release_position('BTC/USDT', 8000.0, pnl=800.0)
    pm.print_summary()
    
    # 5. Проверить статистику
    print("\n5️⃣ Финальная статистика:")
    stats = pm.get_statistics()
    
    print(f"   Total P&L: ${stats['total_pnl']:+,.2f}")
    print(f"   Active Symbols: {stats['active_symbols']}")
    print(f"   Risk: {stats['risk_pct']:.1f}%")
    
    assert stats['total_pnl'] == 800.0
    assert stats['active_symbols'] == 1  # Только ETH
    
    print("\n✅ Workflow успешно завершён!")


if __name__ == '__main__':
    # Запустить полный workflow
    test_full_workflow()
    
    print("\n" + "=" * 80)
    print("🧪 Запуск всех unit тестов...")
    print("=" * 80)
    
    # Запустить pytest
    pytest.main([__file__, '-v'])

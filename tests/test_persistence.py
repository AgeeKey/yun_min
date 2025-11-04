"""
Тесты для persistence layer (database + models + repositories)
"""

import pytest
from datetime import datetime, timedelta
from yunmin.store import (
    init_db, get_session, close_db,
    Position, Trade, PortfolioSnapshot, GrokDecision,
    PositionSide, PositionStatus,
    PositionRepository, TradeRepository, PortfolioRepository,
    GrokDecisionRepository
)


@pytest.fixture(scope='function')
def db_session():
    """Создать временную БД для тестов"""
    # In-memory SQLite для тестов
    init_db('sqlite:///:memory:', echo=False)
    
    session = get_session()
    yield session
    
    session.close()
    close_db()


class TestDatabase:
    """Тесты инициализации БД"""
    
    def test_init_db_in_memory(self):
        """Инициализация in-memory БД"""
        init_db('sqlite:///:memory:')
        session = get_session()
        
        assert session is not None
        
        session.close()
        close_db()
    
    def test_init_db_creates_tables(self, db_session):
        """Проверка что таблицы созданы"""
        from yunmin.store.database import Base, get_engine
        
        engine = get_engine()
        tables = Base.metadata.tables.keys()
        
        assert 'positions' in tables
        assert 'trades' in tables
        assert 'portfolio_snapshots' in tables
        assert 'grok_decisions' in tables


class TestPositionModel:
    """Тесты модели Position"""
    
    def test_create_position(self, db_session):
        """Создание позиции"""
        position = Position(
            symbol='BTC/USDT',
            side=PositionSide.LONG,
            entry_price=100000.0,
            amount=0.01,
            stop_loss=95000.0,
            take_profit=110000.0
        )
        
        db_session.add(position)
        db_session.commit()
        
        assert position.id is not None
        assert position.status == PositionStatus.OPEN
        assert position.opened_at is not None
    
    def test_position_to_dict(self, db_session):
        """Конвертация позиции в dict"""
        position = Position(
            symbol='ETH/USDT',
            side=PositionSide.SHORT,
            entry_price=4000.0,
            amount=1.0
        )
        
        db_session.add(position)
        db_session.commit()
        
        data = position.to_dict()
        
        assert data['symbol'] == 'ETH/USDT'
        assert data['side'] == 'SHORT'
        assert data['entry_price'] == 4000.0


class TestPositionRepository:
    """Тесты PositionRepository"""
    
    def test_create_position(self, db_session):
        """Создание позиции через repository"""
        repo = PositionRepository(db_session)
        
        position = repo.create(
            symbol='BTC/USDT',
            side=PositionSide.LONG,
            entry_price=100000.0,
            amount=0.01,
            stop_loss=95000.0,
            take_profit=110000.0,
            entry_fee=10.0,
            strategy_name='EMA_Crossover'
        )
        
        assert position.id is not None
        assert position.symbol == 'BTC/USDT'
        assert position.status == PositionStatus.OPEN
    
    def test_close_position_long_profit(self, db_session):
        """Закрытие LONG позиции с прибылью"""
        repo = PositionRepository(db_session)
        
        # Открыть позицию
        position = repo.create(
            symbol='BTC/USDT',
            side=PositionSide.LONG,
            entry_price=100000.0,
            amount=0.01,
            entry_fee=10.0
        )
        
        # Закрыть с прибылью (+5%)
        closed = repo.close(
            position_id=position.id,
            exit_price=105000.0,
            exit_fee=10.5
        )
        
        assert closed.status == PositionStatus.CLOSED
        assert closed.exit_price == 105000.0
        
        # P&L = (105000 - 100000) * 0.01 - fees = 50 - 20.5 = 29.5
        assert closed.realized_pnl == pytest.approx(29.5, abs=0.01)
        assert closed.closed_at is not None
    
    def test_close_position_short_profit(self, db_session):
        """Закрытие SHORT позиции с прибылью"""
        repo = PositionRepository(db_session)
        
        # Открыть SHORT
        position = repo.create(
            symbol='ETH/USDT',
            side=PositionSide.SHORT,
            entry_price=4000.0,
            amount=1.0,
            entry_fee=4.0
        )
        
        # Закрыть с прибылью (цена упала на 5%)
        closed = repo.close(
            position_id=position.id,
            exit_price=3800.0,
            exit_fee=3.8
        )
        
        # P&L = (4000 - 3800) * 1.0 - fees = 200 - 7.8 = 192.2
        assert closed.realized_pnl == pytest.approx(192.2, abs=0.01)
    
    def test_get_open_positions(self, db_session):
        """Получение открытых позиций"""
        repo = PositionRepository(db_session)
        
        # Создать 2 открытые и 1 закрытую
        pos1 = repo.create('BTC/USDT', PositionSide.LONG, 100000.0, 0.01)
        pos2 = repo.create('ETH/USDT', PositionSide.SHORT, 4000.0, 1.0)
        pos3 = repo.create('BNB/USDT', PositionSide.LONG, 500.0, 10.0)
        repo.close(pos3.id, 510.0)
        
        open_positions = repo.get_open_positions()
        
        assert len(open_positions) == 2
        assert pos1.id in [p.id for p in open_positions]
        assert pos2.id in [p.id for p in open_positions]
    
    def test_get_closed_positions(self, db_session):
        """Получение закрытых позиций"""
        repo = PositionRepository(db_session)
        
        pos1 = repo.create('BTC/USDT', PositionSide.LONG, 100000.0, 0.01)
        pos2 = repo.create('ETH/USDT', PositionSide.LONG, 4000.0, 1.0)
        
        repo.close(pos1.id, 105000.0)
        repo.close(pos2.id, 4100.0)
        
        closed = repo.get_closed_positions()
        
        assert len(closed) == 2
        assert all(p.status == PositionStatus.CLOSED for p in closed)


class TestTradeRepository:
    """Тесты TradeRepository"""
    
    def test_create_trade(self, db_session):
        """Создание сделки"""
        repo = TradeRepository(db_session)
        
        trade = repo.create(
            symbol='BTC/USDT',
            side='buy',
            price=100000.0,
            amount=0.01,
            fee=10.0,
            exchange_order_id='12345'
        )
        
        assert trade.id is not None
        assert trade.total == 1000.0  # 100000 * 0.01
        assert trade.executed_at is not None
    
    def test_link_trade_to_position(self, db_session):
        """Связывание сделки с позицией"""
        pos_repo = PositionRepository(db_session)
        trade_repo = TradeRepository(db_session)
        
        # Создать позицию
        position = pos_repo.create(
            'BTC/USDT', PositionSide.LONG, 100000.0, 0.01
        )
        
        # Создать сделку для этой позиции
        trade = trade_repo.create(
            symbol='BTC/USDT',
            side='buy',
            price=100000.0,
            amount=0.01,
            position_id=position.id
        )
        
        assert trade.position_id == position.id
        assert len(position.trades) == 1
        assert position.trades[0].id == trade.id
    
    def test_get_recent_trades(self, db_session):
        """Получение последних сделок"""
        repo = TradeRepository(db_session)
        
        # Создать несколько сделок
        for i in range(5):
            repo.create(
                symbol='BTC/USDT',
                side='buy',
                price=100000.0 + i * 100,
                amount=0.01
            )
        
        trades = repo.get_recent_trades(limit=3)
        
        assert len(trades) == 3
        # Последние должны быть первыми
        assert trades[0].price > trades[1].price
    
    def test_get_total_volume(self, db_session):
        """Расчёт общего объёма"""
        repo = TradeRepository(db_session)
        
        repo.create('BTC/USDT', 'buy', 100000.0, 0.01)  # $1000
        repo.create('ETH/USDT', 'buy', 4000.0, 1.0)     # $4000
        repo.create('BNB/USDT', 'sell', 500.0, 10.0)    # $5000
        
        total_volume = repo.get_total_volume()
        
        assert total_volume == pytest.approx(10000.0, abs=0.01)


class TestPortfolioRepository:
    """Тесты PortfolioRepository"""
    
    def test_create_snapshot(self, db_session):
        """Создание snapshot портфеля"""
        repo = PortfolioRepository(db_session)
        
        snapshot = repo.create_snapshot(
            total_capital=100000.0,
            available_capital=90000.0,
            total_exposure=10000.0,
            total_pnl=500.0,
            unrealized_pnl=300.0,
            realized_pnl=200.0,
            win_rate=75.0,
            profit_factor=2.5,
            active_symbols_count=2,
            active_symbols_list='["BTC/USDT", "ETH/USDT"]'
        )
        
        assert snapshot.id is not None
        assert snapshot.total_capital == 100000.0
        assert snapshot.win_rate == 75.0
    
    def test_get_latest_snapshot(self, db_session):
        """Получение последнего snapshot"""
        repo = PortfolioRepository(db_session)
        
        # Создать несколько snapshots
        repo.create_snapshot(100000.0, 95000.0, 5000.0, total_pnl=100.0)
        repo.create_snapshot(100100.0, 95100.0, 5000.0, total_pnl=200.0)
        repo.create_snapshot(100200.0, 95200.0, 5000.0, total_pnl=300.0)
        
        latest = repo.get_latest()
        
        assert latest is not None
        assert latest.total_pnl == 300.0  # Последний
    
    def test_get_history(self, db_session):
        """Получение истории snapshots"""
        repo = PortfolioRepository(db_session)
        
        # Создать несколько snapshots
        for i in range(5):
            repo.create_snapshot(
                100000.0 + i * 100,
                95000.0,
                5000.0,
                total_pnl=i * 50.0
            )
        
        history = repo.get_history(limit=3)
        
        assert len(history) == 3
        # Последние должны быть первыми
        assert history[0].total_pnl > history[1].total_pnl


class TestGrokDecisionRepository:
    """Тесты GrokDecisionRepository"""
    
    def test_create_decision(self, db_session):
        """Создание решения Grok"""
        repo = GrokDecisionRepository(db_session)
        
        decision = repo.create(
            symbol='BTC/USDT',
            side='buy',
            signal_reason='Strong uptrend + RSI rebound',
            approved=True,
            confidence=0.85,
            reasoning='Favorable market conditions',
            risk_factors='[]',
            market_condition_score=8.5,
            signal_quality_score=9.0,
            risk_reward_ratio=3.5
        )
        
        assert decision.id is not None
        assert decision.approved is True
        assert decision.confidence == 0.85
    
    def test_update_decision_result(self, db_session):
        """Обновление результата решения"""
        grok_repo = GrokDecisionRepository(db_session)
        pos_repo = PositionRepository(db_session)
        
        # Создать решение
        decision = grok_repo.create(
            'BTC/USDT', 'buy', 'Test signal',
            approved=True, confidence=0.8, reasoning='Test'
        )
        
        # Создать и закрыть позицию
        position = pos_repo.create('BTC/USDT', PositionSide.LONG, 100000.0, 0.01)
        closed_pos = pos_repo.close(position.id, 105000.0)
        
        # Обновить результат
        updated = grok_repo.update_result(
            decision.id,
            position.id,
            closed_pos.realized_pnl
        )
        
        assert updated.position_id == position.id
        assert updated.actual_pnl == closed_pos.realized_pnl
    
    def test_accuracy_stats(self, db_session):
        """Статистика точности Grok"""
        grok_repo = GrokDecisionRepository(db_session)
        pos_repo = PositionRepository(db_session)
        
        # Создать 3 одобренных решения (2 прибыльных, 1 убыточное)
        for i in range(3):
            decision = grok_repo.create(
                'BTC/USDT', 'buy', f'Signal {i}',
                approved=True, confidence=0.8, reasoning='Test'
            )
            
            position = pos_repo.create('BTC/USDT', PositionSide.LONG, 100000.0, 0.01)
            
            # 2 прибыльных, 1 убыточное
            exit_price = 105000.0 if i < 2 else 95000.0
            closed = pos_repo.close(position.id, exit_price)
            
            grok_repo.update_result(decision.id, position.id, closed.realized_pnl)
        
        # Создать 1 vetoed решение (был бы убыточным)
        veto_decision = grok_repo.create(
            'ETH/USDT', 'sell', 'Risky signal',
            approved=False, confidence=0.3, reasoning='Too risky'
        )
        
        veto_pos = pos_repo.create('ETH/USDT', PositionSide.SHORT, 4000.0, 1.0)
        veto_closed = pos_repo.close(veto_pos.id, 4200.0)  # Убыток для SHORT
        grok_repo.update_result(veto_decision.id, veto_pos.id, veto_closed.realized_pnl)
        
        # Получить статистику
        stats = grok_repo.get_accuracy_stats(days=30)
        
        assert stats['total_decisions'] == 4
        assert stats['approved_count'] == 3
        assert stats['vetoed_count'] == 1
        assert stats['approved_win_rate'] == pytest.approx(66.67, abs=0.1)  # 2/3
        assert stats['vetoed_would_have_lost'] == 100.0  # 1/1


def test_full_workflow(db_session):
    """Полный workflow: позиция → сделки → snapshot"""
    print("\n" + "=" * 80)
    print("ТЕСТ: Full Persistence Workflow")
    print("=" * 80)
    
    pos_repo = PositionRepository(db_session)
    trade_repo = TradeRepository(db_session)
    portfolio_repo = PortfolioRepository(db_session)
    
    # 1. Открыть позицию
    print("\n1️⃣ Открываем позицию BTC...")
    position = pos_repo.create(
        symbol='BTC/USDT',
        side=PositionSide.LONG,
        entry_price=100000.0,
        amount=0.01,
        stop_loss=95000.0,
        take_profit=110000.0,
        entry_fee=10.0
    )
    print(f"   Position ID: {position.id}")
    
    # 2. Создать entry trade
    print("\n2️⃣ Создаём entry trade...")
    entry_trade = trade_repo.create(
        symbol='BTC/USDT',
        side='buy',
        price=100000.0,
        amount=0.01,
        fee=10.0,
        position_id=position.id
    )
    print(f"   Trade ID: {entry_trade.id}, Total: ${entry_trade.total:.2f}")
    
    # 3. Закрыть позицию
    print("\n3️⃣ Закрываем позицию с прибылью...")
    closed_position = pos_repo.close(
        position_id=position.id,
        exit_price=105000.0,
        exit_fee=10.5
    )
    print(f"   P&L: ${closed_position.realized_pnl:+.2f}")
    
    # 4. Создать exit trade
    exit_trade = trade_repo.create(
        symbol='BTC/USDT',
        side='sell',
        price=105000.0,
        amount=0.01,
        fee=10.5,
        position_id=position.id
    )
    
    # 5. Создать portfolio snapshot
    print("\n4️⃣ Создаём portfolio snapshot...")
    snapshot = portfolio_repo.create_snapshot(
        total_capital=100029.5,  # 100000 + 29.5 profit
        available_capital=100029.5,
        total_exposure=0.0,
        total_pnl=29.5,
        realized_pnl=29.5,
        win_rate=100.0,
        active_symbols_count=0
    )
    print(f"   Snapshot ID: {snapshot.id}, Capital: ${snapshot.total_capital:.2f}")
    
    # Проверки
    assert closed_position.realized_pnl == pytest.approx(29.5, abs=0.01)
    assert len(position.trades) == 2
    assert snapshot.total_pnl == 29.5
    
    print("\n✅ Full workflow успешно завершён!")


if __name__ == '__main__':
    # Запустить full workflow
    test_full_workflow()
    
    print("\n" + "=" * 80)
    print("🧪 Запуск всех unit тестов...")
    print("=" * 80)
    
    pytest.main([__file__, '-v'])

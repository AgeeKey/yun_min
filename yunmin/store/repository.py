"""
Repository pattern для работы с БД

Абстракция над SQLAlchemy для удобного доступа к данным
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, UTC
from sqlalchemy import desc, and_, or_, func
from sqlalchemy.orm import Session
from loguru import logger

from .models import (
    Position, Trade, PortfolioSnapshot, GrokDecision,
    PositionSide, PositionStatus
)


class PositionRepository:
    """
    Repository для работы с позициями
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
        self,
        symbol: str,
        side: PositionSide,
        entry_price: float,
        amount: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        entry_fee: float = 0.0,
        strategy_name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Position:
        """Создать новую позицию"""
        position = Position(
            symbol=symbol,
            side=side,
            status=PositionStatus.OPEN,
            entry_price=entry_price,
            amount=amount,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_fee=entry_fee,
            strategy_name=strategy_name,
            notes=notes,
            opened_at=datetime.now(UTC)
        )
        
        self.session.add(position)
        self.session.commit()
        
        logger.info(
            f"Created position: {symbol} {side.value} "
            f"@ ${entry_price:.2f} x {amount}"
        )
        
        return position
    
    def close(
        self,
        position_id: int,
        exit_price: float,
        exit_fee: float = 0.0
    ) -> Position:
        """Закрыть позицию"""
        position = self.get_by_id(position_id)
        
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        if position.status != PositionStatus.OPEN:
            raise ValueError(
                f"Position {position_id} is not open (status: {position.status.value})"
            )
        
        # Рассчитать P&L
        if position.side == PositionSide.LONG:
            pnl = (exit_price - position.entry_price) * position.amount
        else:  # SHORT
            pnl = (position.entry_price - exit_price) * position.amount
        
        # Вычесть комиссии
        total_fees = position.entry_fee + exit_fee
        realized_pnl = pnl - total_fees
        
        # Процент P&L
        cost_basis = position.entry_price * position.amount
        realized_pnl_pct = (realized_pnl / cost_basis) * 100 if cost_basis > 0 else 0.0
        
        # Обновить позицию
        position.exit_price = exit_price
        position.exit_fee = exit_fee
        position.realized_pnl = realized_pnl
        position.realized_pnl_pct = realized_pnl_pct
        position.status = PositionStatus.CLOSED
        position.closed_at = datetime.now(UTC)
        
        self.session.commit()
        
        logger.info(
            f"Closed position {position_id}: "
            f"P&L ${realized_pnl:+.2f} ({realized_pnl_pct:+.2f}%)"
        )
        
        return position
    
    def get_by_id(self, position_id: int) -> Optional[Position]:
        """Получить позицию по ID"""
        return self.session.query(Position).filter(
            Position.id == position_id
        ).first()
    
    def get_open_positions(
        self,
        symbol: Optional[str] = None
    ) -> List[Position]:
        """Получить все открытые позиции"""
        query = self.session.query(Position).filter(
            Position.status == PositionStatus.OPEN
        )
        
        if symbol:
            query = query.filter(Position.symbol == symbol)
        
        return query.order_by(Position.opened_at).all()
    
    def get_closed_positions(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Position]:
        """Получить закрытые позиции"""
        query = self.session.query(Position).filter(
            Position.status == PositionStatus.CLOSED
        )
        
        if symbol:
            query = query.filter(Position.symbol == symbol)
        
        return query.order_by(
            desc(Position.closed_at)
        ).limit(limit).all()
    
    def get_all_positions(
        self,
        symbol: Optional[str] = None,
        status: Optional[PositionStatus] = None,
        limit: int = 100
    ) -> List[Position]:
        """Получить все позиции с фильтрацией"""
        query = self.session.query(Position)
        
        if symbol:
            query = query.filter(Position.symbol == symbol)
        
        if status:
            query = query.filter(Position.status == status)
        
        return query.order_by(
            desc(Position.opened_at)
        ).limit(limit).all()
    
    def delete(self, position_id: int) -> bool:
        """Удалить позицию (для тестов)"""
        position = self.get_by_id(position_id)
        
        if position:
            self.session.delete(position)
            self.session.commit()
            return True
        
        return False


class TradeRepository:
    """
    Repository для работы со сделками
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
        self,
        symbol: str,
        side: str,
        price: float,
        amount: float,
        fee: float = 0.0,
        fee_currency: str = 'USDT',
        position_id: Optional[int] = None,
        exchange_order_id: Optional[str] = None,
        exchange_trade_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Trade:
        """Создать новую сделку"""
        total = price * amount
        
        trade = Trade(
            symbol=symbol,
            side=side,
            price=price,
            amount=amount,
            total=total,
            fee=fee,
            fee_currency=fee_currency,
            position_id=position_id,
            exchange_order_id=exchange_order_id,
            exchange_trade_id=exchange_trade_id,
            executed_at=datetime.now(UTC),
            notes=notes
        )
        
        self.session.add(trade)
        self.session.commit()
        
        logger.debug(
            f"Created trade: {symbol} {side} "
            f"@ ${price:.2f} x {amount} (fee: ${fee:.2f})"
        )
        
        return trade
    
    def get_by_id(self, trade_id: int) -> Optional[Trade]:
        """Получить сделку по ID"""
        return self.session.query(Trade).filter(
            Trade.id == trade_id
        ).first()
    
    def get_by_position(self, position_id: int) -> List[Trade]:
        """Получить все сделки позиции"""
        return self.session.query(Trade).filter(
            Trade.position_id == position_id
        ).order_by(Trade.executed_at).all()
    
    def get_recent_trades(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Trade]:
        """Получить последние сделки"""
        query = self.session.query(Trade)
        
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        
        return query.order_by(
            desc(Trade.executed_at)
        ).limit(limit).all()
    
    def get_total_volume(
        self,
        symbol: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> float:
        """Получить общий объём торговли"""
        query = self.session.query(func.sum(Trade.total))
        
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        
        if since:
            query = query.filter(Trade.executed_at >= since)
        
        result = query.scalar()
        return result if result else 0.0


class PortfolioRepository:
    """
    Repository для работы с portfolio snapshots
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_snapshot(
        self,
        total_capital: float,
        available_capital: float,
        total_exposure: float,
        total_pnl: float = 0.0,
        unrealized_pnl: float = 0.0,
        realized_pnl: float = 0.0,
        win_rate: Optional[float] = None,
        profit_factor: Optional[float] = None,
        sharpe_ratio: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        active_symbols_count: int = 0,
        active_symbols_list: Optional[str] = None,
        notes: Optional[str] = None
    ) -> PortfolioSnapshot:
        """Создать snapshot портфеля"""
        snapshot = PortfolioSnapshot(
            total_capital=total_capital,
            available_capital=available_capital,
            total_exposure=total_exposure,
            total_pnl=total_pnl,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            active_symbols_count=active_symbols_count,
            active_symbols_list=active_symbols_list,
            snapshot_at=datetime.now(UTC),
            notes=notes
        )
        
        self.session.add(snapshot)
        self.session.commit()
        
        logger.debug(
            f"Created portfolio snapshot: "
            f"capital=${total_capital:.2f}, P&L=${total_pnl:+.2f}"
        )
        
        return snapshot
    
    def get_latest(self) -> Optional[PortfolioSnapshot]:
        """Получить последний snapshot"""
        return self.session.query(PortfolioSnapshot).order_by(
            desc(PortfolioSnapshot.snapshot_at)
        ).first()
    
    def get_history(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PortfolioSnapshot]:
        """Получить историю snapshots"""
        query = self.session.query(PortfolioSnapshot)
        
        if since:
            query = query.filter(PortfolioSnapshot.snapshot_at >= since)
        
        return query.order_by(
            desc(PortfolioSnapshot.snapshot_at)
        ).limit(limit).all()
    
    def get_daily_snapshots(self, days: int = 30) -> List[PortfolioSnapshot]:
        """Получить дневные snapshots (последние N дней)"""
        since = datetime.now(UTC) - timedelta(days=days)
        
        # Группировка по дням (берём последний snapshot каждого дня)
        # Это упрощённая версия, в production использовать SQL window functions
        snapshots = self.get_history(since=since, limit=days * 10)
        
        # Группировать по дням
        daily_snapshots = {}
        for snapshot in snapshots:
            day = snapshot.snapshot_at.date()
            if day not in daily_snapshots:
                daily_snapshots[day] = snapshot
        
        return list(daily_snapshots.values())


class GrokDecisionRepository:
    """
    Repository для решений Grok AI
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
        self,
        symbol: str,
        side: str,
        signal_reason: str,
        approved: bool,
        confidence: float,
        reasoning: str,
        risk_factors: Optional[str] = None,
        market_condition_score: Optional[float] = None,
        signal_quality_score: Optional[float] = None,
        risk_reward_ratio: Optional[float] = None
    ) -> GrokDecision:
        """Создать запись решения Grok"""
        decision = GrokDecision(
            symbol=symbol,
            side=side,
            signal_reason=signal_reason,
            approved=approved,
            confidence=confidence,
            reasoning=reasoning,
            risk_factors=risk_factors,
            market_condition_score=market_condition_score,
            signal_quality_score=signal_quality_score,
            risk_reward_ratio=risk_reward_ratio,
            decided_at=datetime.now(UTC)
        )
        
        self.session.add(decision)
        self.session.commit()
        
        return decision
    
    def update_result(
        self,
        decision_id: int,
        position_id: int,
        actual_pnl: float
    ) -> Optional[GrokDecision]:
        """Обновить результат решения (после закрытия позиции)"""
        decision = self.session.query(GrokDecision).filter(
            GrokDecision.id == decision_id
        ).first()
        
        if decision:
            decision.position_id = position_id
            decision.actual_pnl = actual_pnl
            self.session.commit()
        
        return decision
    
    def get_accuracy_stats(self, days: int = 30) -> Dict[str, Any]:
        """Получить статистику точности Grok решений"""
        since = datetime.now(UTC) - timedelta(days=days)
        
        decisions = self.session.query(GrokDecision).filter(
            and_(
                GrokDecision.decided_at >= since,
                GrokDecision.actual_pnl.isnot(None)  # Только завершённые
            )
        ).all()
        
        if not decisions:
            return {
                'total_decisions': 0,
                'approved_count': 0,
                'vetoed_count': 0,
                'approved_win_rate': 0.0,
                'vetoed_would_have_lost': 0.0,
                'avg_confidence': 0.0
            }
        
        approved = [d for d in decisions if d.approved]
        vetoed = [d for d in decisions if not d.approved]
        
        # Win rate одобренных сигналов
        approved_wins = sum(1 for d in approved if d.actual_pnl > 0)
        approved_win_rate = (
            (approved_wins / len(approved) * 100) if approved else 0.0
        )
        
        # Сколько из vetoed были бы убыточными
        vetoed_losses = sum(1 for d in vetoed if d.actual_pnl < 0)
        vetoed_would_have_lost = (
            (vetoed_losses / len(vetoed) * 100) if vetoed else 0.0
        )
        
        # Средняя уверенность
        avg_confidence = sum(d.confidence for d in decisions) / len(decisions)
        
        return {
            'total_decisions': len(decisions),
            'approved_count': len(approved),
            'vetoed_count': len(vetoed),
            'approved_win_rate': approved_win_rate,
            'vetoed_would_have_lost': vetoed_would_have_lost,
            'avg_confidence': avg_confidence * 100
        }

"""
SQLAlchemy models для персистентности данных
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from .database import Base


class PositionSide(str, Enum):
    """Сторона позиции"""
    LONG = 'LONG'
    SHORT = 'SHORT'


class PositionStatus(str, Enum):
    """Статус позиции"""
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'
    CANCELLED = 'CANCELLED'


class Position(Base):
    """
    Модель позиции
    
    Сохраняет открытые и закрытые позиции
    """
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Основные данные
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(SQLEnum(PositionSide), nullable=False)
    status = Column(SQLEnum(PositionStatus), nullable=False, default=PositionStatus.OPEN, index=True)
    
    # Цены и объёмы
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    amount = Column(Float, nullable=False)
    
    # Stop Loss / Take Profit
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    
    # P&L
    realized_pnl = Column(Float, nullable=True)
    realized_pnl_pct = Column(Float, nullable=True)
    
    # Комиссии
    entry_fee = Column(Float, default=0.0)
    exit_fee = Column(Float, default=0.0)
    
    # Временные метки
    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    closed_at = Column(DateTime, nullable=True)
    
    # Метаданные
    strategy_name = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Связь с trades
    trades = relationship('Trade', back_populates='position', cascade='all, delete-orphan')
    
    def __repr__(self):
        return (
            f"<Position(id={self.id}, symbol={self.symbol}, "
            f"side={self.side.value}, status={self.status.value}, "
            f"entry={self.entry_price}, amount={self.amount})>"
        )
    
    def to_dict(self):
        """Конвертировать в словарь"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side.value,
            'status': self.status.value,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'amount': self.amount,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'realized_pnl': self.realized_pnl,
            'realized_pnl_pct': self.realized_pnl_pct,
            'entry_fee': self.entry_fee,
            'exit_fee': self.exit_fee,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'strategy_name': self.strategy_name,
            'notes': self.notes
        }


class Trade(Base):
    """
    Модель сделки (исполненный ордер)
    
    Одна позиция может иметь несколько trades (частичное исполнение)
    """
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Связь с позицией
    position_id = Column(Integer, ForeignKey('positions.id'), nullable=True, index=True)
    position = relationship('Position', back_populates='trades')
    
    # Основные данные
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # 'buy' или 'sell'
    
    # Цена и объём
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    total = Column(Float, nullable=False)  # price * amount
    
    # Комиссия
    fee = Column(Float, default=0.0)
    fee_currency = Column(String(10), default='USDT')
    
    # Exchange данные
    exchange_order_id = Column(String(100), nullable=True)
    exchange_trade_id = Column(String(100), nullable=True)
    
    # Временная метка
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Метаданные
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return (
            f"<Trade(id={self.id}, symbol={self.symbol}, "
            f"side={self.side}, price={self.price}, amount={self.amount})>"
        )
    
    def to_dict(self):
        """Конвертировать в словарь"""
        return {
            'id': self.id,
            'position_id': self.position_id,
            'symbol': self.symbol,
            'side': self.side,
            'price': self.price,
            'amount': self.amount,
            'total': self.total,
            'fee': self.fee,
            'fee_currency': self.fee_currency,
            'exchange_order_id': self.exchange_order_id,
            'exchange_trade_id': self.exchange_trade_id,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'notes': self.notes
        }


class PortfolioSnapshot(Base):
    """
    Snapshot состояния портфеля
    
    Сохраняется периодически для истории
    """
    __tablename__ = 'portfolio_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Капитал
    total_capital = Column(Float, nullable=False)
    available_capital = Column(Float, nullable=False)
    total_exposure = Column(Float, nullable=False)
    
    # P&L
    total_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    
    # Метрики
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    
    # Активные символы
    active_symbols_count = Column(Integer, default=0)
    active_symbols_list = Column(String(500), nullable=True)  # JSON список
    
    # Временная метка
    snapshot_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Метаданные
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return (
            f"<PortfolioSnapshot(id={self.id}, "
            f"capital={self.total_capital}, pnl={self.total_pnl}, "
            f"at={self.snapshot_at})>"
        )
    
    def to_dict(self):
        """Конвертировать в словарь"""
        return {
            'id': self.id,
            'total_capital': self.total_capital,
            'available_capital': self.available_capital,
            'total_exposure': self.total_exposure,
            'total_pnl': self.total_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'active_symbols_count': self.active_symbols_count,
            'active_symbols_list': self.active_symbols_list,
            'snapshot_at': self.snapshot_at.isoformat() if self.snapshot_at else None,
            'notes': self.notes
        }


class GrokDecision(Base):
    """
    Решения Grok AI (для анализа качества)
    """
    __tablename__ = 'grok_decisions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Сигнал
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    signal_reason = Column(Text, nullable=True)
    
    # Решение Grok
    approved = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    risk_factors = Column(Text, nullable=True)  # JSON список
    
    # Метрики
    market_condition_score = Column(Float, nullable=True)
    signal_quality_score = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)
    
    # Результат (если сделка была выполнена)
    position_id = Column(Integer, ForeignKey('positions.id'), nullable=True)
    actual_pnl = Column(Float, nullable=True)
    
    # Временная метка
    decided_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return (
            f"<GrokDecision(id={self.id}, symbol={self.symbol}, "
            f"approved={self.approved}, confidence={self.confidence})>"
        )
    
    def to_dict(self):
        """Конвертировать в словарь"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'signal_reason': self.signal_reason,
            'approved': self.approved,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'risk_factors': self.risk_factors,
            'market_condition_score': self.market_condition_score,
            'signal_quality_score': self.signal_quality_score,
            'risk_reward_ratio': self.risk_reward_ratio,
            'position_id': self.position_id,
            'actual_pnl': self.actual_pnl,
            'decided_at': self.decided_at.isoformat() if self.decided_at else None
        }

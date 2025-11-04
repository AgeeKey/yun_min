"""
Storage layer - персистентность данных

Сохранение состояния бота между перезапусками:
- Открытые позиции
- История сделок
- Статистика портфеля
- Параметры стратегии
"""

# State Manager доступен всегда
from .state_manager import StateManager

# Database опционально (требует sqlalchemy)
try:
    from .database import init_db, get_session, close_db, get_engine
    from .models import Position, Trade, PortfolioSnapshot, GrokDecision, PositionSide, PositionStatus
    from .repository import (
        PositionRepository,
        TradeRepository,
        PortfolioRepository,
        GrokDecisionRepository
    )
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    # Заглушки для отсутствующих функций
    init_db = None
    get_session = None
    close_db = None
    get_engine = None
    Position = None
    Trade = None
    PortfolioSnapshot = None
    GrokDecision = None
    PositionSide = None
    PositionStatus = None
    PositionRepository = None
    TradeRepository = None
    PortfolioRepository = None
    GrokDecisionRepository = None

__all__ = [
    # Database
    'init_db',
    'get_session',
    'close_db',
    'get_engine',
    # Models
    'Position',
    'Trade',
    'PortfolioSnapshot',
    'GrokDecision',
    'PositionSide',
    'PositionStatus',
    # Repositories
    'PositionRepository',
    'TradeRepository',
    'PortfolioRepository',
    'GrokDecisionRepository',
]

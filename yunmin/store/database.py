"""
Database setup and session management using SQLAlchemy
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.pool import StaticPool
from pathlib import Path
from loguru import logger
import os

# Base для всех моделей
Base = declarative_base()

# Global session factory
_SessionFactory = None
_engine = None


def init_db(database_url: str = None, echo: bool = False) -> None:
    """
    Инициализировать базу данных
    
    Args:
        database_url: URL базы данных (default: sqlite:///data/yunmin.db)
        echo: Логировать SQL запросы (для отладки)
    """
    global _SessionFactory, _engine
    
    if database_url is None:
        # Default: SQLite в папке data/
        data_dir = Path(__file__).parent.parent.parent / 'data'
        data_dir.mkdir(exist_ok=True)
        database_url = f'sqlite:///{data_dir}/yunmin.db'
    
    # Создать engine
    if database_url.startswith('sqlite'):
        # SQLite специфичные настройки
        _engine = create_engine(
            database_url,
            echo=echo,
            connect_args={'check_same_thread': False},
            poolclass=StaticPool
        )
    else:
        _engine = create_engine(database_url, echo=echo)
    
    # Создать session factory
    _SessionFactory = scoped_session(
        sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    )
    
    # Создать все таблицы
    Base.metadata.create_all(_engine)
    
    logger.info(f"Database initialized: {database_url}")


def get_session():
    """
    Получить сессию для работы с БД
    
    Returns:
        SQLAlchemy Session
    
    Raises:
        RuntimeError: Если БД не инициализирована
    """
    if _SessionFactory is None:
        raise RuntimeError(
            "Database not initialized. Call init_db() first."
        )
    
    return _SessionFactory()


def close_db() -> None:
    """Закрыть соединение с БД"""
    global _SessionFactory, _engine
    
    if _SessionFactory:
        _SessionFactory.remove()
        _SessionFactory = None
    
    if _engine:
        _engine.dispose()
        _engine = None
    
    logger.info("Database connection closed")


def get_engine():
    """Получить engine (для миграций и прямых запросов)"""
    if _engine is None:
        raise RuntimeError("Database not initialized")
    return _engine

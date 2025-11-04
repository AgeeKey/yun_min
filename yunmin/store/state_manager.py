"""
State Manager - сохранение состояния бота
Решает критическую проблему потери данных при перезапуске
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger


class StateManager:
    """
    Управление состоянием бота
    
    Сохраняет:
    - Открытые позиции
    - История сделок
    - P&L статистика
    - Настройки риска
    """
    
    def __init__(self, state_dir: str = "data"):
        """
        Args:
            state_dir: Директория для файлов состояния
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
        
        self.positions_file = self.state_dir / "positions.json"
        self.trades_file = self.state_dir / "trades.json"
        self.stats_file = self.state_dir / "statistics.json"
        
        logger.info(f"StateManager initialized: {self.state_dir.absolute()}")
        
    def save_positions(self, positions: Dict) -> bool:
        """
        Сохранить открытые позиции
        
        Args:
            positions: {symbol: {side, entry_price, amount, ...}}
        
        Returns:
            True если успешно
        """
        try:
            # Конвертировать datetime в строки
            positions_serializable = {}
            for symbol, pos in positions.items():
                pos_copy = pos.copy()
                if 'opened_at' in pos_copy and isinstance(pos_copy['opened_at'], datetime):
                    pos_copy['opened_at'] = pos_copy['opened_at'].isoformat()
                positions_serializable[symbol] = pos_copy
            
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(positions_serializable, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Saved {len(positions)} positions to {self.positions_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save positions: {e}")
            return False
            
    def load_positions(self) -> Dict:
        """
        Загрузить открытые позиции
        
        Returns:
            Словарь позиций или пустой dict
        """
        try:
            if not self.positions_file.exists():
                logger.info("No positions file found, starting fresh")
                return {}
            
            with open(self.positions_file, 'r', encoding='utf-8') as f:
                positions = json.load(f)
            
            # Конвертировать строки обратно в datetime
            for symbol, pos in positions.items():
                if 'opened_at' in pos and isinstance(pos['opened_at'], str):
                    pos['opened_at'] = datetime.fromisoformat(pos['opened_at'])
            
            logger.info(f"✅ Loaded {len(positions)} positions from {self.positions_file}")
            return positions
            
        except Exception as e:
            logger.error(f"❌ Failed to load positions: {e}")
            return {}
            
    def save_trades(self, trades: List) -> bool:
        """
        Сохранить историю сделок
        
        Args:
            trades: Список Trade объектов
        
        Returns:
            True если успешно
        """
        try:
            # Конвертировать Trade objects в dict
            trades_serializable = []
            for trade in trades:
                trade_dict = {
                    'symbol': trade.symbol,
                    'side': trade.side,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'amount': trade.amount,
                    'entry_fee': trade.entry_fee,
                    'exit_fee': trade.exit_fee,
                    'pnl': trade.pnl,
                    'pnl_pct': trade.pnl_pct,
                    'opened_at': trade.opened_at.isoformat() if hasattr(trade.opened_at, 'isoformat') else str(trade.opened_at),
                    'closed_at': trade.closed_at.isoformat() if hasattr(trade.closed_at, 'isoformat') else str(trade.closed_at)
                }
                trades_serializable.append(trade_dict)
            
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                json.dump(trades_serializable, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Saved {len(trades)} trades to {self.trades_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save trades: {e}")
            return False
            
    def load_trades(self) -> List[Dict]:
        """
        Загрузить историю сделок
        
        Returns:
            Список dict с данными сделок
        """
        try:
            if not self.trades_file.exists():
                logger.info("No trades file found, starting fresh")
                return []
            
            with open(self.trades_file, 'r', encoding='utf-8') as f:
                trades = json.load(f)
            
            logger.info(f"✅ Loaded {len(trades)} trades from {self.trades_file}")
            return trades
            
        except Exception as e:
            logger.error(f"❌ Failed to load trades: {e}")
            return []
            
    def save_statistics(self, stats: Dict) -> bool:
        """
        Сохранить статистику
        
        Args:
            stats: Словарь со статистикой
        
        Returns:
            True если успешно
        """
        try:
            stats_copy = stats.copy()
            stats_copy['last_updated'] = datetime.now().isoformat()
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_copy, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Saved statistics to {self.stats_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save statistics: {e}")
            return False
            
    def load_statistics(self) -> Dict:
        """
        Загрузить статистику
        
        Returns:
            Словарь со статистикой или пустой dict
        """
        try:
            if not self.stats_file.exists():
                logger.info("No statistics file found, starting fresh")
                return {}
            
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            
            logger.info(f"✅ Loaded statistics from {self.stats_file}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to load statistics: {e}")
            return {}
            
    def clear_all(self) -> bool:
        """
        Очистить все сохранённые данные
        
        Returns:
            True если успешно
        """
        try:
            for file in [self.positions_file, self.trades_file, self.stats_file]:
                if file.exists():
                    file.unlink()
                    logger.info(f"🗑️ Deleted {file}")
            
            logger.info("✅ All state files cleared")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to clear state files: {e}")
            return False
            
    def backup_state(self, backup_name: Optional[str] = None) -> bool:
        """
        Создать резервную копию состояния
        
        Args:
            backup_name: Название бэкапа (default: timestamp)
        
        Returns:
            True если успешно
        """
        try:
            if backup_name is None:
                backup_name = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            backup_dir = self.state_dir / "backups" / backup_name
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            import shutil
            for file in [self.positions_file, self.trades_file, self.stats_file]:
                if file.exists():
                    shutil.copy2(file, backup_dir / file.name)
            
            logger.info(f"✅ Backup created: {backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
            return False

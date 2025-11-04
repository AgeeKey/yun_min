"""
Portfolio Manager - управление портфелем из нескольких торговых пар

Ключевые возможности:
1. Мультисимвольная торговля (BTC/USDT, ETH/USDT, BNB/USDT и т.д.)
2. Динамическое распределение капитала на основе возможностей
3. Анализ корреляций для избежания перегрузки
4. Портфельные лимиты риска (макс 12% общий риск)
5. Балансировка позиций
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
import numpy as np


@dataclass
class SymbolAllocation:
    """Распределение капитала для одного символа"""
    symbol: str
    allocated_capital: float  # Выделенный капитал
    current_exposure: float  # Текущий exposure (стоимость позиции)
    available_capital: float  # Доступный капитал
    max_allocation_pct: float  # Макс процент от портфеля
    
    # Метрики
    pnl: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    
    def __post_init__(self):
        """Валидация после создания"""
        if self.allocated_capital < 0:
            raise ValueError("Allocated capital cannot be negative")
        if not 0 <= self.max_allocation_pct <= 1:
            raise ValueError("Max allocation must be between 0 and 1")


@dataclass
class PortfolioState:
    """Состояние портфеля"""
    total_capital: float
    available_capital: float
    total_exposure: float  # Сумма всех позиций
    total_pnl: float
    
    # Распределение по символам
    allocations: Dict[str, SymbolAllocation] = field(default_factory=dict)
    
    # Корреляционная матрица
    correlation_matrix: Optional[np.ndarray] = None
    
    # Лимиты
    max_portfolio_risk_pct: float = 0.12  # 12% макс риск
    max_symbols_active: int = 5  # Макс активных пар
    
    # Метрики
    portfolio_sharpe: float = 0.0
    portfolio_volatility: float = 0.0
    
    @property
    def total_risk_pct(self) -> float:
        """Общий риск портфеля (% от капитала)"""
        if self.total_capital == 0:
            return 0.0
        return self.total_exposure / self.total_capital
    
    @property
    def active_symbols(self) -> List[str]:
        """Активные символы (с позициями)"""
        return [
            symbol 
            for symbol, alloc in self.allocations.items() 
            if alloc.current_exposure > 0
        ]
    
    @property
    def utilization_pct(self) -> float:
        """Использование капитала (%)"""
        if self.total_capital == 0:
            return 0.0
        return (self.total_capital - self.available_capital) / self.total_capital


class PortfolioManager:
    """
    Менеджер портфеля для мультисимвольной торговли
    
    Отвечает за:
    - Распределение капитала между символами
    - Контроль корреляций
    - Ограничения риска на уровне портфеля
    - Ребалансировку
    """
    
    def __init__(
        self,
        total_capital: float,
        symbols: List[str],
        max_portfolio_risk_pct: float = 0.12,
        max_symbols_active: int = 5,
        correlation_threshold: float = 0.7
    ):
        """
        Args:
            total_capital: Общий капитал портфеля
            symbols: Список торговых пар (e.g., ['BTC/USDT', 'ETH/USDT'])
            max_portfolio_risk_pct: Макс риск портфеля (0.12 = 12%)
            max_symbols_active: Макс активных символов одновременно
            correlation_threshold: Порог корреляции (>0.7 = сильная)
        """
        if total_capital <= 0:
            raise ValueError("Total capital must be positive")
        if not symbols:
            raise ValueError("Must provide at least one symbol")
        
        self.symbols = symbols
        self.correlation_threshold = correlation_threshold
        
        # Равномерное начальное распределение
        allocation_per_symbol = total_capital / len(symbols)
        max_allocation_pct = 1.0 / len(symbols)  # Равные доли
        
        allocations = {
            symbol: SymbolAllocation(
                symbol=symbol,
                allocated_capital=allocation_per_symbol,
                current_exposure=0.0,
                available_capital=allocation_per_symbol,
                max_allocation_pct=max_allocation_pct
            )
            for symbol in symbols
        }
        
        self.state = PortfolioState(
            total_capital=total_capital,
            available_capital=total_capital,
            total_exposure=0.0,
            total_pnl=0.0,
            allocations=allocations,
            max_portfolio_risk_pct=max_portfolio_risk_pct,
            max_symbols_active=max_symbols_active
        )
        
        # История цен для корреляций
        self.price_history: Dict[str, List[float]] = {s: [] for s in symbols}
        
        logger.info(
            f"PortfolioManager initialized with ${total_capital:,.2f} "
            f"across {len(symbols)} symbols "
            f"(max risk: {max_portfolio_risk_pct*100}%, max active: {max_symbols_active})"
        )
    
    def can_open_position(self, symbol: str, position_value: float) -> tuple[bool, str]:
        """
        Проверить можно ли открыть позицию
        
        Args:
            symbol: Торговая пара
            position_value: Стоимость позиции
        
        Returns:
            (can_open, reason)
        """
        if symbol not in self.state.allocations:
            return False, f"Symbol {symbol} not in portfolio"
        
        alloc = self.state.allocations[symbol]
        
        # 1. Проверить доступный капитал символа
        if position_value > alloc.available_capital:
            return False, (
                f"Insufficient capital for {symbol}: "
                f"need ${position_value:.2f}, "
                f"available ${alloc.available_capital:.2f}"
            )
        
        # 2. Проверить лимит активных символов
        if alloc.current_exposure == 0:  # Новая позиция
            if len(self.state.active_symbols) >= self.state.max_symbols_active:
                return False, (
                    f"Max active symbols reached: "
                    f"{len(self.state.active_symbols)}/{self.state.max_symbols_active}"
                )
        
        # 3. Проверить общий риск портфеля
        new_exposure = self.state.total_exposure + position_value
        new_risk_pct = new_exposure / self.state.total_capital
        
        if new_risk_pct > self.state.max_portfolio_risk_pct:
            return False, (
                f"Portfolio risk limit exceeded: "
                f"{new_risk_pct*100:.1f}% > "
                f"{self.state.max_portfolio_risk_pct*100:.1f}%"
            )
        
        # 4. Проверить корреляции
        correlation_warning = self._check_correlation(symbol)
        if correlation_warning:
            return False, correlation_warning
        
        return True, "OK"
    
    def allocate_position(
        self, 
        symbol: str, 
        position_value: float
    ) -> bool:
        """
        Выделить капитал для позиции
        
        Args:
            symbol: Торговая пара
            position_value: Стоимость позиции
        
        Returns:
            True если успешно
        """
        can_open, reason = self.can_open_position(symbol, position_value)
        
        if not can_open:
            logger.warning(f"Cannot allocate position for {symbol}: {reason}")
            return False
        
        # Обновить аллокацию
        alloc = self.state.allocations[symbol]
        alloc.current_exposure += position_value
        alloc.available_capital -= position_value
        
        # Обновить состояние портфеля
        self.state.total_exposure += position_value
        self.state.available_capital -= position_value
        
        logger.info(
            f"Allocated ${position_value:.2f} to {symbol} "
            f"(exposure: ${alloc.current_exposure:.2f}, "
            f"available: ${alloc.available_capital:.2f})"
        )
        
        return True
    
    def release_position(
        self, 
        symbol: str, 
        position_value: float,
        pnl: float
    ) -> None:
        """
        Освободить капитал после закрытия позиции
        
        Args:
            symbol: Торговая пара
            position_value: Стоимость позиции
            pnl: Прибыль/убыток
        """
        if symbol not in self.state.allocations:
            logger.error(f"Symbol {symbol} not in portfolio")
            return
        
        alloc = self.state.allocations[symbol]
        
        # Вернуть капитал + P&L
        released_capital = position_value + pnl
        alloc.available_capital += released_capital
        alloc.current_exposure = max(0, alloc.current_exposure - position_value)
        alloc.pnl += pnl
        
        # Обновить портфель
        self.state.total_exposure = max(0, self.state.total_exposure - position_value)
        self.state.available_capital += released_capital
        self.state.total_pnl += pnl
        
        logger.info(
            f"Released ${position_value:.2f} from {symbol} "
            f"(P&L: ${pnl:+.2f}, "
            f"available: ${alloc.available_capital:.2f})"
        )
    
    def update_prices(self, prices: Dict[str, float]) -> None:
        """
        Обновить историю цен для корреляционного анализа
        
        Args:
            prices: {symbol: current_price}
        """
        for symbol, price in prices.items():
            if symbol in self.price_history:
                self.price_history[symbol].append(price)
                
                # Ограничить историю последними 100 свечами
                if len(self.price_history[symbol]) > 100:
                    self.price_history[symbol] = self.price_history[symbol][-100:]
        
        # Пересчитать корреляции если достаточно данных
        self._update_correlation_matrix()
    
    def _update_correlation_matrix(self) -> None:
        """Обновить матрицу корреляций"""
        # Нужно минимум 30 свечей для надёжной корреляции
        min_length = min(
            len(prices) 
            for prices in self.price_history.values()
        )
        
        if min_length < 30:
            return
        
        # Создать матрицу цен (символы × свечи)
        price_matrix = np.array([
            self.price_history[symbol][-min_length:]
            for symbol in self.symbols
        ])
        
        # Рассчитать корреляцию returns (изменений цен)
        returns = np.diff(price_matrix, axis=1) / price_matrix[:, :-1]
        
        if returns.shape[1] > 0:
            self.state.correlation_matrix = np.corrcoef(returns)
            logger.debug(
                f"Updated correlation matrix "
                f"(shape: {self.state.correlation_matrix.shape})"
            )
    
    def _check_correlation(self, symbol: str) -> Optional[str]:
        """
        Проверить корреляцию с активными позициями
        
        Returns:
            Warning message если корреляция слишком высокая, иначе None
        """
        if self.state.correlation_matrix is None:
            return None  # Недостаточно данных
        
        symbol_idx = self.symbols.index(symbol)
        
        # Проверить корреляцию с каждым активным символом
        for active_symbol in self.state.active_symbols:
            if active_symbol == symbol:
                continue
            
            active_idx = self.symbols.index(active_symbol)
            correlation = self.state.correlation_matrix[symbol_idx, active_idx]
            
            if abs(correlation) > self.correlation_threshold:
                return (
                    f"High correlation with {active_symbol}: "
                    f"{correlation:.2f} > {self.correlation_threshold}"
                )
        
        return None
    
    def rebalance(self, target_allocations: Dict[str, float]) -> None:
        """
        Ребалансировать портфель
        
        Args:
            target_allocations: {symbol: target_allocation_pct}
        """
        logger.info("Starting portfolio rebalancing...")
        
        for symbol, target_pct in target_allocations.items():
            if symbol not in self.state.allocations:
                continue
            
            alloc = self.state.allocations[symbol]
            target_capital = self.state.total_capital * target_pct
            
            # Обновить только allocated_capital, не трогая позиции
            diff = target_capital - alloc.allocated_capital
            alloc.allocated_capital = target_capital
            alloc.max_allocation_pct = target_pct
            
            logger.debug(
                f"Rebalanced {symbol}: "
                f"${alloc.allocated_capital:.2f} ({target_pct*100:.1f}%)"
            )
    
    def get_statistics(self) -> Dict:
        """Получить статистику портфеля"""
        return {
            'total_capital': self.state.total_capital,
            'available_capital': self.state.available_capital,
            'total_exposure': self.state.total_exposure,
            'total_pnl': self.state.total_pnl,
            'risk_pct': self.state.total_risk_pct * 100,
            'utilization_pct': self.state.utilization_pct * 100,
            'active_symbols': len(self.state.active_symbols),
            'max_symbols': self.state.max_symbols_active,
            'allocations': {
                symbol: {
                    'allocated': alloc.allocated_capital,
                    'exposure': alloc.current_exposure,
                    'available': alloc.available_capital,
                    'pnl': alloc.pnl
                }
                for symbol, alloc in self.state.allocations.items()
            }
        }
    
    def print_summary(self) -> None:
        """Вывести сводку портфеля"""
        print("\n" + "=" * 80)
        print("📊 PORTFOLIO SUMMARY")
        print("=" * 80)
        
        print(f"\n💰 Capital:")
        print(f"   Total: ${self.state.total_capital:,.2f}")
        print(f"   Available: ${self.state.available_capital:,.2f}")
        print(f"   Exposure: ${self.state.total_exposure:,.2f}")
        print(f"   P&L: ${self.state.total_pnl:+,.2f}")
        
        print(f"\n📈 Metrics:")
        print(f"   Risk: {self.state.total_risk_pct*100:.1f}% "
              f"(max: {self.state.max_portfolio_risk_pct*100:.1f}%)")
        print(f"   Utilization: {self.state.utilization_pct*100:.1f}%")
        print(f"   Active Symbols: {len(self.state.active_symbols)}/{self.state.max_symbols_active}")
        
        if self.state.active_symbols:
            print(f"\n🎯 Active Positions:")
            for symbol in self.state.active_symbols:
                alloc = self.state.allocations[symbol]
                print(
                    f"   {symbol}: ${alloc.current_exposure:,.2f} "
                    f"(P&L: ${alloc.pnl:+,.2f})"
                )
        
        print("=" * 80)

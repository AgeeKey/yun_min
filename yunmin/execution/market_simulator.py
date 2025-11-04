"""
Market Simulator - точная симуляция реального рынка для DRY RUN режима

Реализует:
1. Комиссии Binance: 0.1% maker, 0.1% taker
2. Проскальзывание (slippage): 0.01-0.05% в зависимости от волатильности
3. Market impact: влияние больших ордеров на цену
4. Синхронизация с реальными ценами

Формулы:
- Комиссия: order_value * 0.001 (0.1%)
- Slippage: базовый 0.02% + volatility_factor
- Market impact: order_size / daily_volume * price_impact_factor
"""

import random
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger


@dataclass
class OrderExecution:
    """Результат исполнения ордера"""
    symbol: str
    side: str  # 'buy' или 'sell'
    requested_price: float
    executed_price: float
    amount: float
    total_cost: float
    commission: float
    slippage: float
    slippage_pct: float
    timestamp: datetime


class MarketSimulator:
    """
    Симулятор рыночных условий для DRY RUN режима
    
    Максимально реалистичная симуляция торговли:
    - Комиссии как на Binance
    - Проскальзывание как в реальности
    - Market impact для больших объёмов
    - Синхронизация с реальными ценами
    """
    
    # Константы Binance
    MAKER_FEE = 0.001  # 0.1%
    TAKER_FEE = 0.001  # 0.1%
    
    # Проскальзывание
    BASE_SLIPPAGE = 0.0002  # 0.02% базовое
    MAX_SLIPPAGE = 0.0005   # 0.05% максимальное
    
    # Market impact
    MARKET_IMPACT_FACTOR = 0.00001  # 0.001% на каждый 1% дневного объёма
    
    def __init__(self, exchange=None):
        """
        Инициализация симулятора
        
        Args:
            exchange: Exchange adapter для получения реальных данных (опционально)
        """
        self.exchange = exchange
        self.execution_history: list[OrderExecution] = []
        
        # Кэш волатильности (обновляется раз в минуту)
        self.volatility_cache: Dict[str, Tuple[float, datetime]] = {}
        self.cache_ttl = timedelta(minutes=1)
        
        logger.info("MarketSimulator initialized (Binance fees: 0.1% maker/taker)")
    
    def calculate_commission(self, order_value: float, is_maker: bool = False) -> float:
        """
        Рассчитать комиссию за ордер
        
        Args:
            order_value: Стоимость ордера (price * amount)
            is_maker: True если maker order, False если taker
        
        Returns:
            Комиссия в USDT
        """
        fee_rate = self.MAKER_FEE if is_maker else self.TAKER_FEE
        commission = order_value * fee_rate
        
        return commission
    
    def get_volatility(self, symbol: str) -> float:
        """
        Получить текущую волатильность символа
        
        Используется для расчёта проскальзывания.
        Волатильность = std(price changes) за последние 24ч
        
        Args:
            symbol: Торговая пара (BTC/USDT)
        
        Returns:
            Volatility factor (0.0 - 1.0+)
        """
        # Проверить кэш
        if symbol in self.volatility_cache:
            vol, timestamp = self.volatility_cache[symbol]
            if timestamp and datetime.now() - timestamp < self.cache_ttl:
                return vol
        
        # Если нет exchange - использовать средние значения
        if not self.exchange:
            # BTC: средняя волатильность ~2%/день
            # ETH: средняя волатильность ~3%/день
            # BNB: средняя волатильность ~4%/день
            default_vol = {
                'BTC/USDT': 0.02,
                'ETH/USDT': 0.03,
                'BNB/USDT': 0.04
            }
            vol = default_vol.get(symbol, 0.025)
            self.volatility_cache[symbol] = (vol, datetime.now())
            return vol
        
        try:
            # Получить данные за 24 часа
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=24)
            
            if not ohlcv or len(ohlcv) < 2:
                vol = 0.02  # Default
            else:
                # Рассчитать volatility как std процентных изменений
                prices = [candle[4] for candle in ohlcv]  # Close prices
                changes = []
                for i in range(1, len(prices)):
                    change_pct = abs(prices[i] - prices[i-1]) / prices[i-1]
                    changes.append(change_pct)
                
                # Стандартное отклонение
                if changes:
                    mean = sum(changes) / len(changes)
                    variance = sum((x - mean) ** 2 for x in changes) / len(changes)
                    vol = variance ** 0.5
                else:
                    vol = 0.02
            
            # Кэшировать
            self.volatility_cache[symbol] = (vol, datetime.now())
            return vol
            
        except Exception as e:
            logger.warning(f"Failed to calculate volatility for {symbol}: {e}")
            return 0.02  # Default volatility
    
    def calculate_slippage(
        self,
        symbol: str,
        side: str,
        price: float,
        amount: float
    ) -> Tuple[float, float]:
        """
        Рассчитать проскальзывание
        
        Проскальзывание зависит от:
        1. Волатильности рынка (выше волатильность = больше slippage)
        2. Размера ордера относительно объёма
        3. Случайный фактор (имитация реального рынка)
        
        Args:
            symbol: Торговая пара
            side: 'buy' или 'sell'
            price: Запрошенная цена
            amount: Размер ордера
        
        Returns:
            (slippage_price, slippage_pct)
            slippage_price: Цена с учётом проскальзывания
            slippage_pct: Процент проскальзывания
        """
        # Получить волатильность
        volatility = self.get_volatility(symbol)
        
        # Базовое проскальзывание + фактор волатильности
        vol_factor = min(volatility * 2, 1.0)  # Макс 100%
        base_slip = self.BASE_SLIPPAGE * (1 + vol_factor)
        
        # Случайный компонент (±50% от базового)
        random_factor = random.uniform(0.5, 1.5)
        slippage_pct = base_slip * random_factor
        
        # Ограничить максимумом
        slippage_pct = min(slippage_pct, self.MAX_SLIPPAGE)
        
        # Применить к цене
        if side == 'buy':
            # При покупке цена ВЫШЕ (платим больше)
            slippage_price = price * (1 + slippage_pct)
        else:
            # При продаже цена НИЖЕ (получаем меньше)
            slippage_price = price * (1 - slippage_pct)
        
        return slippage_price, slippage_pct
    
    def calculate_market_impact(
        self,
        symbol: str,
        amount: float,
        price: float
    ) -> float:
        """
        Рассчитать market impact (влияние большого ордера на цену)
        
        Большие ордера двигают рынок:
        - Большая покупка -> цена растёт
        - Большая продажа -> цена падает
        
        Args:
            symbol: Торговая пара
            amount: Размер ордера
            price: Текущая цена
        
        Returns:
            Price impact (в процентах)
        """
        # Если нет данных о volume - не применять impact
        if not self.exchange:
            return 0.0
        
        try:
            # Получить 24h volume
            ticker = self.exchange.fetch_ticker(symbol)
            volume_24h = ticker.get('quoteVolume', 0)  # В USDT
            
            if volume_24h == 0:
                return 0.0
            
            # Размер ордера в USDT
            order_value = amount * price
            
            # Доля от дневного объёма
            volume_pct = order_value / volume_24h
            
            # Impact = доля * impact_factor
            impact = volume_pct * self.MARKET_IMPACT_FACTOR
            
            # Ограничить максимумом 0.5%
            impact = min(impact, 0.005)
            
            return impact
            
        except Exception as e:
            logger.warning(f"Failed to calculate market impact for {symbol}: {e}")
            return 0.0
    
    def execute_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        current_price: float,
        is_maker: bool = False
    ) -> OrderExecution:
        """
        Исполнить рыночный ордер с реалистичной симуляцией
        
        Применяет:
        1. Проскальзывание (slippage)
        2. Market impact
        3. Комиссии
        
        Args:
            symbol: Торговая пара
            side: 'buy' или 'sell'
            amount: Количество базовой валюты
            current_price: Текущая рыночная цена
            is_maker: True если limit order (maker), False если market (taker)
        
        Returns:
            OrderExecution с деталями исполнения
        """
        # 1. Рассчитать проскальзывание
        slippage_price, slippage_pct = self.calculate_slippage(
            symbol, side, current_price, amount
        )
        
        # 2. Рассчитать market impact
        impact = self.calculate_market_impact(symbol, amount, current_price)
        
        # Применить impact к цене
        if side == 'buy':
            # Покупка двигает цену вверх
            final_price = slippage_price * (1 + impact)
        else:
            # Продажа двигает цену вниз
            final_price = slippage_price * (1 - impact)
        
        # 3. Рассчитать стоимость ордера
        total_cost = amount * final_price
        
        # 4. Рассчитать комиссию
        commission = self.calculate_commission(total_cost, is_maker)
        
        # Логировать детали
        slippage_amount = abs(final_price - current_price)
        logger.debug(
            f"Market order {side} {amount:.6f} {symbol}: "
            f"Requested ${current_price:.2f}, "
            f"Executed ${final_price:.2f} "
            f"(slippage {slippage_pct*100:.3f}%, impact {impact*100:.3f}%), "
            f"Fee ${commission:.2f}"
        )
        
        # Создать результат
        execution = OrderExecution(
            symbol=symbol,
            side=side,
            requested_price=current_price,
            executed_price=final_price,
            amount=amount,
            total_cost=total_cost,
            commission=commission,
            slippage=slippage_amount,
            slippage_pct=slippage_pct + impact,  # Общее отклонение от цены
            timestamp=datetime.now()
        )
        
        # Сохранить в историю
        self.execution_history.append(execution)
        
        return execution
    
    def get_real_price(self, symbol: str) -> Optional[float]:
        """
        Получить реальную рыночную цену
        
        Args:
            symbol: Торговая пара
        
        Returns:
            Текущая цена или None если нет данных
        """
        if not self.exchange:
            return None
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker.get('last') or ticker.get('close')
        except Exception as e:
            logger.error(f"Failed to fetch real price for {symbol}: {e}")
            return None
    
    def get_statistics(self) -> Dict:
        """
        Получить статистику исполнения ордеров
        
        Returns:
            Словарь со статистикой
        """
        if not self.execution_history:
            return {
                'total_orders': 0,
                'total_commission': 0.0,
                'avg_slippage_pct': 0.0,
                'max_slippage_pct': 0.0,
                'total_cost': 0.0
            }
        
        total_commission = sum(ex.commission for ex in self.execution_history)
        slippages = [ex.slippage_pct for ex in self.execution_history]
        total_cost = sum(ex.total_cost for ex in self.execution_history)
        
        return {
            'total_orders': len(self.execution_history),
            'total_commission': total_commission,
            'avg_slippage_pct': sum(slippages) / len(slippages) * 100,
            'max_slippage_pct': max(slippages) * 100,
            'total_cost': total_cost
        }
    
    def reset(self):
        """Сбросить историю исполнения"""
        self.execution_history.clear()
        logger.info("MarketSimulator history reset")

"""
BOSS ULTIMATE DECISION: AI-Driven Trading Strategy

ПРОБЛЕМА:
- Все классические стратегии (EMA, RSI, MACD) проваливаются
- 2024 данные: -9% до -21%
- 2025 данные: -42% до -45% (КАТАСТРОФА!)

ROOT CAUSE:
- Рынок 2025 слишком эффективен
- Простые индикаторы не работают  
- BTC: $103k → $126k (+22% бычий тренд)
- Нужна АДАПТИВНАЯ стратегия

РЕШЕНИЕ: AI-Generated Signals
- Используем Groq AI (Llama 3.3 70B)
- AI анализирует текущий рынок в реальном времени
- Генерирует BUY/SELL/HOLD сигналы
- Адаптируется к меняющимся условиям

ПРЕИМУЩЕСТВА:
✅ Нет фиксированных правил (адаптивно)
✅ AI видит паттерны, которые не видят индикаторы
✅ Контекстное понимание рынка
✅ FREE (14,400 запросов/день)

BACKTEST PLAN:
1. Пройти по историческим данным (30 дней)
2. На каждой свече: дать AI последние N свечей
3. AI решает: BUY/SELL/HOLD
4. Симулировать сделки
5. Сравнить с индикаторными стратегиями
"""

import os
import sys
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from groq import Groq
from loguru import logger
from dotenv import load_dotenv

# Load environment
load_dotenv()
sys.path.insert(0, 'f:/AgeeKey/yun_min')

from run_backtest_v3_realdata import load_binance_historical_data, resample_to_timeframe

class AITradingStrategy:
    """
    AI-Driven Trading Strategy using Groq Llama 3.3 70B
    
    На каждой свече AI анализирует:
    - Последние N свечей (price action)
    - Текущие индикаторы (RSI, MACD, BB)
    - Market context
    
    Генерирует сигнал: BUY, SELL, HOLD
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        lookback_candles: int = 20,  # Сколько свечей давать AI
        temperature: float = 0.1     # Low temp для консистентности
    ):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.lookback_candles = lookback_candles
        self.temperature = temperature
        
        logger.info(f"🤖 AI Trading Strategy initialized")
        logger.info(f"   Model: {model}")
        logger.info(f"   Lookback: {lookback_candles} candles")
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Рассчитываем индикаторы для AI"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        return df
        
    def format_market_context(self, df_slice: pd.DataFrame, current_capital: float) -> str:
        """Форматируем данные для AI"""
        last = df_slice.iloc[-1]
        
        # Price action (последние свечи)
        price_action = []
        for idx, row in df_slice.tail(10).iterrows():
            candle_type = "🟢" if row['close'] > row['open'] else "🔴"
            price_action.append(
                f"{candle_type} {row['timestamp']}: "
                f"O:{row['open']:.2f} H:{row['high']:.2f} "
                f"L:{row['low']:.2f} C:{row['close']:.2f}"
            )
        
        # Indicators
        indicators = f"""
RSI: {last['rsi']:.2f}
MACD: {last['macd']:.4f}
MACD Signal: {last['macd_signal']:.4f}
BB Upper: {last['bb_upper']:.2f}
BB Middle: {last['bb_middle']:.2f}
BB Lower: {last['bb_lower']:.2f}
Current Price: {last['close']:.2f}
"""
        
        # Price change
        first_price = df_slice.iloc[0]['close']
        last_price = last['close']
        change_pct = ((last_price - first_price) / first_price) * 100
        
        context = f"""
BITCOIN MARKET ANALYSIS REQUEST

TIMEFRAME: 5-minute candles
PERIOD: Last {len(df_slice)} candles

CURRENT SITUATION:
{indicators}

RECENT PRICE ACTION (Last 10 candles):
{chr(10).join(price_action)}

TREND:
- Period change: {change_pct:+.2f}%
- Price: ${first_price:.2f} → ${last_price:.2f}

TRADING CONTEXT:
- Available Capital: ${current_capital:.2f}
- Commission: 0.1% per trade
- Slippage: 0.05%

YOUR TASK:
Analyze the market and provide a CLEAR trading signal.

RESPOND WITH EXACTLY ONE OF:
1. BUY - If you see strong bullish opportunity
2. SELL - If you see strong bearish opportunity  
3. HOLD - If market is unclear or risky

IMPORTANT:
- Be conservative (prefer HOLD over risky trades)
- Consider trend, momentum, support/resistance
- Avoid buying overbought or selling oversold
- Factor in commission costs

RESPONSE FORMAT (JSON):
{{
    "signal": "BUY" or "SELL" or "HOLD",
    "confidence": 0-100,
    "reason": "Brief explanation (max 50 words)"
}}

RESPOND WITH JSON ONLY (no markdown, no code blocks):
"""
        return context
        
    def get_ai_signal(self, df_slice: pd.DataFrame, current_capital: float) -> Dict:
        """Получаем сигнал от AI"""
        try:
            prompt = self.format_market_context(df_slice, current_capital)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert crypto trader. Analyze market data and provide trading signals. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=200
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Remove markdown if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            signal = json.loads(content)
            
            # Validate
            if signal['signal'] not in ['BUY', 'SELL', 'HOLD']:
                logger.warning(f"Invalid signal: {signal['signal']}, defaulting to HOLD")
                signal['signal'] = 'HOLD'
                
            return signal
            
        except Exception as e:
            logger.error(f"AI signal generation failed: {e}")
            # Default to HOLD on error
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'reason': f'Error: {str(e)[:30]}'
            }
            
    def backtest(
        self,
        df: pd.DataFrame,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005
    ) -> Dict:
        """
        Backt AI стратегии
        
        На каждой свече:
        1. Даем AI последние N свечей
        2. AI генерирует сигнал
        3. Выполняем сделку (если BUY/SELL)
        """
        logger.info(f"\n🤖 Starting AI Strategy Backtest")
        logger.info(f"   Period: {df.iloc[0]['timestamp']} → {df.iloc[-1]['timestamp']}")
        logger.info(f"   Candles: {len(df)}")
        logger.info(f"   Initial Capital: ${initial_capital:,.2f}")
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        # Drop NaN rows (from indicator calculation)
        df = df.dropna().reset_index(drop=True)
        
        # Trading state
        capital = initial_capital
        position = None  # 'LONG' or 'SHORT' or None
        entry_price = None
        trades = []
        ai_calls = 0
        
        # Start after lookback period
        for i in range(self.lookback_candles, len(df)):
            current_row = df.iloc[i]
            current_price = current_row['close']
            
            # Get market context (last N candles)
            df_slice = df.iloc[i - self.lookback_candles:i + 1]
            
            # Exit existing position first
            if position is not None:
                # Simple exit rule: opposite signal or max holding period
                # For now: hold until next signal (AI will decide)
                pass
            
            # Get AI signal (only if no position)
            if position is None:
                ai_signal = self.get_ai_signal(df_slice, capital)
                ai_calls += 1
                
                signal_type = ai_signal['signal']
                confidence = ai_signal.get('confidence', 0)
                reason = ai_signal.get('reason', '')
                
                logger.debug(f"[{current_row['timestamp']}] AI: {signal_type} "
                           f"(confidence: {confidence}%) - {reason}")
                
                # Execute trade based on signal
                if signal_type == 'BUY' and capital > 0:
                    # Enter LONG
                    position = 'LONG'
                    entry_price = current_price * (1 + slippage)  # Buy slippage
                    position_size = (capital * 0.9) / entry_price  # Use 90% capital
                    
                    # Commission
                    commission_paid = (position_size * entry_price) * commission
                    capital -= commission_paid
                    
                    logger.info(f"🟢 BUY @ ${entry_price:.2f} | "
                               f"Size: {position_size:.6f} BTC | "
                               f"Reason: {reason}")
                    
                elif signal_type == 'SELL' and capital > 0:
                    # Enter SHORT
                    position = 'SHORT'
                    entry_price = current_price * (1 - slippage)  # Sell slippage
                    position_size = (capital * 0.9) / entry_price
                    
                    commission_paid = (position_size * entry_price) * commission
                    capital -= commission_paid
                    
                    logger.info(f"🔴 SELL @ ${entry_price:.2f} | "
                               f"Size: {position_size:.6f} BTC | "
                               f"Reason: {reason}")
                               
            # Check exit conditions (if in position)
            elif position is not None:
                # Get AI signal for exit decision
                ai_signal = self.get_ai_signal(df_slice, capital)
                ai_calls += 1
                
                should_exit = False
                exit_reason = ""
                
                # Exit on opposite signal
                if position == 'LONG' and ai_signal['signal'] == 'SELL':
                    should_exit = True
                    exit_reason = f"AI Exit Signal: {ai_signal.get('reason', '')}"
                elif position == 'SHORT' and ai_signal['signal'] == 'BUY':
                    should_exit = True
                    exit_reason = f"AI Exit Signal: {ai_signal.get('reason', '')}"
                # Exit on HOLD with low confidence (uncertain market)
                elif ai_signal['signal'] == 'HOLD' and ai_signal.get('confidence', 0) < 30:
                    should_exit = True
                    exit_reason = "AI: Market uncertain, exit"
                    
                if should_exit:
                    exit_price = current_price * (1 - slippage if position == 'LONG' else 1 + slippage)
                    
                    # Calculate P&L
                    if position == 'LONG':
                        pnl = (exit_price - entry_price) * position_size
                    else:  # SHORT
                        pnl = (entry_price - exit_price) * position_size
                        
                    # Commission on exit
                    commission_paid = (position_size * exit_price) * commission
                    capital -= commission_paid
                    
                    # Update capital
                    capital += pnl
                    
                    pnl_pct = (pnl / (entry_price * position_size)) * 100
                    
                    trades.append({
                        'entry_time': df.iloc[i - 1]['timestamp'],
                        'exit_time': current_row['timestamp'],
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'position_type': position,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'exit_reason': exit_reason
                    })
                    
                    logger.info(f"❌ EXIT {position} @ ${exit_price:.2f} | "
                               f"P&L: ${pnl:.2f} ({pnl_pct:+.2f}%) | "
                               f"{exit_reason} | Capital: ${capital:.2f}")
                    
                    # Reset
                    position = None
                    entry_price = None
                    position_size = None
                    
        # Calculate metrics
        if not trades:
            logger.warning("⚠️  No trades executed!")
            return {
                'total_return': 0.0,
                'total_trades': 0,
                'ai_calls': ai_calls,
            }
            
        total_return = ((capital - initial_capital) / initial_capital) * 100
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0
        
        avg_win = sum(t['pnl_pct'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl_pct'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        total_profit = sum(t['pnl'] for t in winning_trades)
        total_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        # Max Drawdown
        cumulative_returns = []
        cum_capital = initial_capital
        for trade in trades:
            cum_capital += trade['pnl']
            cumulative_returns.append(cum_capital)
        
        max_dd = 0
        peak = cumulative_returns[0]
        for value in cumulative_returns:
            if value > peak:
                peak = value
            dd = ((peak - value) / peak) * 100
            if dd > max_dd:
                max_dd = dd
        
        return {
            'total_return': total_return,
            'final_capital': capital,
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd,
            'ai_calls': ai_calls,
            'trades': trades
        }


def main():
    logger.info("="*80)
    logger.info("🤖 BOSS ULTIMATE: AI-DRIVEN TRADING STRATEGY")
    logger.info("="*80)
    logger.info("All indicator-based strategies failed:")
    logger.info("  RSI V2 (2025): -45.55%")
    logger.info("  Trend Breakout (2025): -42.12%")
    logger.info("")
    logger.info("Testing: AI-Generated Signals (Groq Llama 3.3 70B)")
    logger.info("="*80)
    
    # Load data
    data_path = Path("data/binance_historical/BTCUSDT_historical_2025-10-01_to_30days.csv")
    df = load_binance_historical_data(str(data_path))
    df_5m = resample_to_timeframe(df, '5T')
    
    # Initialize AI strategy
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("❌ GROQ_API_KEY not found in .env!")
        return
        
    strategy = AITradingStrategy(
        api_key=api_key,
        model="llama-3.3-70b-versatile",
        lookback_candles=20,
        temperature=0.1
    )
    
    # Run backtest
    # NOTE: Full 30-day backtest would use ~8000 AI calls (expensive)
    # Test on first 7 days only (1400 AI calls, within free limit)
    logger.warning("⚠️  Testing on FIRST 7 DAYS only (to stay within free API limits)")
    df_test = df_5m.head(2016)  # 7 days * 288 candles/day
    
    results = strategy.backtest(df_test, initial_capital=10000.0)
    
    # Print results
    logger.info("\n" + "="*80)
    logger.info("📊 AI STRATEGY RESULTS (7 DAYS)")
    logger.info("="*80)
    logger.info(f"💰 Total Return: {results['total_return']:+.2f}%")
    logger.info(f"💵 Final Capital: ${results['final_capital']:,.2f}")
    logger.info(f"🎯 Win Rate: {results['win_rate']:.2f}%")
    logger.info(f"📈 Profit Factor: {results['profit_factor']:.2f}")
    logger.info(f"📊 Total Trades: {results['total_trades']}")
    logger.info(f"   ✅ Winning: {results['winning_trades']}")
    logger.info(f"   ❌ Losing: {results['losing_trades']}")
    logger.info(f"📊 Avg Win: {results['avg_win']:+.2f}%")
    logger.info(f"📊 Avg Loss: {results['avg_loss']:+.2f}%")
    logger.info(f"📉 Max Drawdown: {results['max_drawdown']:.2f}%")
    logger.info(f"🤖 AI Calls Made: {results['ai_calls']}")
    
    # Comparison
    logger.info("\n" + "="*80)
    logger.info("🏆 ULTIMATE COMPARISON (2025 Data)")
    logger.info("="*80)
    logger.info("Strategy              Return       Win Rate     Max DD")
    logger.info("-" * 80)
    logger.info(f"RSI V2                -45.55%      43.68%       45.79%")
    logger.info(f"Trend Breakout        -42.12%      27.03%       N/A")
    logger.info(f"AI-Driven (7d)        {results['total_return']:+.2f}%      {results['win_rate']:.2f}%       {results['max_drawdown']:.2f}%")
    
    # Verdict
    logger.info("\n" + "="*80)
    logger.info("🎯 BOSS VERDICT")
    logger.info("="*80)
    if results['total_return'] > 0:
        logger.success(f"✅ AI Strategy PROFITABLE: {results['total_return']:+.2f}%")
        logger.info("Ready for extended testing and paper trading!")
    elif results['total_return'] > -10:
        logger.warning(f"🟡 AI Strategy Close: {results['total_return']:+.2f}%")
        logger.info("Needs optimization but shows promise!")
    else:
        logger.error(f"❌ AI Strategy Failed: {results['total_return']:+.2f}%")
        logger.info("AI signals not better than indicators.")
    logger.info("="*80)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"backtest_ai_strategy_{timestamp}.json"
    
    # Convert trades for JSON
    results_json = results.copy()
    results_json['trades'] = [
        {
            'entry_time': str(t['entry_time']),
            'exit_time': str(t['exit_time']),
            'entry_price': t['entry_price'],
            'exit_price': t['exit_price'],
            'position_type': t['position_type'],
            'pnl': t['pnl'],
            'pnl_pct': t['pnl_pct'],
            'exit_reason': t['exit_reason']
        }
        for t in results['trades']
    ]
    
    with open(result_file, 'w') as f:
        json.dump(results_json, f, indent=2)
    
    logger.info(f"\n💾 Results saved: {result_file}")


if __name__ == "__main__":
    main()

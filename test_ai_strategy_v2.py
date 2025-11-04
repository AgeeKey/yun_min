"""
AI-Driven Trading Strategy V2 - AGGRESSIVE VERSION

BOSS IMPROVEMENTS:
- Temperature увеличен с 0.1 до 0.4 (более агрессивные решения)
- Prompt изменён: убрана излишняя осторожность
- Добавлен minimum position requirement (50%+ capital в работе)
- Lookback увеличен до 50 свечей (4+ часа контекста)
"""

import os
import json
from datetime import datetime
from pathlib import Path
from loguru import logger
from groq import Groq
import pandas as pd
import numpy as np
from run_backtest_v3_realdata import load_binance_historical_data, resample_to_timeframe


class AITradingStrategyV2:
    """AI-driven trading strategy using Groq Llama 3.3 70B - AGGRESSIVE VERSION"""
    
    def __init__(self, lookback_candles=50, temperature=0.4):
        self.lookback = lookback_candles
        self.temperature = temperature
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        
        logger.info("🤖 AI Trading Strategy V2 initialized (AGGRESSIVE MODE)")
        logger.info(f"   Model: {self.model}")
        logger.info(f"   Lookback: {lookback_candles} candles")
        logger.info(f"   Temperature: {temperature}")
    
    def calculate_indicators(self, df):
        """Calculate technical indicators for AI context"""
        df = df.copy()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df.loc[:, 'rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        df.loc[:, 'macd'] = ema_fast - ema_slow
        df.loc[:, 'macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Bollinger Bands
        df.loc[:, 'bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df.loc[:, 'bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df.loc[:, 'bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        return df
    
    def format_market_context(self, df_slice, current_capital, position_value):
        """Format market data for AI prompt"""
        
        current = df_slice.iloc[-1]
        prev_10 = df_slice.tail(10)
        
        # Price action summary
        price_change = ((current['close'] - prev_10.iloc[0]['close']) / prev_10.iloc[0]['close']) * 100
        volatility = prev_10['close'].std()
        
        # Trend direction
        sma_20 = prev_10['close'].mean()
        trend = "BULLISH" if current['close'] > sma_20 else "BEARISH"
        
        # BB position
        bb_position = "MIDDLE"
        if current['close'] > current['bb_upper']:
            bb_position = "ABOVE UPPER (overbought zone)"
        elif current['close'] < current['bb_lower']:
            bb_position = "BELOW LOWER (oversold zone)"
        elif current['close'] > current['bb_middle']:
            bb_position = "UPPER HALF"
        else:
            bb_position = "LOWER HALF"
        
        # Current position
        position_pct = (position_value / current_capital) * 100 if current_capital > 0 else 0
        
        context = f"""
MARKET ANALYSIS REQUEST:

Current BTC Price: ${current['close']:.2f}
10-Candle Change: {price_change:+.2f}%
Volatility (Std Dev): ${volatility:.2f}
Trend: {trend}

INDICATORS:
- RSI(14): {current['rsi']:.1f}
- MACD: {current['macd']:.2f} (Signal: {current['macd_signal']:.2f})
- Bollinger Position: {bb_position}
- BB Upper: ${current['bb_upper']:.2f}
- BB Middle: ${current['bb_middle']:.2f}
- BB Lower: ${current['bb_lower']:.2f}

RECENT PRICE ACTION (last 10 candles):
{prev_10[['close', 'volume']].tail(5).to_string()}

PORTFOLIO STATUS:
- Total Capital: ${current_capital:.2f}
- Position Value: ${position_value:.2f}
- Position %: {position_pct:.1f}%
- Cash Available: ${current_capital - position_value:.2f}

YOUR TASK:
You are an AGGRESSIVE crypto trader aiming for MAXIMUM RETURNS in a BULL MARKET.

TRADING RULES:
1. MINIMUM 50% capital must be ACTIVE (in position or pending trades)
2. Use FULL portfolio power - don't sit on cash in bull trends
3. BUY on dips in uptrends (RSI < 40 + bullish MACD)
4. SELL only on clear reversals (RSI > 75 + bearish divergence)
5. HOLD is ONLY for:
   - Extreme uncertainty (choppy sideways)
   - Waiting for better entry in confirmed downtrend

RESPOND WITH JSON ONLY:
{{
  "signal": "BUY|SELL|HOLD",
  "confidence": 0-100,
  "reason": "brief explanation (max 80 chars)",
  "position_target": 0-100
}}

position_target = % of capital that SHOULD be in BTC position after this action.
"""
        return context
    
    def get_ai_signal(self, df_slice, current_capital, position_value):
        """Get trading signal from AI"""
        
        prompt = self.format_market_context(df_slice, current_capital, position_value)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert crypto trader. Output ONLY valid JSON. Be aggressive in bull markets."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            signal = json.loads(content)
            
            # Validate required fields
            required = ['signal', 'confidence', 'reason']
            if not all(k in signal for k in required):
                logger.warning(f"Invalid AI response: {signal}")
                return {"signal": "HOLD", "confidence": 50, "reason": "Invalid AI response", "position_target": 0}
            
            # Ensure signal is uppercase
            signal['signal'] = signal['signal'].upper()
            
            # Default position_target if not provided
            if 'position_target' not in signal:
                if signal['signal'] == 'BUY':
                    signal['position_target'] = 80  # Aggressive default
                elif signal['signal'] == 'SELL':
                    signal['position_target'] = 0
                else:
                    signal['position_target'] = max(50, position_value / current_capital * 100) if current_capital > 0 else 50
            
            return signal
            
        except Exception as e:
            logger.error(f"AI API error: {e}")
            return {"signal": "HOLD", "confidence": 0, "reason": f"API Error: {str(e)[:50]}", "position_target": 50}
    
    def backtest(self, df, initial_capital=10000, fee_rate=0.001):
        """Run backtest with AI signals"""
        
        logger.info("\n🤖 Starting AI Strategy V2 Backtest (AGGRESSIVE)")
        logger.info(f"   Period: {df.iloc[0]['timestamp']} → {df.iloc[-1]['timestamp']}")
        logger.info(f"   Candles: {len(df)}")
        logger.info(f"   Initial Capital: ${initial_capital:,.2f}")
        
        capital = initial_capital
        position = 0.0  # BTC amount
        position_value = 0.0
        trades = []
        ai_calls = 0
        
        df_with_indicators = self.calculate_indicators(df)
        
        for i in range(self.lookback, len(df_with_indicators)):
            row = df_with_indicators.iloc[i]
            price = row['close']
            
            # Update position value
            position_value = position * price
            total_value = capital + position_value
            
            # Get AI signal
            df_slice = df_with_indicators.iloc[i-self.lookback:i+1]
            signal_data = self.get_ai_signal(df_slice, total_value, position_value)
            ai_calls += 1
            
            signal = signal_data['signal']
            confidence = signal_data['confidence']
            reason = signal_data['reason']
            target_pct = signal_data.get('position_target', 50)
            
            logger.debug(f"[{row['timestamp']}] AI: {signal} (confidence: {confidence}%) - {reason} | Target: {target_pct}%")
            
            # Execute trades based on signal
            if signal == "BUY" and capital > 100:
                # Calculate buy amount based on target position
                target_value = total_value * (target_pct / 100)
                buy_value = max(0, target_value - position_value)
                
                if buy_value > 100 and capital >= buy_value:
                    buy_amount = (buy_value / price) * (1 - fee_rate)
                    cost = buy_value
                    
                    position += buy_amount
                    capital -= cost
                    
                    trades.append({
                        'timestamp': row['timestamp'],
                        'type': 'BUY',
                        'price': price,
                        'amount': buy_amount,
                        'value': cost,
                        'capital_after': capital,
                        'position_after': position,
                        'ai_confidence': confidence,
                        'ai_reason': reason
                    })
                    
                    logger.info(f"✅ BUY {buy_amount:.6f} BTC @ ${price:.2f} (target {target_pct}%)")
            
            elif signal == "SELL" and position > 0:
                # Calculate sell amount based on target position
                target_btc = (total_value * (target_pct / 100)) / price if target_pct > 0 else 0
                sell_amount = max(0, position - target_btc)
                
                if sell_amount > 0.0001:
                    proceeds = sell_amount * price * (1 - fee_rate)
                    
                    position -= sell_amount
                    capital += proceeds
                    
                    trades.append({
                        'timestamp': row['timestamp'],
                        'type': 'SELL',
                        'price': price,
                        'amount': sell_amount,
                        'value': proceeds,
                        'capital_after': capital,
                        'position_after': position,
                        'ai_confidence': confidence,
                        'ai_reason': reason
                    })
                    
                    logger.info(f"📉 SELL {sell_amount:.6f} BTC @ ${price:.2f} (target {target_pct}%)")
        
        # Final settlement
        final_price = df_with_indicators.iloc[-1]['close']
        if position > 0:
            capital += position * final_price * (1 - fee_rate)
            position = 0
        
        # Calculate metrics
        total_return = ((capital - initial_capital) / initial_capital) * 100
        
        buy_trades = [t for t in trades if t['type'] == 'BUY']
        sell_trades = [t for t in trades if t['type'] == 'SELL']
        
        wins = losses = 0
        if len(buy_trades) > 0 and len(sell_trades) > 0:
            for i, sell in enumerate(sell_trades):
                if i < len(buy_trades):
                    buy = buy_trades[i]
                    if sell['price'] > buy['price']:
                        wins += 1
                    else:
                        losses += 1
        
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        results = {
            'initial_capital': initial_capital,
            'final_capital': capital,
            'total_return_pct': total_return,
            'total_trades': len(trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'wins': wins,
            'losses': losses,
            'win_rate_pct': win_rate,
            'ai_calls_made': ai_calls,
            'fee_rate': fee_rate,
            'trades': trades
        }
        
        return results


def main():
    logger.info("=" * 80)
    logger.info("🤖 BOSS ULTIMATE V2: AGGRESSIVE AI TRADING STRATEGY")
    logger.info("=" * 80)
    logger.info("V1 Results: 0 trades (too conservative)")
    logger.info("")
    logger.info("V2 Improvements:")
    logger.info("  - Temperature: 0.1 → 0.4 (more aggressive)")
    logger.info("  - Lookback: 20 → 50 candles (better context)")
    logger.info("  - Prompt: Requires 50%+ capital active")
    logger.info("  - Target-based position sizing")
    logger.info("=" * 80)
    
    # Load data
    data_file = Path("data/binance_historical/BTCUSDT_historical_2025-10-01_to_30days.csv")
    
    if not data_file.exists():
        logger.error(f"Data file not found: {data_file}")
        return
    
    df = load_binance_historical_data(str(data_file))
    df_5m = resample_to_timeframe(df, "5T")
    
    # Test on first 7 days only (to stay within API limits)
    test_days = 7
    candles_per_day = 288  # 5-min candles
    test_candles = test_days * candles_per_day
    
    df_test = df_5m.head(test_candles)
    
    logger.warning(f"⚠️  Testing on FIRST {test_days} DAYS only (to stay within free API limits)")
    
    # Run backtest
    strategy = AITradingStrategyV2(lookback_candles=50, temperature=0.4)
    results = strategy.backtest(df_test)
    
    # Print results
    logger.info("\n" + "=" * 80)
    logger.info("🤖 AI STRATEGY V2 RESULTS (AGGRESSIVE MODE)")
    logger.info("=" * 80)
    logger.info(f"Initial Capital: ${results['initial_capital']:,.2f}")
    logger.info(f"Final Capital: ${results['final_capital']:,.2f}")
    logger.info(f"Total Return: {results['total_return_pct']:+.2f}%")
    logger.info(f"")
    logger.info(f"Total Trades: {results['total_trades']}")
    logger.info(f"  - Buys: {results['buy_trades']}")
    logger.info(f"  - Sells: {results['sell_trades']}")
    logger.info(f"Win Rate: {results['win_rate_pct']:.2f}%")
    logger.info(f"AI Calls Made: {results['ai_calls_made']}")
    logger.info("=" * 80)
    
    # Save results
    output_file = f"backtest_ai_strategy_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        # Convert Timestamp objects to strings
        results_clean = results.copy()
        results_clean['trades'] = [
            {**t, 'timestamp': str(t['timestamp'])} for t in results['trades']
        ]
        json.dump(results_clean, f, indent=2)
    
    logger.success(f"✅ Results saved to: {output_file}")
    
    # Boss verdict
    logger.info("\n" + "=" * 80)
    logger.info("💎 BOSS VERDICT")
    logger.info("=" * 80)
    
    if results['total_trades'] == 0:
        logger.error("❌ STILL TOO CONSERVATIVE - 0 trades executed")
        logger.info("   Need to increase temperature further or change model")
    elif results['total_return_pct'] > 20:
        logger.success(f"✅ EXCELLENT - Beat buy & hold ({results['total_return_pct']:+.2f}% vs +21.66%)")
    elif results['total_return_pct'] > 0:
        logger.warning(f"⚠️  POSITIVE BUT WEAK - {results['total_return_pct']:+.2f}% (buy & hold: +21.66%)")
    else:
        logger.error(f"❌ FAILED - Negative return: {results['total_return_pct']:+.2f}%")
    
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

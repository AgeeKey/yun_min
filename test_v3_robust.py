#!/usr/bin/env python3
"""
AI Trading Strategy V3 - DYNAMIC POSITION SIZING
=================================================
IMPROVEMENTS:
- 25%/50%/75%/100% position levels (not just all-or-nothing)
- Partial sells on overbought (RSI>70)
- Reload cash on dips (RSI<40)
- Stop-loss on bearish reversals

TARGET: Beat Buy & Hold by making 11+ trades with +1.99% average
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
from groq import Groq

# Initialize Groq
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class AITradingStrategyV3:
    def __init__(self, lookback_candles=50, temperature=0.4):
        self.lookback = lookback_candles
        self.temperature = temperature
        self.model = "llama-3.3-70b-versatile"
        
    def calculate_indicators(self, df):
        """Calculate technical indicators"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # EMA
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        return df
    
    def format_market_context(self, df, idx, current_position_pct):
        """Format market data for AI with POSITION CONTEXT"""
        recent = df.iloc[max(0, idx - self.lookback):idx + 1].copy()
        
        current = recent.iloc[-1]
        price = current['close']
        rsi = current['rsi']
        macd = current['macd']
        macd_signal = current['macd_signal']
        
        # Price action
        price_change_5 = ((recent['close'].iloc[-1] / recent['close'].iloc[-5]) - 1) * 100 if len(recent) >= 5 else 0
        price_change_20 = ((recent['close'].iloc[-1] / recent['close'].iloc[-20]) - 1) * 100 if len(recent) >= 20 else 0
        
        # Trend
        trend = "BULL" if current['ema_20'] > current['ema_50'] else "BEAR"
        
        context = f"""
YOUR TASK:
You are an AGGRESSIVE crypto trader with DYNAMIC POSITION SIZING aiming for MAXIMUM RETURNS.

CURRENT POSITION: {current_position_pct}% in BTC
- If 0%: You have 100% cash, ready to buy
- If 25%: You have 75% cash available
- If 50%: You have 50% cash available
- If 75%: You have 25% cash available
- If 100%: You are FULLY invested, can only SELL or HOLD

CURRENT MARKET DATA:
- Price: ${price:,.2f}
- RSI: {rsi:.1f}
- MACD: {macd:.2f} (Signal: {macd_signal:.2f})
- Trend: {trend} (EMA20: ${current['ema_20']:,.2f}, EMA50: ${current['ema_50']:,.2f})
- 5-candle change: {price_change_5:+.2f}%
- 20-candle change: {price_change_20:+.2f}%

TRADING RULES (V3 - DYNAMIC SIZING):

1. BUY RULES (when position < 100%):
   - RSI < 30 → BUY to 100% (AGGRESSIVE dip buy)
   - RSI 30-40 + bullish MACD → BUY to 75% (STRONG buy)
   - RSI 40-50 + uptrend → BUY to 50% (MODERATE buy)
   - Never buy if RSI > 70 (overbought)

2. SELL RULES (when position > 0%):
   - RSI > 75 + bearish MACD → SELL to 0% (FULL exit on reversal)
   - RSI 70-75 → SELL to 50% (PARTIAL profit taking)
   - RSI 65-70 + bearish divergence → SELL to 75% (REDUCE position)
   - Never sell if RSI < 40 in uptrend (don't panic sell dips)

3. HOLD RULES:
   - Position comfortable for current RSI level
   - Waiting for better entry/exit
   - Unclear signals

CURRENT POSITION ANALYSIS:
"""
        if current_position_pct == 0:
            context += "- You have NO position. Look for BUY opportunities.\n"
        elif current_position_pct == 100:
            context += "- You are FULLY invested. Look for SELL opportunities or HOLD.\n"
        else:
            context += f"- You have {current_position_pct}% position. Can BUY more or SELL partial.\n"
        
        context += f"""
RESPOND WITH VALID JSON:
{{
  "signal": "BUY|SELL|HOLD",
  "target_position": 0-100,
  "confidence": 0-100,
  "reason": "brief explanation (max 15 words)"
}}

Example responses:
{{"signal": "BUY", "target_position": 100, "confidence": 90, "reason": "RSI 28 extreme dip in bull trend"}}
{{"signal": "SELL", "target_position": 50, "confidence": 75, "reason": "RSI 72 overbought partial exit"}}
{{"signal": "HOLD", "target_position": {current_position_pct}, "confidence": 60, "reason": "Neutral zone wait for clarity"}}

YOUR RESPONSE (JSON only):"""
        
        return context
    
    def get_ai_signal(self, df, idx, current_position_pct):
        """Get trading signal from AI with retry logic"""
        import time
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                context = self.format_market_context(df, idx, current_position_pct)
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert crypto trader. Respond ONLY with valid JSON, no markdown, no explanation."
                        },
                        {
                            "role": "user",
                            "content": context
                        }
                    ],
                    temperature=self.temperature,
                    max_tokens=150,timeout=60
                )
                
                raw_response = response.choices[0].message.content.strip()
                
                # Clean response
                if raw_response.startswith("```"):
                    raw_response = raw_response.split("```")[1]
                    if raw_response.startswith("json"):
                        raw_response = raw_response[4:]
                
                signal = json.loads(raw_response)
                
                # Validate
                if signal['signal'] not in ['BUY', 'SELL', 'HOLD']:
                    signal['signal'] = 'HOLD'
                
                signal['target_position'] = max(0, min(100, signal.get('target_position', current_position_pct)))
                signal['confidence'] = max(0, min(100, signal.get('confidence', 50)))
                
                # Add small delay to avoid rate limits
                time.sleep(0.3)
                
                return signal
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠ Retry {attempt+1}/{max_retries} after error: {str(e)[:40]}")
                    time.sleep(5)  # Wait before retry
                    continue
                else:
                    # Last attempt failed
                    print(f"❌ AI Error after {max_retries} attempts: {str(e)[:50]}")
                    return {
                        'signal': 'HOLD',
                        'target_position': current_position_pct,
                        'confidence': 0,
                        'reason': 'API error'
                    }
    
    def backtest(self, data_file, initial_capital=10000):
        """Run backtest with dynamic position sizing"""
        print(f"\n{'='*60}")
        print("AI STRATEGY V3 BACKTEST - DYNAMIC POSITION SIZING")
        print(f"{'='*60}\n")
        
        # Load data
        df = pd.read_csv(data_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        df = df.dropna().reset_index(drop=True)
        
        print(f"[DATA] {len(df)} candles")
        print(f"[PERIOD] {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
        print(f"[CAPITAL] ${initial_capital:,.2f}")
        print(f"[MODEL] {self.model} (T={self.temperature})")
        print(f"[LOOKBACK] {self.lookback} candles\n")
        
        # Portfolio state
        cash = initial_capital
        btc_amount = 0
        position_pct = 0  # Current position percentage (0-100)
        
        trades = []
        portfolio_values = []
        ai_calls = 0
        
        # Start from lookback
        for i in range(self.lookback, len(df)):
            current = df.iloc[i]
            price = current['close']
            timestamp = current['timestamp']
            
            # Current portfolio value
            portfolio_value = cash + (btc_amount * price)
            portfolio_values.append(portfolio_value)
            
            # Get AI signal
            signal_data = self.get_ai_signal(df, i, position_pct)
            ai_calls += 1
            
            signal = signal_data['signal']
            target_position = signal_data['target_position']
            confidence = signal_data['confidence']
            reason = signal_data['reason']
            
            # Calculate position change needed
            target_btc_value = portfolio_value * (target_position / 100)
            current_btc_value = btc_amount * price
            
            # Execute trade if significant change
            if abs(target_position - position_pct) >= 10:  # Min 10% change to avoid tiny trades
                
                if target_position > position_pct:
                    # BUY: Increase position
                    buy_amount = target_btc_value - current_btc_value
                    if buy_amount > 0 and cash >= buy_amount:
                        btc_bought = buy_amount / price
                        btc_amount += btc_bought
                        cash -= buy_amount
                        position_pct = target_position
                        
                        trades.append({
                            'timestamp': timestamp,
                            'type': 'BUY',
                            'price': price,
                            'btc_amount': btc_bought,
                            'usd_amount': buy_amount,
                            'position_pct': position_pct,
                            'reason': reason,
                            'rsi': current['rsi']
                        })
                        
                        print(f"[{timestamp.strftime('%m-%d %H:%M')}] BUY to {position_pct}% @ ${price:,.2f}")
                        print(f"  AI: {signal} ({confidence}%) - {reason}")
                        print(f"  BTC: +{btc_bought:.6f} | Cash: ${cash:,.2f} | Portfolio: ${portfolio_value:,.2f}")
                
                elif target_position < position_pct:
                    # SELL: Decrease position
                    sell_value = current_btc_value - target_btc_value
                    if sell_value > 0 and btc_amount > 0:
                        btc_to_sell = sell_value / price
                        btc_to_sell = min(btc_to_sell, btc_amount)  # Don't oversell
                        
                        cash += btc_to_sell * price
                        btc_amount -= btc_to_sell
                        position_pct = target_position
                        
                        trades.append({
                            'timestamp': timestamp,
                            'type': 'SELL',
                            'price': price,
                            'btc_amount': btc_to_sell,
                            'usd_amount': btc_to_sell * price,
                            'position_pct': position_pct,
                            'reason': reason,
                            'rsi': current['rsi']
                        })
                        
                        print(f"[{timestamp.strftime('%m-%d %H:%M')}] 🔴 SELL to {position_pct}% @ ${price:,.2f}")
                        print(f"  └─ AI: {signal} ({confidence}%) - {reason}")
                        print(f"  └─ BTC: -{btc_to_sell:.6f} | Cash: ${cash:,.2f} | Portfolio: ${portfolio_value:,.2f}")
            
            else:
                # HOLD
                if ai_calls % 200 == 0:  # Print every 200 calls to reduce spam
                    print(f"[{timestamp.strftime('%m-%d %H:%M')}] ⚪ HOLD {position_pct}% - {reason}")
        
        # Final portfolio value
        final_price = df.iloc[-1]['close']
        final_value = cash + (btc_amount * final_price)
        total_return = ((final_value - initial_capital) / initial_capital) * 100
        
        # Calculate buy & hold
        buy_hold_btc = initial_capital / df.iloc[self.lookback]['close']
        buy_hold_value = buy_hold_btc * final_price
        buy_hold_return = ((buy_hold_value - initial_capital) / initial_capital) * 100
        
        # Trade statistics
        buy_trades = [t for t in trades if t['type'] == 'BUY']
        sell_trades = [t for t in trades if t['type'] == 'SELL']
        
        # Results
        print(f"\n{'='*60}")
        print(f"AI STRATEGY V3 RESULTS")
        print(f"{'='*60}\n")
        print(f"💰 Initial Capital: ${initial_capital:,.2f}")
        print(f"💵 Final Capital: ${final_value:,.2f}")
        print(f"📈 Total Return: {total_return:+.2f}%")
        print(f"📊 Buy & Hold Return: {buy_hold_return:+.2f}%")
        print(f"🎯 Outperformance: {total_return - buy_hold_return:+.2f}%")
        print(f"\n📊 TRADE STATISTICS:")
        print(f"  Total Trades: {len(trades)} ({len(buy_trades)} BUY, {len(sell_trades)} SELL)")
        print(f"  AI Calls Made: {ai_calls:,}")
        print(f"  AI Call Efficiency: {len(trades) / ai_calls * 100:.2f}% resulted in trades")
        
        # Save results
        results = {
            'strategy': 'AI_V3_Dynamic_Position_Sizing',
            'initial_capital': initial_capital,
            'final_capital': final_value,
            'total_return_pct': total_return,
            'buy_hold_return_pct': buy_hold_return,
            'outperformance_pct': total_return - buy_hold_return,
            'total_trades': len(trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'ai_calls': ai_calls,
            'trades': trades,
            'parameters': {
                'lookback': self.lookback,
                'temperature': self.temperature,
                'model': self.model
            }
        }
        
        filename = f"backtest_ai_strategy_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {filename}")
        
        # VERDICT
        print(f"\n{'='*60}")
        print(f"🎯 BOSS VERDICT:")
        if total_return > buy_hold_return:
            print(f"✅ AI V3 BEATS BUY & HOLD by {total_return - buy_hold_return:+.2f}%!")
            print(f"🚀 DYNAMIC SIZING WORKS! {len(trades)} trades vs V2's 3 trades")
        elif total_return > 5.98:
            print(f"✅ AI V3 BETTER THAN V2 ({total_return:.2f}% vs 5.98%)")
            print(f"📈 But still below Buy & Hold ({buy_hold_return:.2f}%)")
        else:
            print(f"⚠️ AI V3 WORSE than V2 (5.98%)")
            print(f"🔄 Consider reverting or tweaking parameters")
        print(f"{'='*60}\n")
        
        return results

if __name__ == "__main__":
    print("\n[AI] Initializing AI Trading Strategy V3...")
    
    # Check API key
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY not set!")
        print("Set it with: $env:GROQ_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Initialize strategy
    strategy = AITradingStrategyV3(
        lookback_candles=50,  # 4+ hours context on 5min
        temperature=0.4       # Aggressive decisions
    )
    
    # Run backtest
    data_file = "BTCUSDT_5m_resampled.csv"
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        print("Run download_binance_data.py first!")
        sys.exit(1)
    
    results = strategy.backtest(data_file)
    
    print("\n✅ V3 Test complete! Review results above.")
    print("📊 Compare with V2: +5.98% (3 trades)")
    print("🎯 Target: Beat Buy & Hold with 11+ trades at +1.99% avg\n")

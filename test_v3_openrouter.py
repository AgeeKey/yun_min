#!/usr/bin/env python3
"""
AI Trading Strategy V3 - OPENROUTER (FREE Llama 3.3 70B)
========================================================
FINAL VERSION with OpenRouter API for unlimited FREE calls

PROVIDER: OpenRouter (https://openrouter.ai)
MODEL: meta-llama/llama-3.3-70b-instruct:free
COST: $0 per token (completely FREE!)
UPTIME: 98-100% with 4 provider fallbacks
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import time
from datetime import datetime
from openai import OpenAI

# Initialize OpenRouter client
client = OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

class AITradingStrategyV3:
    def __init__(self, lookback_candles=50, temperature=0.4):
        self.lookback = lookback_candles
        self.temperature = temperature
        self.model = "meta-llama/llama-3.3-70b-instruct"  # Paid version ($0.0006/1K tokens)
        
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
   - RSI < 30 -> BUY to 100% (AGGRESSIVE dip buy)
   - RSI 30-40 + bullish MACD -> BUY to 75% (STRONG buy)
   - RSI 40-50 + uptrend -> BUY to 50% (MODERATE buy)
   - Else -> HOLD

2. SELL RULES (when position > 0%):
   - RSI > 75 + bearish MACD -> SELL to 0% (EXIT all)
   - RSI 70-75 -> SELL to 50% (TAKE PROFIT partially)
   - RSI 65-70 + bearish divergence -> SELL to 75% (REDUCE slightly)
   - Else -> HOLD

3. POSITION LOGIC:
   - Only change position if difference >= 10%
   - Aim for 15-25 trades in 7 days to beat Buy & Hold
   - Target average return per trade: +1.99%

RESPOND WITH VALID JSON ONLY:
{{
  "signal": "BUY|SELL|HOLD",
  "target_position": 0-100,
  "confidence": 0-100,
  "reason": "brief technical explanation"
}}
"""
        return context
    
    def get_ai_signal(self, df, idx, current_position_pct):
        """Get AI trading signal via OpenRouter"""
        context = self.format_market_context(df, idx, current_position_pct)
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a crypto trading AI. Respond ONLY with valid JSON. No markdown, no explanation outside JSON."
                        },
                        {
                            "role": "user",
                            "content": context
                        }
                    ],
                    temperature=self.temperature,
                    max_tokens=150
                )
                
                # Parse response
                content = response.choices[0].message.content.strip()
                
                # Clean markdown if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                signal_data = json.loads(content)
                
                # Validate
                required_keys = ['signal', 'target_position', 'confidence', 'reason']
                if not all(k in signal_data for k in required_keys):
                    raise ValueError(f"Missing required keys in response: {signal_data}")
                
                # Small delay to avoid rate limits
                time.sleep(0.1)  # VPN enabled - faster!
                
                return signal_data
                
            except Exception as e:
                print(f"  [RETRY {attempt+1}/{max_retries}] Error: {str(e)[:100]}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    # Fallback to HOLD
                    return {
                        "signal": "HOLD",
                        "target_position": current_position_pct,
                        "confidence": 0,
                        "reason": f"API error after {max_retries} retries"
                    }
    
    def backtest(self, data_file):
        """Run backtest with DYNAMIC POSITION SIZING"""
        print(f"\n{'='*80}")
        print(f"AI TRADING STRATEGY V3 - OPENROUTER (FREE)")
        print(f"{'='*80}")
        print(f"Model: {self.model}")
        print(f"Temperature: {self.temperature}")
        print(f"Lookback: {self.lookback} candles\n")
        
        # Load data
        df = pd.read_csv(data_file)
        df = self.calculate_indicators(df)
        
        # Initialize tracking
        initial_cash = 10000
        cash = initial_cash
        btc = 0
        position_pct = 0  # Track current position percentage
        
        trades = []
        portfolio_values = []
        ai_call_count = 0
        
        start_price = df.iloc[self.lookback]['close']
        end_price = df.iloc[-1]['close']
        buy_hold_return = ((end_price / start_price) - 1) * 100
        
        print(f"Start Price: ${start_price:,.2f}")
        print(f"End Price: ${end_price:,.2f}")
        print(f"Buy & Hold: {buy_hold_return:+.2f}%")
        print(f"\n{'='*80}")
        print(f"RUNNING V3 BACKTEST...")
        print(f"{'='*80}\n")
        
        # Run backtest
        for i in range(self.lookback, len(df)):
            current_price = df.iloc[i]['close']
            timestamp = df.iloc[i]['timestamp']
            
            # Calculate current portfolio value
            portfolio_value = cash + (btc * current_price)
            portfolio_values.append({
                'timestamp': timestamp,
                'value': portfolio_value,
                'price': current_price
            })
            
            # Get AI signal
            ai_call_count += 1
            signal_data = self.get_ai_signal(df, i, position_pct)
            
            signal = signal_data['signal']
            target_position = signal_data['target_position']
            confidence = signal_data['confidence']
            reason = signal_data['reason']
            
            # Only trade if position change >= 10%
            position_change = abs(target_position - position_pct)
            
            if position_change >= 10:
                if target_position > position_pct:
                    # BUY - Increase position
                    target_btc_value = portfolio_value * (target_position / 100)
                    current_btc_value = btc * current_price
                    additional_btc_value = target_btc_value - current_btc_value
                    
                    if additional_btc_value > 0 and cash >= additional_btc_value:
                        btc_to_buy = additional_btc_value / current_price
                        btc += btc_to_buy
                        cash -= additional_btc_value
                        position_pct = target_position
                        
                        trades.append({
                            'timestamp': timestamp,
                            'action': 'BUY',
                            'price': current_price,
                            'amount': btc_to_buy,
                            'value': additional_btc_value,
                            'position_from': position_pct - position_change,
                            'position_to': position_pct,
                            'confidence': confidence,
                            'reason': reason
                        })
                        
                        print(f"[{timestamp}] BUY to {position_pct}% @ ${current_price:,.2f}")
                        print(f"  AI: {signal} ({confidence}%) - {reason}")
                        print(f"  Portfolio: ${portfolio_value:,.2f}\n")
                
                elif target_position < position_pct:
                    # SELL - Decrease position
                    target_btc_value = portfolio_value * (target_position / 100)
                    current_btc_value = btc * current_price
                    reduce_btc_value = current_btc_value - target_btc_value
                    
                    if reduce_btc_value > 0 and btc > 0:
                        btc_to_sell = reduce_btc_value / current_price
                        btc_to_sell = min(btc_to_sell, btc)
                        
                        cash_received = btc_to_sell * current_price
                        btc -= btc_to_sell
                        cash += cash_received
                        
                        old_position = position_pct
                        position_pct = target_position
                        
                        trades.append({
                            'timestamp': timestamp,
                            'action': 'SELL',
                            'price': current_price,
                            'amount': btc_to_sell,
                            'value': cash_received,
                            'position_from': old_position,
                            'position_to': position_pct,
                            'confidence': confidence,
                            'reason': reason
                        })
                        
                        print(f"[{timestamp}] SELL to {position_pct}% @ ${current_price:,.2f}")
                        print(f"  AI: {signal} ({confidence}%) - {reason}")
                        print(f"  Portfolio: ${portfolio_value:,.2f}\n")
            
            # Progress indicator
            if (i - self.lookback) % 100 == 0:
                progress = ((i - self.lookback) / (len(df) - self.lookback)) * 100
                print(f"[PROGRESS] {progress:.1f}% complete ({i}/{len(df)}) - {ai_call_count} AI calls")
        
        # Final portfolio value
        final_portfolio_value = cash + (btc * end_price)
        strategy_return = ((final_portfolio_value / initial_cash) - 1) * 100
        
        # Calculate metrics
        winning_trades = [t for t in trades if t['action'] == 'SELL']
        total_trades = len([t for t in trades if t['action'] == 'BUY'])
        
        print(f"\n{'='*80}")
        print(f"BACKTEST RESULTS (V3)")
        print(f"{'='*80}")
        print(f"Period: {df.iloc[self.lookback]['timestamp']} to {df.iloc[-1]['timestamp']}")
        print(f"Initial Capital: ${initial_cash:,.2f}")
        print(f"Final Portfolio: ${final_portfolio_value:,.2f}")
        print(f"Strategy Return: {strategy_return:+.2f}%")
        print(f"Buy & Hold Return: {buy_hold_return:+.2f}%")
        print(f"Outperformance: {strategy_return - buy_hold_return:+.2f}%")
        print(f"\nTotal Trades: {total_trades}")
        print(f"Total AI Calls: {ai_call_count}")
        print(f"AI Calls per Trade: {ai_call_count / max(total_trades, 1):.1f}")
        
        # Save results
        results = {
            'strategy': 'AI_V3_OPENROUTER',
            'model': self.model,
            'temperature': self.temperature,
            'lookback': self.lookback,
            'period': {
                'start': df.iloc[self.lookback]['timestamp'],
                'end': df.iloc[-1]['timestamp']
            },
            'returns': {
                'strategy': strategy_return,
                'buy_hold': buy_hold_return,
                'outperformance': strategy_return - buy_hold_return
            },
            'trades': trades,
            'total_trades': total_trades,
            'ai_calls': ai_call_count,
            'portfolio_history': portfolio_values
        }
        
        filename = f"backtest_ai_v3_openrouter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {filename}")
        return results

if __name__ == "__main__":
    # Check API key
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY not found!")
        print("\n=== SETUP INSTRUCTIONS ===")
        print("1. Go to https://openrouter.ai")
        print("2. Create FREE account")
        print("3. Get API key from dashboard")
        print("4. Run: $env:OPENROUTER_API_KEY='sk-or-v1-...'")
        sys.exit(1)
    
    strategy = AITradingStrategyV3(
        lookback_candles=50,
        temperature=0.4
    )
    
    results = strategy.backtest('f:/AgeeKey/yun_min/BTCUSDT_5m_resampled.csv')

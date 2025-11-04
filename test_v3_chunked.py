#!/usr/bin/env python3
"""
AI Trading Strategy V3 - CHUNKED EXECUTION (обход network timeout)
==================================================================
Стратегия: Разбить тест на маленькие порции по 100 свечей,
сохранять прогресс после каждой порции в JSON файл.
Если упадет - можно продолжить с того места, где остановились.
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

CHECKPOINT_FILE = "v3_checkpoint.json"
CHUNK_SIZE = 100  # Обрабатываем по 100 свечей за раз

class AITradingStrategyV3:
    def __init__(self, lookback_candles=50, temperature=0.4):
        self.lookback = lookback_candles
        self.temperature = temperature
        self.model = "meta-llama/llama-3.3-70b-instruct:free"
        
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
        
        max_retries = 3
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
                    max_tokens=150,
                    timeout=30  # Reduced timeout
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
                
                # Small delay
                time.sleep(0.15)
                
                return signal_data
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  [RETRY {attempt+1}/{max_retries}] {str(e)[:80]}")
                    time.sleep(2)
                else:
                    # Fallback to HOLD
                    return {
                        "signal": "HOLD",
                        "target_position": current_position_pct,
                        "confidence": 0,
                        "reason": f"API error: {str(e)[:50]}"
                    }
    
    def save_checkpoint(self, state):
        """Сохранить прогресс в файл"""
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"  [CHECKPOINT SAVED] Progress: {state['last_index']}/{state['total_candles']}")
    
    def load_checkpoint(self):
        """Загрузить прогресс из файла"""
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        return None
    
    def backtest_chunked(self, data_file):
        """Run backtest with CHUNKED EXECUTION to avoid timeouts"""
        print(f"\n{'='*80}")
        print(f"AI TRADING STRATEGY V3 - CHUNKED EXECUTION")
        print(f"{'='*80}")
        print(f"Model: {self.model}")
        print(f"Chunk Size: {CHUNK_SIZE} candles")
        print(f"Checkpoint File: {CHECKPOINT_FILE}\n")
        
        # Load data
        df = pd.read_csv(data_file)
        df = self.calculate_indicators(df)
        
        # Check for existing checkpoint
        checkpoint = self.load_checkpoint()
        
        if checkpoint:
            print(f"[RESUME] Found checkpoint at candle {checkpoint['last_index']}")
            print(f"[RESUME] Continuing from where we left off...\n")
            
            cash = checkpoint['cash']
            btc = checkpoint['btc']
            position_pct = checkpoint['position_pct']
            trades = checkpoint['trades']
            portfolio_values = checkpoint['portfolio_values']
            ai_call_count = checkpoint['ai_call_count']
            start_index = checkpoint['last_index'] + 1
        else:
            print("[NEW] Starting fresh backtest...\n")
            
            # Initialize tracking
            initial_cash = 10000
            cash = initial_cash
            btc = 0
            position_pct = 0
            trades = []
            portfolio_values = []
            ai_call_count = 0
            start_index = self.lookback
        
        start_price = df.iloc[self.lookback]['close']
        end_price = df.iloc[-1]['close']
        buy_hold_return = ((end_price / start_price) - 1) * 100
        
        print(f"Start Price: ${start_price:,.2f}")
        print(f"End Price: ${end_price:,.2f}")
        print(f"Buy & Hold: {buy_hold_return:+.2f}%")
        print(f"\n{'='*80}")
        print(f"RUNNING V3 BACKTEST (CHUNKED)...")
        print(f"{'='*80}\n")
        
        # Run backtest in chunks
        total_candles = len(df)
        
        for chunk_start in range(start_index, total_candles, CHUNK_SIZE):
            chunk_end = min(chunk_start + CHUNK_SIZE, total_candles)
            
            print(f"\n[CHUNK] Processing candles {chunk_start}-{chunk_end} ({chunk_end - chunk_start} candles)")
            
            for i in range(chunk_start, chunk_end):
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
                            
                            print(f"  [{timestamp}] BUY to {position_pct}% @ ${current_price:,.2f} - {reason[:50]}")
                    
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
                            
                            print(f"  [{timestamp}] SELL to {position_pct}% @ ${current_price:,.2f} - {reason[:50]}")
            
            # Save checkpoint after each chunk
            checkpoint_state = {
                'last_index': chunk_end - 1,
                'total_candles': total_candles,
                'cash': cash,
                'btc': btc,
                'position_pct': position_pct,
                'trades': trades,
                'portfolio_values': portfolio_values,
                'ai_call_count': ai_call_count,
                'timestamp': datetime.now().isoformat()
            }
            self.save_checkpoint(checkpoint_state)
            
            progress = (chunk_end / total_candles) * 100
            print(f"  [PROGRESS] {progress:.1f}% complete ({chunk_end}/{total_candles}) - {ai_call_count} AI calls - {len(trades)} trades")
        
        # Final portfolio value
        final_portfolio_value = cash + (btc * end_price)
        strategy_return = ((final_portfolio_value / 10000) - 1) * 100
        
        # Calculate metrics
        total_trades = len([t for t in trades if t['action'] == 'BUY'])
        
        print(f"\n{'='*80}")
        print(f"BACKTEST COMPLETE!")
        print(f"{'='*80}")
        print(f"Period: {df.iloc[self.lookback]['timestamp']} to {df.iloc[-1]['timestamp']}")
        print(f"Initial Capital: $10,000.00")
        print(f"Final Portfolio: ${final_portfolio_value:,.2f}")
        print(f"Strategy Return: {strategy_return:+.2f}%")
        print(f"Buy & Hold Return: {buy_hold_return:+.2f}%")
        print(f"Outperformance: {strategy_return - buy_hold_return:+.2f}%")
        print(f"\nTotal Trades: {total_trades}")
        print(f"Total AI Calls: {ai_call_count}")
        
        # Save final results
        results = {
            'strategy': 'AI_V3_CHUNKED',
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
        
        filename = f"backtest_ai_v3_chunked_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {filename}")
        
        # Clean up checkpoint
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            print(f"Checkpoint file removed: {CHECKPOINT_FILE}")
        
        return results

if __name__ == "__main__":
    # Check API key
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY not found!")
        print("\nRun: $env:OPENROUTER_API_KEY='sk-or-v1-...'")
        sys.exit(1)
    
    strategy = AITradingStrategyV3(
        lookback_candles=50,
        temperature=0.4
    )
    
    results = strategy.backtest_chunked('f:/AgeeKey/yun_min/BTCUSDT_5m_resampled.csv')

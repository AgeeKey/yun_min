"""
Test improved OpenAI strategy with trend filter
Run 20 iterations to verify balanced signal distribution
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from yunmin.llm.openai_analyzer import OpenAIAnalyzer
import random

def generate_market_scenarios():
    """Generate 20 diverse market scenarios."""
    scenarios = []
    
    # 5 strong uptrend scenarios
    for i in range(5):
        scenarios.append({
            'name': f'Strong Uptrend #{i+1}',
            'price': 102000 + random.randint(0, 3000),
            'ema_fast': 101500,
            'ema_slow': 99000,  # Price 3% above slow EMA
            'rsi': random.randint(45, 75),
            'volume': 25000000,
            'trend': 'bullish'
        })
    
    # 5 strong downtrend scenarios
    for i in range(5):
        scenarios.append({
            'name': f'Strong Downtrend #{i+1}',
            'price': 98000 - random.randint(0, 3000),
            'ema_fast': 98500,
            'ema_slow': 101000,  # Price 3% below slow EMA
            'rsi': random.randint(25, 55),
            'volume': 30000000,
            'trend': 'bearish'
        })
    
    # 5 sideways/neutral scenarios
    for i in range(5):
        scenarios.append({
            'name': f'Sideways #{i+1}',
            'price': 100000 + random.randint(-500, 500),
            'ema_fast': 100200,
            'ema_slow': 100000,  # Price near EMAs
            'rsi': random.randint(40, 60),
            'volume': 20000000,
            'trend': 'neutral'
        })
    
    # 5 mixed scenarios (oversold/overbought)
    scenarios.extend([
        {
            'name': 'Oversold Bounce',
            'price': 99000,
            'ema_fast': 99500,
            'ema_slow': 100000,
            'rsi': 28,
            'volume': 35000000,
            'trend': 'bearish'
        },
        {
            'name': 'Overbought Pullback',
            'price': 105000,
            'ema_fast': 104500,
            'ema_slow': 103000,
            'rsi': 78,
            'volume': 28000000,
            'trend': 'bullish'
        },
        {
            'name': 'Moderate Uptrend',
            'price': 101000,
            'ema_fast': 100800,
            'ema_slow': 100500,
            'rsi': 58,
            'volume': 22000000,
            'trend': 'bullish'
        },
        {
            'name': 'Moderate Downtrend',
            'price': 99500,
            'ema_fast': 99700,
            'ema_slow': 100000,
            'rsi': 42,
            'volume': 24000000,
            'trend': 'bearish'
        },
        {
            'name': 'Range Bound',
            'price': 100200,
            'ema_fast': 100100,
            'ema_slow': 100000,
            'rsi': 50,
            'volume': 18000000,
            'trend': 'neutral'
        }
    ])
    
    return scenarios

def main():
    print("="*70)
    print("🧪 Testing Improved OpenAI Strategy (Trend Filter)")
    print("="*70)
    
    analyzer = OpenAIAnalyzer(model="gpt-4o-mini")
    
    if not analyzer.enabled:
        print("❌ OpenAI analyzer not enabled. Check API key in .env")
        return
    
    print(f"✅ OpenAI analyzer ready (model: {analyzer.model})")
    print("\n🎯 Testing 20 diverse market scenarios...\n")
    
    scenarios = generate_market_scenarios()
    results = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'='*70}")
        print(f"Scenario {i}/20: {scenario['name']}")
        print(f"{'='*70}")
        print(f"💰 Price: ${scenario['price']:,}")
        print(f"📈 EMA Fast: ${scenario['ema_fast']:,} | EMA Slow: ${scenario['ema_slow']:,}")
        print(f"📊 RSI: {scenario['rsi']} | Trend: {scenario['trend']}")
        
        # Analyze
        result = analyzer.analyze_market(scenario)
        
        print(f"\n🤖 GPT-4o-mini Decision:")
        print(f"   Signal: {result['signal']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reasoning: {result['reasoning'][:150]}...")
        
        results[result['signal']] += 1
    
    # Final report
    print("\n" + "="*70)
    print("📊 FINAL RESULTS")
    print("="*70)
    print(f"Total Scenarios: 20")
    print(f"✅ BUY signals:  {results['BUY']:2d} ({results['BUY']/20*100:.0f}%)")
    print(f"❌ SELL signals: {results['SELL']:2d} ({results['SELL']/20*100:.0f}%)")
    print(f"⏸️  HOLD signals: {results['HOLD']:2d} ({results['HOLD']/20*100:.0f}%)")
    
    print("\n🎯 Target Distribution: 40% BUY / 40% SELL / 20% HOLD")
    print(f"📈 Actual Distribution: {results['BUY']/20*100:.0f}% BUY / {results['SELL']/20*100:.0f}% SELL / {results['HOLD']/20*100:.0f}% HOLD")
    
    # Check if balanced
    if 6 <= results['BUY'] <= 10 and 6 <= results['SELL'] <= 10:
        print("\n✅ STRATEGY BALANCED! Good signal diversity.")
    else:
        print("\n⚠️ Strategy may need further tuning for better balance.")
    
    print("="*70)

if __name__ == "__main__":
    main()

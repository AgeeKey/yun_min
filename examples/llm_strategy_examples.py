"""
Example: Using LLM Strategy with Different Providers

This example demonstrates how to use the generic LLMStrategy with
different LLM providers (OpenAI, Groq, etc.).
"""

import os
from yunmin.strategy.llm_strategy import LLMStrategy
from yunmin.llm.base import create_llm_analyzer
from yunmin.backtesting.backtester import Backtester
from yunmin.backtesting.data_loader import HistoricalDataLoader


def example_openai():
    """Example using OpenAI GPT-4o-mini."""
    print("\n🤖 Example 1: OpenAI GPT-4o-mini")
    print("=" * 50)
    
    # Create OpenAI analyzer
    llm = create_llm_analyzer(
        provider='openai',
        api_key=os.getenv('OPENAI_API_KEY'),
        model='gpt-4o-mini'
    )
    
    # Create strategy with LLM
    strategy = LLMStrategy(
        llm_analyzer=llm,
        use_advanced_indicators=True,
        hybrid_mode=True
    )
    
    print(f"✅ Strategy created with {llm.__class__.__name__}")
    print(f"   Model: gpt-4o-mini")
    print(f"   Mode: Hybrid (Classical + AI)")
    
    return strategy


def example_groq():
    """Example using Groq Llama."""
    print("\n🤖 Example 2: Groq Llama 3.3")
    print("=" * 50)
    
    # Create Groq analyzer
    llm = create_llm_analyzer(
        provider='groq',
        api_key=os.getenv('GROK_API_KEY')  # or GROQ_API_KEY
    )
    
    # Create strategy with LLM
    strategy = LLMStrategy(
        llm_analyzer=llm,
        use_advanced_indicators=True,
        hybrid_mode=False  # AI-only mode
    )
    
    print(f"✅ Strategy created with {llm.__class__.__name__}")
    print(f"   Model: llama-3.3-70b-versatile")
    print(f"   Mode: AI-only (no classical fallback)")
    
    return strategy


def example_backtest_with_llm():
    """Example: Run backtest with LLM strategy."""
    print("\n📊 Example 3: Backtest with LLM Strategy")
    print("=" * 50)
    
    # Create LLM analyzer (OpenAI in this case)
    llm = create_llm_analyzer(
        provider='openai',
        model='gpt-4o-mini'
    )
    
    # Create strategy
    strategy = LLMStrategy(llm_analyzer=llm)
    
    # Generate sample data
    loader = HistoricalDataLoader()
    data = loader.generate_sample_data(
        symbol='BTC/USDT',
        start_price=50000,
        num_candles=500,
        trend='uptrend'
    )
    
    # Create backtester
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        position_size_pct=0.01,
        leverage=1.0,
        use_risk_manager=True
    )
    
    # Run backtest
    print("\n🔄 Running backtest...")
    results = backtester.run(data, symbol='BTC/USDT')
    
    # Display results
    print("\n📈 Results:")
    print(f"   Total Trades: {results['total_trades']}")
    print(f"   Win Rate: {results['win_rate']:.2f}%")
    print(f"   Total P&L: ${results['total_pnl']:.2f}")
    print(f"   Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    
    # Save artifacts
    print("\n💾 Saving artifacts...")
    backtester.save_artifacts('artifacts', run_name='llm_example')
    print("✅ Artifacts saved to artifacts/llm_example_*")
    
    return results


def example_custom_analyzer():
    """Example: Create custom LLM analyzer."""
    print("\n🔧 Example 4: Custom LLM Analyzer")
    print("=" * 50)
    
    from yunmin.llm.base import LLMAnalyzer
    
    class CustomAnalyzer(LLMAnalyzer):
        """Custom LLM analyzer example."""
        
        def __init__(self):
            super().__init__()
            self.enabled = True  # Mark as enabled
            print("✅ Custom analyzer initialized")
        
        def analyze_market(self, market_data):
            """Simple rule-based analysis."""
            rsi = market_data.get('rsi', 50)
            
            if rsi < 30:
                return {
                    'signal': 'BUY',
                    'confidence': 0.8,
                    'reasoning': f'RSI oversold at {rsi}',
                    'model_used': 'custom_rules'
                }
            elif rsi > 70:
                return {
                    'signal': 'SELL',
                    'confidence': 0.8,
                    'reasoning': f'RSI overbought at {rsi}',
                    'model_used': 'custom_rules'
                }
            else:
                return {
                    'signal': 'HOLD',
                    'confidence': 0.5,
                    'reasoning': f'RSI neutral at {rsi}',
                    'model_used': 'custom_rules'
                }
        
        def analyze_market_conditions(self, market_data):
            result = self.analyze_market(market_data)
            return f"{result['signal']}: {result['reasoning']}"
        
        def explain_signal(self, signal_type, reason, market_data):
            return f"Custom analyzer: {signal_type} because {reason}"
        
        def analyze_text(self, prompt, max_tokens=300):
            return "Custom analysis: Simple rule-based system"
    
    # Use custom analyzer
    custom_llm = CustomAnalyzer()
    strategy = LLMStrategy(llm_analyzer=custom_llm)
    
    print(f"✅ Strategy created with custom analyzer")
    print(f"   This demonstrates how to create your own LLM interface")
    
    return strategy


def example_backward_compatibility():
    """Example: Backward compatibility with GrokAIStrategy."""
    print("\n🔄 Example 5: Backward Compatibility")
    print("=" * 50)
    
    # Old way (still works)
    from yunmin.strategy.grok_ai_strategy import GrokAIStrategy
    from yunmin.llm.openai_analyzer import OpenAIAnalyzer
    
    analyzer = OpenAIAnalyzer(model='gpt-4o-mini')
    
    # This still works for backward compatibility
    old_strategy = GrokAIStrategy(grok_analyzer=analyzer)
    
    print("✅ GrokAIStrategy still works (backward compatibility)")
    print("   But LLMStrategy is recommended for new code")
    
    return old_strategy


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  LLM Strategy Examples - Multiple Provider Support")
    print("=" * 60)
    
    # Run examples (comment out if you don't have API keys)
    try:
        example_openai()
    except Exception as e:
        print(f"⚠️  OpenAI example skipped: {e}")
    
    try:
        example_groq()
    except Exception as e:
        print(f"⚠️  Groq example skipped: {e}")
    
    # These don't need API keys
    example_custom_analyzer()
    example_backward_compatibility()
    
    # Uncomment to run backtest (requires API key)
    # example_backtest_with_llm()
    
    print("\n" + "=" * 60)
    print("✅ Examples complete!")
    print("=" * 60)

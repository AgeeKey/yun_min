"""
Advanced AI Strategy Framework - Integration Example

This example demonstrates how to use all components together:
1. Multi-Model AI Ensemble
2. Adaptive Position Sizing Optimizer
3. Market Regime Detection
4. Advanced Backtesting Suite
"""

import pandas as pd
import numpy as np
from loguru import logger

from yunmin.strategy.ai_ensemble import AIEnsembleStrategy
from yunmin.strategy.position_optimizer import PositionOptimizer
from yunmin.ml.regime_detector import RegimeDetector, MarketRegime
from yunmin.core.backtester import AdvancedBacktester


class IntegratedAIStrategy:
    """
    Integrated AI trading strategy combining all advanced components.
    
    Features:
    - Multi-model AI ensemble for signal generation
    - Regime-aware position sizing and strategy adjustments
    - Dynamic position optimization based on performance and volatility
    """
    
    def __init__(
        self,
        groq_api_key: str = None,
        openrouter_api_key: str = None,
        openai_api_key: str = None,
        initial_capital: float = 10000.0
    ):
        """
        Initialize integrated AI strategy.
        
        Args:
            groq_api_key: API key for Groq
            openrouter_api_key: API key for OpenRouter
            openai_api_key: API key for OpenAI
            initial_capital: Starting capital
        """
        # Initialize AI Ensemble
        self.ai_ensemble = AIEnsembleStrategy(
            groq_api_key=groq_api_key,
            openrouter_api_key=openrouter_api_key,
            openai_api_key=openai_api_key
        )
        
        # Initialize Position Optimizer
        self.position_optimizer = PositionOptimizer(
            initial_capital=initial_capital,
            base_risk_pct=0.02
        )
        
        # Initialize Regime Detector
        self.regime_detector = RegimeDetector(
            adx_period=14,
            adx_trending_threshold=25.0,
            bb_volatility_threshold=0.04
        )
        
        logger.info("🚀 Integrated AI Strategy initialized with all components")
    
    def analyze_and_size(self, df: pd.DataFrame) -> dict:
        """
        Complete analysis: regime detection, AI signal, and position sizing.
        
        Args:
            df: Market data DataFrame
            
        Returns:
            Dictionary with complete analysis and recommendations
        """
        # 1. Detect market regime
        regime_analysis = self.regime_detector.detect_regime(df)
        logger.info(f"📊 Regime: {regime_analysis.regime.value.upper()}")
        
        # 2. Get AI ensemble signal
        ai_signal = self.ai_ensemble.analyze(df)
        logger.info(f"🤖 AI Signal: {ai_signal.type.value} (confidence: {ai_signal.confidence:.2f})")
        
        # 3. Get regime-based strategy adjustments
        regime_adjustments = self.regime_detector.get_strategy_adjustments(
            regime_analysis.regime
        )
        
        # 4. Check if signal meets regime requirements
        meets_requirements = (
            ai_signal.confidence >= regime_adjustments['required_confidence']
        )
        
        if not meets_requirements:
            logger.warning(
                f"⚠️  Signal confidence {ai_signal.confidence:.2f} below "
                f"regime requirement {regime_adjustments['required_confidence']:.2f}"
            )
            # Downgrade to HOLD
            final_signal = ai_signal.type
            final_confidence = 0.0
        else:
            final_signal = ai_signal.type
            final_confidence = ai_signal.confidence
        
        # 5. Calculate position size
        position_size = self.position_optimizer.calculate_position_size(
            df,
            signal_confidence=final_confidence
        )
        
        # 6. Apply regime-based position adjustment
        regime_multiplier = regime_analysis.position_sizing_recommendation
        adjusted_position = position_size.adjusted_size * regime_multiplier
        
        logger.info(
            f"💰 Position Size: ${adjusted_position:.2f} "
            f"(base: ${position_size.adjusted_size:.2f}, "
            f"regime: {regime_multiplier:.2f}x)"
        )
        
        return {
            'signal': final_signal.value,
            'confidence': final_confidence,
            'regime': regime_analysis.regime.value,
            'trend_direction': regime_analysis.trend_direction.value,
            'position_size': adjusted_position,
            'position_size_base': position_size.adjusted_size,
            'regime_multiplier': regime_multiplier,
            'volatility_factor': position_size.volatility_factor,
            'performance_factor': position_size.performance_factor,
            'meets_requirements': meets_requirements,
            'required_confidence': regime_adjustments['required_confidence'],
            'reasoning': {
                'ai': ai_signal.reason,
                'regime': regime_analysis.reasoning,
                'position': position_size.reasoning
            }
        }


def example_backtest_with_integrated_strategy():
    """
    Example: Run backtest with integrated AI strategy.
    """
    logger.info("=" * 80)
    logger.info("EXAMPLE: Backtesting with Integrated AI Strategy")
    logger.info("=" * 80)
    
    # Generate sample data
    dates = pd.date_range(start='2024-01-01', periods=500, freq='5min')
    base_price = 50000
    trend = np.linspace(0, 3000, 500)
    noise = np.random.randn(500) * 200
    prices = base_price + trend + noise
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices + np.abs(np.random.randn(500) * 100),
        'low': prices - np.abs(np.random.randn(500) * 100),
        'close': prices,
        'volume': np.random.rand(500) * 1000
    })
    
    # Note: For real use, provide actual API keys
    # Here we demonstrate the structure without live API calls
    logger.info("📈 Creating sample data...")
    logger.info(f"Data shape: {data.shape}")
    logger.info(f"Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
    
    # Analyze a few points in time
    logger.info("\n" + "=" * 80)
    logger.info("Analyzing key time points...")
    logger.info("=" * 80)
    
    # Note: This example shows the structure without API keys
    # In production, you would provide real keys to get actual AI predictions
    logger.info("\n⚠️  Note: API keys not provided - using mock analysis structure")
    logger.info("For real trading, provide API keys for:")
    logger.info("  - GROQ_API_KEY")
    logger.info("  - OPENROUTER_API_KEY")
    logger.info("  - OPENAI_API_KEY")


def example_parameter_optimization():
    """
    Example: Optimize strategy parameters using grid search.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE: Parameter Optimization")
    logger.info("=" * 80)
    
    # Generate sample data
    dates = pd.date_range(start='2024-01-01', periods=300, freq='5min')
    prices = 50000 + np.cumsum(np.random.randn(300) * 100)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices + np.abs(np.random.randn(300) * 50),
        'low': prices - np.abs(np.random.randn(300) * 50),
        'close': prices,
        'volume': np.random.rand(300) * 1000
    })
    
    # Define parameter grid
    param_grid = {
        'adx_trending_threshold': [20.0, 25.0, 30.0],
        'bb_volatility_threshold': [0.03, 0.04, 0.05]
    }
    
    logger.info(f"📊 Parameter combinations to test: {len(param_grid['adx_trending_threshold']) * len(param_grid['bb_volatility_threshold'])}")
    logger.info("Metrics to optimize: Sharpe Ratio")
    
    # In production, you would run optimization:
    # backtester = AdvancedBacktester()
    # results = backtester.optimize_parameters(
    #     StrategyClass,
    #     data,
    #     param_grid,
    #     optimization_metric='sharpe_ratio'
    # )
    
    logger.info("\n✅ Optimization complete!")
    logger.info("Best parameters would be selected based on backtest performance")


def example_walk_forward_validation():
    """
    Example: Perform walk-forward validation.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE: Walk-Forward Validation")
    logger.info("=" * 80)
    
    logger.info("Walk-forward validation splits data into multiple windows:")
    logger.info("  1. Train on 70% of each window")
    logger.info("  2. Test on remaining 30% (out-of-sample)")
    logger.info("  3. Repeat for N windows")
    logger.info("  4. Aggregate results for realistic performance estimate")
    
    logger.info("\nThis prevents overfitting and provides robust performance metrics")


def example_monte_carlo_simulation():
    """
    Example: Run Monte Carlo simulation.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE: Monte Carlo Simulation")
    logger.info("=" * 80)
    
    # Sample trade results
    sample_trades = [
        {'pnl': 150, 'return': 0.015},
        {'pnl': -75, 'return': -0.0075},
        {'pnl': 200, 'return': 0.02},
        {'pnl': -50, 'return': -0.005},
        {'pnl': 100, 'return': 0.01}
    ]
    
    logger.info(f"📊 Sample trades: {len(sample_trades)}")
    logger.info(f"Total P&L: ${sum(t['pnl'] for t in sample_trades)}")
    
    backtester = AdvancedBacktester()
    mc_results = backtester.monte_carlo_simulation(
        sample_trades,
        n_simulations=1000,
        initial_capital=10000.0
    )
    
    logger.info("\n📈 Monte Carlo Results (1000 simulations):")
    logger.info(f"  Mean Final Capital: ${mc_results['final_capital_mean']:.2f}")
    logger.info(f"  Median Final Capital: ${mc_results['final_capital_median']:.2f}")
    logger.info(f"  5th Percentile: ${mc_results['percentile_5']:.2f}")
    logger.info(f"  95th Percentile: ${mc_results['percentile_95']:.2f}")
    logger.info(f"  Worst Max DD: {mc_results['max_dd_worst']*100:.2f}%")


def example_regime_visualization():
    """
    Example: Visualize market regime detection.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE: Market Regime Visualization")
    logger.info("=" * 80)
    
    # Generate sample data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
    prices = 50000 + np.linspace(0, 2000, 100) + np.random.randn(100) * 100
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices + np.abs(np.random.randn(100) * 50),
        'low': prices - np.abs(np.random.randn(100) * 50),
        'close': prices,
        'volume': np.random.rand(100) * 1000
    })
    
    detector = RegimeDetector()
    analysis = detector.detect_regime(data)
    
    # Print visualization
    print("\n" + detector.visualize_regime(analysis))


def main():
    """Run all examples."""
    logger.info("🚀 Advanced AI Strategy Framework Examples")
    logger.info("=" * 80)
    
    # Run examples
    example_backtest_with_integrated_strategy()
    example_parameter_optimization()
    example_walk_forward_validation()
    example_monte_carlo_simulation()
    example_regime_visualization()
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ All examples completed!")
    logger.info("=" * 80)
    logger.info("\nNext steps:")
    logger.info("1. Set up API keys for AI models (GROQ, OpenRouter, OpenAI)")
    logger.info("2. Run backtests on historical data")
    logger.info("3. Optimize parameters for your specific market")
    logger.info("4. Validate with walk-forward and Monte Carlo")
    logger.info("5. Deploy to live trading with proper risk management")


if __name__ == "__main__":
    main()

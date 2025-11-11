#!/usr/bin/env python3
"""
Example: Running Parameter Optimization for October 2025

This example demonstrates how to:
1. Run optimization with synthetic data for October 2025
2. Review the generated report
3. Extract and use the best parameters

Usage:
    python examples/run_optimizer_example.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.optimizer import StrategyOptimizer


def main():
    """Run optimization example."""
    print("=" * 80)
    print("Parameter Optimization Example - October 2025")
    print("=" * 80)
    print()
    
    # Use quick config for demonstration
    config_path = "tools/optimizer_config_quick.yaml"
    
    print(f"📋 Loading configuration from: {config_path}")
    print()
    
    # Initialize optimizer
    optimizer = StrategyOptimizer(config_path)
    
    # Load data (will use synthetic data for October 2025)
    print("📊 Loading data...")
    data = optimizer.load_data()
    print(f"✓ Loaded {len(data)} bars of data")
    print()
    
    # Run optimization
    print("🔍 Running parameter optimization...")
    print("   This will test different combinations of:")
    print("   - RSI thresholds (oversold/overbought)")
    print("   - EMA periods (fast/slow)")
    print()
    
    opt_results = optimizer.run_optimization(data)
    
    print()
    print("=" * 80)
    print("✅ Optimization Complete!")
    print("=" * 80)
    print()
    
    # Display best parameters
    best_params = opt_results['best_params']
    best_score = opt_results['best_score']
    
    print(f"🏆 Best {opt_results['metric']}: {best_score:.4f}")
    print()
    print("📈 Optimized Parameters:")
    for param, value in best_params.items():
        print(f"   - {param:25s}: {value}")
    print()
    
    # Run walk-forward validation
    print("🔄 Running walk-forward validation...")
    wf_results = optimizer.walk_forward_validation(data, best_params)
    
    if wf_results.get('enabled'):
        print(f"✓ Validated across {wf_results['n_splits']} time periods")
        print()
        
        # Display stability metrics
        if wf_results['splits']:
            stability = wf_results['stability']
            print("📊 Stability Analysis:")
            print(f"   - Mean Profit: ${stability['profit_mean']:.2f}")
            print(f"   - Profit Std: ${stability['profit_std']:.2f}")
            print(f"   - Mean Sharpe: {stability['sharpe_mean']:.3f}")
            print(f"   - Mean Win Rate: {stability['win_rate_mean']:.1%}")
            print()
    
    # Save results
    print("💾 Saving results...")
    optimizer.save_results(opt_results, wf_results)
    
    results_dir = optimizer.results_dir
    print()
    print("=" * 80)
    print("📁 Output Files Generated:")
    print("=" * 80)
    print()
    print(f"1. JSON: {results_dir}/optimization_results_*.json")
    print(f"2. CSV:  {results_dir}/optimization_results_*.csv")
    print(f"3. Report: {results_dir}/optimization_report_*.md")
    print()
    print("💡 Next Steps:")
    print()
    print("1. Review the markdown report for detailed analysis")
    print("2. Update your strategy configuration with the best parameters")
    print("3. Run paper trading tests before live deployment")
    print()
    
    # Example of how to use the best parameters
    print("=" * 80)
    print("📝 Implementation Example:")
    print("=" * 80)
    print()
    print("Update config/default.yaml with:")
    print()
    print("```yaml")
    print("strategy:")
    print("  name: ema_crossover")
    print(f"  fast_ema: {best_params['fast_period']}")
    print(f"  slow_ema: {best_params['slow_period']}")
    print(f"  rsi_oversold: {best_params['rsi_oversold']}")
    print(f"  rsi_overbought: {best_params['rsi_overbought']}")
    print("```")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()

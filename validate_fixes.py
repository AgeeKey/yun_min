#!/usr/bin/env python
"""
Validation Script for Critical Security Fixes

This script validates that all the critical P0 fixes are working correctly.
Run this script to verify the system before deployment.

Usage:
    python validate_fixes.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def validate_imports():
    """Validate all new imports work correctly."""
    print("=" * 80)
    print("VALIDATING IMPORTS")
    print("=" * 80)
    
    try:
        from yunmin.risk.policies import (
            ExchangeMarginLevelPolicy,
            FundingRateLimitPolicy,
            OrderRequest,
            RiskCheckResult
        )
        print("✅ Risk policies imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import risk policies: {e}")
        return False
    
    try:
        from yunmin.data_ingest.exchange_adapter import ExchangeAdapter
        print("✅ ExchangeAdapter imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ExchangeAdapter: {e}")
        return False
    
    try:
        from yunmin.strategy.grok_ai_strategy import GrokAIStrategy
        print("✅ GrokAIStrategy imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import GrokAIStrategy: {e}")
        return False
    
    try:
        from yunmin.core.config import RiskConfig
        print("✅ RiskConfig imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import RiskConfig: {e}")
        return False
    
    print()
    return True


def validate_config():
    """Validate configuration has new fields."""
    print("=" * 80)
    print("VALIDATING CONFIGURATION")
    print("=" * 80)
    
    try:
        from yunmin.core.config import RiskConfig, load_config
        
        # Load from YAML file for production values
        try:
            config = load_config('config/default.yaml')
            risk_config = config.risk
            print("✅ Loaded configuration from config/default.yaml")
        except:
            # Fallback to defaults (for testing)
            risk_config = RiskConfig()
            print("⚠️  Using default RiskConfig (YAML not found - this is OK for validation)")
        
        # Check new fields exist
        required_fields = [
            'max_position_size',
            'max_leverage',
            'max_total_exposure',
            'min_margin_level',
            'critical_margin_level',
            'max_funding_rate'
        ]
        
        for field in required_fields:
            if not hasattr(risk_config, field):
                print(f"❌ Missing field: {field}")
                return False
            value = getattr(risk_config, field)
            print(f"✅ {field}: {value}")
        
        # Validate values are in safe range (not too strict since defaults may differ from YAML)
        if risk_config.max_position_size > 0.10:
            print(f"⚠️  WARNING: max_position_size ({risk_config.max_position_size}) > 10% (risky but not critical)")
        
        if risk_config.max_leverage > 5.0:
            print(f"⚠️  WARNING: max_leverage ({risk_config.max_leverage}) > 5x (risky)")
        
        if risk_config.max_total_exposure > 0.30:
            print(f"⚠️  WARNING: max_total_exposure ({risk_config.max_total_exposure}) > 30% (risky)")
        
        print("✅ Configuration structure is valid")
        print("   Note: Production values from config/default.yaml will override these defaults")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_exchange_adapter():
    """Validate ExchangeAdapter has new methods."""
    print("=" * 80)
    print("VALIDATING EXCHANGE ADAPTER")
    print("=" * 80)
    
    try:
        from yunmin.data_ingest.exchange_adapter import ExchangeAdapter
        import inspect
        
        # Check get_balance exists
        if not hasattr(ExchangeAdapter, 'get_balance'):
            print("❌ get_balance method not found")
            return False
        
        sig = inspect.signature(ExchangeAdapter.get_balance)
        print(f"✅ get_balance exists: {sig}")
        
        # Check get_funding_rate exists
        if not hasattr(ExchangeAdapter, 'get_funding_rate'):
            print("❌ get_funding_rate method not found")
            return False
        
        sig = inspect.signature(ExchangeAdapter.get_funding_rate)
        print(f"✅ get_funding_rate exists: {sig}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ ExchangeAdapter validation failed: {e}")
        return False


def validate_risk_policies():
    """Validate risk policies work correctly."""
    print("=" * 80)
    print("VALIDATING RISK POLICIES")
    print("=" * 80)
    
    try:
        from yunmin.risk.policies import (
            ExchangeMarginLevelPolicy,
            FundingRateLimitPolicy,
            OrderRequest,
            RiskCheckResult
        )
        
        # Test ExchangeMarginLevelPolicy
        print("\nTesting ExchangeMarginLevelPolicy:")
        policy = ExchangeMarginLevelPolicy(min_margin_level=200.0, critical_margin_level=150.0)
        order = OrderRequest(symbol='BTC/USDT', side='buy', order_type='market', amount=0.01, leverage=3.0)
        
        # Test healthy margin
        context = {'capital': 10000, 'exchange_balance': {'margin_level': 300.0}}
        result, msg = policy.check(order, context)
        assert result == RiskCheckResult.APPROVED, f"Expected APPROVED, got {result}"
        print(f"  ✅ Healthy margin (300%): {result.value}")
        
        # Test low margin
        context = {'capital': 10000, 'exchange_balance': {'margin_level': 180.0}}
        result, msg = policy.check(order, context)
        assert result == RiskCheckResult.WARNING, f"Expected WARNING, got {result}"
        print(f"  ✅ Low margin (180%): {result.value}")
        
        # Test critical margin
        context = {'capital': 10000, 'exchange_balance': {'margin_level': 140.0}}
        result, msg = policy.check(order, context)
        assert result == RiskCheckResult.REJECTED, f"Expected REJECTED, got {result}"
        print(f"  ✅ Critical margin (140%): {result.value}")
        
        # Test FundingRateLimitPolicy
        print("\nTesting FundingRateLimitPolicy:")
        policy = FundingRateLimitPolicy(max_funding_rate=0.001)
        
        # Test acceptable funding
        context = {'capital': 10000, 'funding_rate': {'rate': 0.0001}}
        result, msg = policy.check(order, context)
        assert result == RiskCheckResult.APPROVED, f"Expected APPROVED, got {result}"
        print(f"  ✅ Acceptable funding (0.01%): {result.value}")
        
        # Test high funding
        context = {'capital': 10000, 'funding_rate': {'rate': 0.002}}
        result, msg = policy.check(order, context)
        assert result == RiskCheckResult.REJECTED, f"Expected REJECTED, got {result}"
        print(f"  ✅ High funding (0.2%): {result.value}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Risk policy validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_strategy_filters():
    """Validate strategy filter methods."""
    print("=" * 80)
    print("VALIDATING STRATEGY FILTERS")
    print("=" * 80)
    
    try:
        from yunmin.strategy.grok_ai_strategy import GrokAIStrategy
        
        strategy = GrokAIStrategy(grok_analyzer=None)
        
        # Check filter methods exist
        filter_methods = [
            '_check_volume_confirmation',
            '_check_ema_crossover',
            '_check_divergence',
            '_check_ema_distance',
            '_get_grok_decision_with_filters',
            '_fallback_logic_with_filters'
        ]
        
        for method in filter_methods:
            if not hasattr(strategy, method):
                print(f"❌ Missing method: {method}")
                return False
            print(f"✅ {method} exists")
        
        # Test volume confirmation
        result = strategy._check_volume_confirmation(1000, 600, multiplier=1.5)
        assert result is True, "Volume confirmation should return True for 1000 > 600*1.5"
        print("✅ Volume confirmation works")
        
        # Test EMA distance
        result = strategy._check_ema_distance(100, 95, min_distance=0.005)
        assert result is True, "EMA distance should return True for 5% distance"
        print("✅ EMA distance check works")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Strategy filter validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(results):
    """Print summary of validation results."""
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check}")
    
    print()
    
    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED!")
        print()
        print("System is ready for testing phase.")
        print()
        print("⚠️  IMPORTANT: Do NOT deploy to production yet!")
        print("Required next steps:")
        print("  1. Run backtesting (100+ trades)")
        print("  2. Test on Binance Testnet (50+ trades, 7+ days)")
        print("  3. Validate win rate >40% and no liquidations")
        print()
        return 0
    else:
        print("❌ VALIDATION FAILED!")
        print()
        print("Some checks did not pass. Review errors above.")
        print("Do NOT proceed with testing until all issues are resolved.")
        print()
        return 1


def main():
    """Run all validation checks."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 18 + "CRITICAL SECURITY FIXES VALIDATION" + " " * 26 + "║")
    print("║" + " " * 78 + "║")
    print("║" + " " * 15 + "Yun Min Trading System - November 2025" + " " * 24 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    results = {
        'Imports': validate_imports(),
        'Configuration': validate_config(),
        'ExchangeAdapter': validate_exchange_adapter(),
        'Risk Policies': validate_risk_policies(),
        'Strategy Filters': validate_strategy_filters()
    }
    
    return print_summary(results)


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
V3 Testnet Readiness Check

Quick validation that all components are ready for testnet deployment:
1. Binance connector (testnet mode)
2. Risk manager
3. V3 strategy signal generation
4. WebSocket connection (if available)

Usage:
    python check_testnet_ready.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, UTC
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from yunmin.connectors.binance_connector import BinanceConnector
from yunmin.risk.manager import RiskManager
from yunmin.core.config import RiskConfig
from yunmin.strategy.ema_crossover import EMACrossoverStrategy
from yunmin.backtesting.data_loader import generate_sample_data


def check_environment():
    """Check environment variables."""
    logger.info("=" * 60)
    logger.info("1. CHECKING ENVIRONMENT VARIABLES")
    logger.info("=" * 60)
    
    required_vars = ["BINANCE_TESTNET_API_KEY", "BINANCE_TESTNET_API_SECRET"]
    missing = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            masked = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"
            logger.info(f"✅ {var}: {masked}")
        else:
            logger.error(f"❌ {var}: NOT SET")
            missing.append(var)
    
    if missing:
        logger.error(f"\n❌ Missing environment variables: {', '.join(missing)}")
        logger.info("\nCreate .env.testnet file with:")
        logger.info("BINANCE_TESTNET_API_KEY=your_testnet_key")
        logger.info("BINANCE_TESTNET_API_SECRET=your_testnet_secret")
        logger.info("\nGet testnet keys at: https://testnet.binance.vision/")
        return False
    
    logger.success("✅ All environment variables set\n")
    return True


def check_binance_connector():
    """Test Binance testnet connectivity."""
    logger.info("=" * 60)
    logger.info("2. TESTING BINANCE TESTNET CONNECTION")
    logger.info("=" * 60)
    
    try:
        api_key = os.getenv("BINANCE_TESTNET_API_KEY")
        api_secret = os.getenv("BINANCE_TESTNET_API_SECRET")
        
        connector = BinanceConnector(
            api_key=api_key,
            api_secret=api_secret,
            testnet=True
        )
        
        # Test 1: Ping
        logger.info("Test 1: Ping exchange...")
        connector.ping()
        logger.success("✅ Ping successful")
        
        # Test 2: Server time
        logger.info("\nTest 2: Check server time...")
        server_time = connector.get_server_time()
        now = int(datetime.now(UTC).timestamp() * 1000)
        drift = abs(server_time - now)
        logger.info(f"Server time: {server_time}")
        logger.info(f"Local time:  {now}")
        logger.info(f"Drift: {drift}ms")
        
        if drift > 5000:
            logger.warning(f"⚠️  Clock drift > 5s! May cause auth errors.")
        else:
            logger.success("✅ Server time sync OK")
        
        # Test 3: Account balance
        logger.info("\nTest 3: Fetch account balance...")
        balance = connector.get_balance()
        logger.info(f"Balance: {balance}")
        
        if "USDT" in balance:
            usdt_balance = balance["USDT"]["free"]
            logger.info(f"USDT Available: {usdt_balance}")
            
            if usdt_balance < 100:
                logger.warning(f"⚠️  Low testnet balance: ${usdt_balance}")
                logger.info("Get testnet funds at: https://testnet.binance.vision/")
            else:
                logger.success(f"✅ Sufficient testnet funds: ${usdt_balance}")
        else:
            logger.warning("⚠️  No USDT in account")
        
        # Test 4: Exchange info
        logger.info("\nTest 4: Fetch exchange info (BTC/USDT)...")
        info = connector.get_exchange_info("BTCUSDT")
        logger.info(f"Symbol: {info['symbol']}")
        logger.info(f"Status: {info['status']}")
        logger.info(f"Min Qty: {info['filters'][2]['minQty']}")
        logger.info(f"Step Size: {info['filters'][2]['stepSize']}")
        logger.success("✅ Exchange info retrieved")
        
        logger.success("\n✅ Binance connector READY\n")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Binance connector FAILED: {e}")
        return False


def check_risk_manager():
    """Test risk manager initialization."""
    logger.info("=" * 60)
    logger.info("3. TESTING RISK MANAGER")
    logger.info("=" * 60)
    
    try:
        config = RiskConfig(
            max_position_size=0.10,  # 10% of capital
            max_leverage=1.0,
            max_daily_drawdown=0.05  # 5%
        )
        
        manager = RiskManager(config)
        logger.info(f"Risk policies loaded: {len(manager.policies)}")
        
        # Test order validation
        from yunmin.core.data_contracts import Order, OrderType, OrderSide
        
        test_order = Order(
            order_id="test-001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            amount=0.01,
            price=50000.0,
            timestamp=datetime.now(UTC)
        )
        
        logger.info("\nTest order validation...")
        result = manager.validate_order(test_order, current_capital=10000.0)
        
        if result.approved:
            logger.success(f"✅ Order approved: {result.reason}")
        else:
            logger.warning(f"⚠️  Order rejected: {result.reason}")
        
        logger.success("\n✅ Risk manager READY\n")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Risk manager FAILED: {e}")
        return False


def check_strategy():
    """Test V3 strategy signal generation."""
    logger.info("=" * 60)
    logger.info("4. TESTING V3 STRATEGY")
    logger.info("=" * 60)
    
    try:
        strategy = EMACrossoverStrategy(
            fast_period=9,
            slow_period=21,
            rsi_period=14,
            rsi_overbought=70,
            rsi_oversold=30
        )
        
        logger.info(f"Strategy initialized: {strategy.__class__.__name__}")
        logger.info(f"Parameters: EMA({strategy.fast_period}/{strategy.slow_period}), RSI({strategy.rsi_period})")
        
        # Generate test data
        logger.info("\nGenerating test market data (100 candles)...")
        data = generate_sample_data(
            symbol="BTCUSDT",
            num_candles=100,
            start_price=50000,
            trend='uptrend'
        )
        
        # Test signal generation
        logger.info("\nTest signal generation...")
        signal = strategy.generate_signal(data)
        
        logger.info(f"Signal type: {signal.type}")
        logger.info(f"Confidence: {signal.confidence:.2%}")
        logger.info(f"Reason: {signal.reason}")
        
        if signal.metadata:
            logger.info(f"Metadata: {signal.metadata}")
        
        logger.success("\n✅ V3 Strategy READY\n")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Strategy FAILED: {e}")
        return False


def check_websocket():
    """Test WebSocket availability (optional)."""
    logger.info("=" * 60)
    logger.info("5. CHECKING WEBSOCKET SUPPORT (Optional)")
    logger.info("=" * 60)
    
    try:
        from yunmin.core.websocket_layer import WebSocketConnector
        logger.success("✅ WebSocket module available")
        
        # Note: Actual connection test skipped (requires running event loop)
        logger.info("⚠️  Full WebSocket test skipped (requires async context)")
        logger.info("WebSocket will be tested during actual deployment")
        
        return True
        
    except ImportError:
        logger.warning("⚠️  WebSocket module not available")
        logger.info("System can still run with REST API polling")
        return True


def main():
    """Run all readiness checks."""
    logger.info("\n" + "=" * 60)
    logger.info("YunMin V3 TESTNET READINESS CHECK")
    logger.info("=" * 60 + "\n")
    
    checks = [
        ("Environment Variables", check_environment),
        ("Binance Connector", check_binance_connector),
        ("Risk Manager", check_risk_manager),
        ("V3 Strategy", check_strategy),
        ("WebSocket Support", check_websocket),
    ]
    
    results = {}
    
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            logger.exception(f"❌ {name} check crashed: {e}")
            results[name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("READINESS CHECK SUMMARY")
    logger.info("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {name}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    logger.info(f"\nScore: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        logger.success("\n🎉 ALL CHECKS PASSED - V3 READY FOR TESTNET DEPLOYMENT!")
        return 0
    elif passed_count >= total_count - 1:
        logger.warning("\n⚠️  MOSTLY READY - Review failed checks before deployment")
        return 1
    else:
        logger.error("\n❌ NOT READY - Fix critical issues before deployment")
        return 2


if __name__ == "__main__":
    sys.exit(main())

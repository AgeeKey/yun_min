"""
Example: Risk Management Demonstration

Shows how to use the risk management system to validate orders.
"""

from yunmin.core.config import RiskConfig
from yunmin.risk import RiskManager
from yunmin.risk.policies import OrderRequest, PositionInfo


def main():
    """Demonstrate risk management features."""
    
    print("=" * 60)
    print("Risk Management System Demo")
    print("=" * 60)
    
    # Create risk configuration
    risk_config = RiskConfig(
        max_position_size=0.1,  # 10% of capital
        max_leverage=3.0,
        max_daily_drawdown=0.05,  # 5%
        stop_loss_pct=0.02,  # 2%
        take_profit_pct=0.03,  # 3%
        enable_circuit_breaker=True
    )
    
    # Create risk manager
    risk_manager = RiskManager(risk_config)
    
    print(f"\n✅ Risk Manager initialized with {len(risk_manager.policies)} policies\n")
    
    # Trading context
    capital = 10000.0
    current_price = 50000.0
    context = {'capital': capital, 'current_price': current_price}
    
    print("=" * 60)
    print("Test 1: Valid order (should pass)")
    print("=" * 60)
    
    order1 = OrderRequest(
        symbol='BTC/USDT',
        side='buy',
        order_type='market',
        amount=0.01,  # Small amount
        price=current_price,
        leverage=2.0
    )
    
    approved, messages = risk_manager.validate_order(order1, context)
    print(f"Order: BUY 0.01 BTC @ ${current_price:,}")
    print(f"Result: {'✅ APPROVED' if approved else '❌ REJECTED'}")
    for msg in messages:
        print(f"  - {msg}")
    
    print("\n" + "=" * 60)
    print("Test 2: Too large position (should fail)")
    print("=" * 60)
    
    order2 = OrderRequest(
        symbol='BTC/USDT',
        side='buy',
        order_type='market',
        amount=0.5,  # Too large - 50% of capital
        price=current_price,
        leverage=1.0
    )
    
    approved, messages = risk_manager.validate_order(order2, context)
    print(f"Order: BUY 0.5 BTC @ ${current_price:,}")
    print(f"Result: {'✅ APPROVED' if approved else '❌ REJECTED'}")
    for msg in messages:
        print(f"  - {msg}")
    
    print("\n" + "=" * 60)
    print("Test 3: Excessive leverage (should fail)")
    print("=" * 60)
    
    order3 = OrderRequest(
        symbol='BTC/USDT',
        side='buy',
        order_type='market',
        amount=0.01,
        price=current_price,
        leverage=10.0  # Too high
    )
    
    approved, messages = risk_manager.validate_order(order3, context)
    print(f"Order: BUY 0.01 BTC @ ${current_price:,} with 10x leverage")
    print(f"Result: {'✅ APPROVED' if approved else '❌ REJECTED'}")
    for msg in messages:
        print(f"  - {msg}")
    
    print("\n" + "=" * 60)
    print("Test 4: Position monitoring (stop loss)")
    print("=" * 60)
    
    # Simulate a losing position
    position = PositionInfo(
        symbol='BTC/USDT',
        size=0.1,
        entry_price=50000.0,
        current_price=48500.0,  # 3% loss
        leverage=2.0
    )
    
    should_close, reason = risk_manager.check_position(position)
    print(f"Position: 0.1 BTC @ ${position.entry_price:,}")
    print(f"Current Price: ${position.current_price:,}")
    print(f"PnL: {position.pnl_percentage:.2f}%")
    print(f"Should close: {'✅ YES' if should_close else '❌ NO'}")
    print(f"Reason: {reason}")
    
    print("\n" + "=" * 60)
    print("Test 5: Circuit breaker")
    print("=" * 60)
    
    # Trigger circuit breaker
    risk_manager.trigger_circuit_breaker("Emergency market conditions")
    print("Circuit breaker triggered: Emergency market conditions")
    
    # Try to place order
    approved, messages = risk_manager.validate_order(order1, context)
    print(f"\nAttempt to place order: {'✅ APPROVED' if approved else '❌ REJECTED'}")
    for msg in messages:
        print(f"  - {msg}")
    
    # Reset circuit breaker
    print("\nResetting circuit breaker...")
    risk_manager.reset_circuit_breaker()
    
    approved, messages = risk_manager.validate_order(order1, context)
    print(f"After reset: {'✅ APPROVED' if approved else '❌ REJECTED'}")
    
    print("\n" + "=" * 60)
    print("Risk Summary")
    print("=" * 60)
    
    summary = risk_manager.get_risk_summary(context)
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Risk management demo completed!\n")


if __name__ == "__main__":
    main()

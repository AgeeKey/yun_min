"""
V4 Backtesting Script - Grok AI Optimized Strategy

Tests the improved V4 strategy against V3 baseline.
Goal: Improve LONG Win Rate from 38.7% to 60%+

V4 Improvements:
1. Asymmetric SL/TP (SHORT: 1.5%/2%, LONG: 3%/4%)
2. Trend filter (EMA 50)
3. Conservative RSI thresholds (65/35 instead of 70/30)
"""

import sys
from pathlib import Path
from datetime import datetime, UTC
import numpy as np
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from yunmin.backtesting.data_loader import HistoricalDataLoader
from yunmin.backtesting.backtester import Backtester
from yunmin.strategy.ema_crossover_v4 import EMACrossoverV4Strategy
from yunmin.risk.manager import RiskManager
from yunmin.core.config import RiskConfig


def run_v4_backtest():
    """Run V4 backtest and generate detailed report."""
    
    logger.info("=" * 80)
    logger.info("🚀 YunMin V4 Backtest - Grok AI Optimized Strategy")
    logger.info("=" * 80)
    
    # Configuration
    symbol = "BTC/USDT"
    initial_capital = 10000.0
    num_candles = 2880  # Same as V3: 2 days of 1-minute data
    
    # V4.1 Strategy: Asymmetric SL/TP only (NO trend filter)
    strategy = EMACrossoverV4Strategy(
        fast_period=9,
        slow_period=21,
        trend_period=50,        # Ignored when trend_filter_enabled=False
        rsi_period=14,
        rsi_overbought=65.0,    # More conservative (was 70)
        rsi_oversold=35.0,      # More conservative (was 30)
        # Asymmetric risk management
        short_sl_pct=1.5,       # Tighter SHORT SL
        short_tp_pct=2.0,
        long_sl_pct=3.0,        # Wider LONG SL
        long_tp_pct=4.0,        # Higher LONG TP
        trend_filter_enabled=False  # V4.1: Disable trend filter
    )
    
    # Run backtest
    backtester = Backtester(
        strategy=strategy,
        initial_capital=initial_capital,
        commission_rate=0.001,  # 0.1% commission
        use_risk_manager=True
    )
    
    # Generate test data (uptrend like V3)
    logger.info(f"Generating {num_candles} candles for {symbol}...")
    data_loader = HistoricalDataLoader(symbol)
    data = data_loader.generate_sample_data(
        num_candles=num_candles,
        trend='uptrend',  # V3 tested uptrend
        volatility=0.02
    )
    
    logger.info(f"Starting V4 backtest...")
    start_time = datetime.now(UTC)
    
    results = backtester.run(data)
    
    end_time = datetime.now(UTC)
    duration = (end_time - start_time).total_seconds()
    
    # Extract metrics and trades
    trades = backtester.metrics.trades  # Сделки хранятся в backtester.metrics.trades
    metrics = results  # results - это уже словарь метрик
    
    # Разделяем сделки по направлению
    long_trades = [t for t in trades if t.side == "LONG"]
    short_trades = [t for t in trades if t.side == "SHORT"]
    
    # Вычисляем LONG статистику
    long_winners = [t for t in long_trades if t.pnl > 0]
    long_losers = [t for t in long_trades if t.pnl <= 0]
    long_wr = (len(long_winners) / len(long_trades) * 100) if long_trades else 0
    long_pnl = sum(t.pnl for t in long_trades) if long_trades else 0
    
    # Вычисляем SHORT статистику
    short_winners = [t for t in short_trades if t.pnl > 0]
    short_losers = [t for t in short_trades if t.pnl <= 0]
    short_wr = (len(short_winners) / len(short_trades) * 100) if short_trades else 0
    short_pnl = sum(t.pnl for t in short_trades) if short_trades else 0
    
    # Print results
    logger.info("=" * 80)
    logger.info("📊 V4 BACKTEST RESULTS")
    logger.info("=" * 80)
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info(f"Test Period: {num_candles} candles (48 hours of 1min data)")
    logger.info("")
    
    logger.info("💰 OVERALL PERFORMANCE:")
    logger.info(f"  Net P&L:          ${metrics['net_pnl']:,.2f} ({metrics['total_return']:.2f}%)")
    logger.info(f"  Max Drawdown:     {metrics['max_drawdown_pct']:.2f}%")
    logger.info(f"  Sharpe Ratio:     {metrics['sharpe_ratio']:.2f}")
    logger.info(f"  Profit Factor:    {metrics['profit_factor']:.2f}")
    logger.info("")
    
    logger.info("📈 TRADE STATISTICS:")
    logger.info(f"  Total Trades:     {metrics['total_trades']}")
    logger.info(f"  Winning Trades:   {metrics['winning_trades']} ({metrics['win_rate']:.1f}%)")
    logger.info(f"  Losing Trades:    {metrics['losing_trades']}")
    logger.info(f"  Avg Win:          ${metrics['avg_win']:,.2f}")
    logger.info(f"  Avg Loss:         ${metrics['avg_loss']:,.2f}")
    logger.info("")
    
    # V4 SPECIFIC: Analyze LONG vs SHORT performance
    logger.info("🔍 DIRECTIONAL ANALYSIS (V4 Focus):")
    logger.info(f"  LONG Trades:      {len(long_trades)} ({len(long_winners)}W / {len(long_losers)}L)")
    logger.info(f"  LONG Win Rate:    {long_wr:.1f}% {'✅' if long_wr >= 60 else '❌'}")
    logger.info(f"  LONG P&L:         ${long_pnl:,.2f}")
    logger.info("")
    logger.info(f"  SHORT Trades:     {len(short_trades)} ({len(short_winners)}W / {len(short_losers)}L)")
    logger.info(f"  SHORT Win Rate:   {short_wr:.1f}% {'✅' if short_wr >= 80 else '❌'}")
    logger.info(f"  SHORT P&L:        ${short_pnl:,.2f}")
    logger.info("")
    
    # V3 vs V4 Comparison
    logger.info("📊 V3 vs V4 COMPARISON:")
    logger.info("  Metric              V3 Result    V4 Result    Change")
    logger.info("  " + "-" * 60)
    logger.info(f"  Total Trades        124          {metrics['total_trades']:<12} {metrics['total_trades'] - 124:+}")
    logger.info(f"  Overall Win Rate    50.8%        {metrics['win_rate']:.1f}%{' ' * (12 - len(f'{metrics['win_rate']:.1f}%'))} {metrics['win_rate'] - 50.8:+.1f}%")
    logger.info(f"  LONG Win Rate       38.7%        {long_wr:.1f}%{' ' * (12 - len(f'{long_wr:.1f}%'))} {long_wr - 38.7:+.1f}%")
    logger.info(f"  SHORT Win Rate      100.0%       {short_wr:.1f}%{' ' * (12 - len(f'{short_wr:.1f}%'))} {short_wr - 100.0:+.1f}%")
    logger.info("")
    
    # Success criteria
    logger.info("✅ V4 SUCCESS CRITERIA:")
    criteria = {
        "LONG WR ≥ 60%": long_wr >= 60.0,
        "SHORT WR ≥ 80%": short_wr >= 80.0,
        "Overall WR ≥ 65%": metrics['win_rate'] >= 65.0,
        "Profit Factor ≥ 2.0": metrics['profit_factor'] >= 2.0,
        "Max Drawdown < 10%": abs(metrics['max_drawdown_pct']) < 10.0,
        "Positive P&L": metrics['net_pnl'] > 0
    }
    
    for criterion, passed in criteria.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {criterion:<25} {status}")
    
    passed_count = sum(criteria.values())
    logger.info("")
    logger.info(f"  Overall: {passed_count}/{len(criteria)} criteria passed")
    
    if passed_count == len(criteria):
        logger.success("🎉 V4 OPTIMIZATION SUCCESSFUL! Ready for testnet deployment.")
    elif passed_count >= len(criteria) * 0.7:
        logger.warning("⚠️  V4 shows improvement but needs refinement.")
    else:
        logger.error("❌ V4 did not meet targets. Further optimization needed.")
    
    logger.info("=" * 80)
    
    # Save detailed report
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_file = project_root / f"V4_BACKTEST_REPORT_{timestamp}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# YunMin V4 Backtest Report\n\n")
        f.write(f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        f.write("## Strategy Configuration\n\n")
        f.write("### V4 Grok AI Optimizations:\n")
        f.write("1. **Asymmetric Risk Management:**\n")
        f.write(f"   - SHORT: SL {strategy.short_sl_pct}%, TP {strategy.short_tp_pct}%\n")
        f.write(f"   - LONG: SL {strategy.long_sl_pct}%, TP {strategy.long_tp_pct}%\n\n")
        f.write("2. **Trend Filter:**\n")
        f.write(f"   - EMA Period: {strategy.trend_period}\n")
        f.write(f"   - Enabled: {strategy.trend_filter_enabled}\n\n")
        f.write("3. **Conservative RSI:**\n")
        f.write(f"   - Overbought: {strategy.rsi_overbought} (was 70)\n")
        f.write(f"   - Oversold: {strategy.rsi_oversold} (was 30)\n\n")
        
        f.write("## Results Summary\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total Trades | {metrics['total_trades']} |\n")
        f.write(f"| Win Rate | {metrics['win_rate']:.1f}% |\n")
        f.write(f"| LONG Win Rate | {long_wr:.1f}% |\n")
        f.write(f"| SHORT Win Rate | {short_wr:.1f}% |\n")
        f.write(f"| Net P&L | ${metrics['net_pnl']:,.2f} |\n")
        f.write(f"| Return | {metrics['total_return']:.2f}% |\n")
        f.write(f"| Max Drawdown | {abs(metrics['max_drawdown_pct']):.2f}% |\n")
        f.write(f"| Profit Factor | {metrics['profit_factor']:.2f} |\n")
        f.write(f"| Sharpe Ratio | {metrics['sharpe_ratio']:.2f} |\n\n")
        
        f.write("## V3 vs V4 Comparison\n\n")
        f.write("| Metric | V3 | V4 | Change |\n")
        f.write("|--------|----|----|--------|\n")
        f.write(f"| LONG WR | 38.7% | {long_wr:.1f}% | {long_wr - 38.7:+.1f}% |\n")
        f.write(f"| SHORT WR | 100.0% | {short_wr:.1f}% | {short_wr - 100.0:+.1f}% |\n")
        f.write(f"| Overall WR | 50.8% | {metrics['win_rate']:.1f}% | {metrics['win_rate'] - 50.8:+.1f}% |\n\n")
        
        f.write("## Next Steps\n\n")
        if passed_count == len(criteria):
            f.write("✅ **V4 READY FOR TESTNET**\n\n")
            f.write("1. Deploy to Binance Testnet\n")
            f.write("2. Run 48h live validation\n")
            f.write("3. Monitor real-time performance\n")
        else:
            f.write("⚠️ **Further Optimization Needed**\n\n")
            f.write("Consider:\n")
            f.write("1. Adjust LONG SL/TP ratios\n")
            f.write("2. Fine-tune trend filter parameters\n")
            f.write("3. Test different RSI thresholds\n")
    
    logger.info(f"📄 Detailed report saved: {report_file}")
    
    return metrics, long_wr, short_wr


if __name__ == "__main__":
    try:
        metrics, long_wr, short_wr = run_v4_backtest()
        
        # Exit code based on success
        if long_wr >= 60.0 and short_wr >= 80.0:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Needs improvement
            
    except Exception as e:
        logger.exception(f"V4 backtest failed: {e}")
        sys.exit(2)

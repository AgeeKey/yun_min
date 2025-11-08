"""
AI Agent Demo - Autonomous Trading Agent Example

Demonstrates the complete autonomous AI trading agent architecture.
Shows how all components work together to make trading decisions.
"""

import asyncio
from datetime import datetime
from loguru import logger

from yunmin.agents.market_analyst import MarketAnalystAgent
from yunmin.agents.risk_assessor import RiskAssessorAgent
from yunmin.agents.portfolio_manager import PortfolioManagerAgent
from yunmin.agents.execution_agent import ExecutionAgent
from yunmin.context.market_data import MarketDataProvider
from yunmin.context.orderbook import OrderBookAnalyzer
from yunmin.reasoning.chain_of_thought import ChainOfThoughtReasoning
from yunmin.reasoning.ensemble import EnsembleDecisionMaker
from yunmin.memory.trade_history import TradeHistory
from yunmin.memory.pattern_library import PatternLibrary, PatternType


class AutonomousAITradingAgent:
    """
    Complete autonomous AI trading agent.
    
    Architecture:
    1. Context Building: Gather rich market data
    2. Analysis: AI agents analyze market
    3. Reasoning: Chain-of-thought decision making
    4. Risk Assessment: Evaluate trade risk
    5. Portfolio Management: Allocate capital
    6. Execution: Smart order placement
    7. Memory: Learn from outcomes
    """
    
    def __init__(self):
        """Initialize all agent components."""
        logger.info("🤖 Initializing Autonomous AI Trading Agent...")
        
        # Memory system
        self.trade_history = TradeHistory(embedding_model='simple')
        self.pattern_library = PatternLibrary()
        
        # Context providers
        self.market_data = MarketDataProvider()
        self.orderbook_analyzer = OrderBookAnalyzer()
        
        # AI Agents
        self.market_analyst = MarketAnalystAgent(memory=self.trade_history)
        self.risk_assessor = RiskAssessorAgent(max_position_size=0.1)
        self.portfolio_manager = PortfolioManagerAgent(max_assets=5)
        self.execution_agent = ExecutionAgent(default_strategy='adaptive')
        
        # Reasoning
        self.reasoning = ChainOfThoughtReasoning()
        self.ensemble = EnsembleDecisionMaker(method='confidence')
        
        # Portfolio state
        self.portfolio = {
            'positions': [],
            'available_capital': 10000.0,
            'total_capital': 10000.0
        }
        
        logger.info("✅ All components initialized")
    
    async def trading_loop(self, symbol: str = 'BTC/USDT'):
        """
        Main trading loop - one complete decision cycle.
        
        Args:
            symbol: Trading pair to analyze
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🔄 Starting trading cycle for {symbol}")
        logger.info(f"{'='*60}\n")
        
        try:
            # Step 1: Gather context
            logger.info("📊 Step 1: Gathering market context...")
            market_context = await self._build_context(symbol)
            logger.info(f"   Price: ${market_context['price']:.2f}")
            logger.info(f"   Trend: {market_context['trend']}")
            logger.info(f"   RSI: {market_context['indicators']['rsi']:.1f}")
            
            # Step 2: Market analysis
            logger.info("\n🔍 Step 2: Market analysis...")
            analysis = await self.market_analyst.analyze(
                market_context,
                risk_tolerance=0.7
            )
            logger.info(f"   Decision: {analysis['decision']}")
            logger.info(f"   Confidence: {analysis['confidence']:.2%}")
            
            # Step 3: Apply reasoning
            logger.info("\n🧠 Step 3: Chain-of-thought reasoning...")
            if analysis['decision'] != 'HOLD':
                # Get risk assessment first
                risk_result = self.risk_assessor.evaluate(
                    analysis,
                    market_context,
                    self.portfolio
                )
                
                # Apply reasoning
                reasoning_result = self.reasoning.reason(
                    market_context,
                    analysis,
                    risk_result,
                    memory=self.trade_history.recall_similar(market_context, top_k=3)
                )
                
                logger.info(f"   Final decision: {reasoning_result['final_decision']}")
                logger.info(f"   Reasoning steps: {len(reasoning_result['steps'])}")
                
                # Print reasoning chain
                formatted_reasoning = self.reasoning.format_reasoning_chain(reasoning_result)
                logger.info(f"\n{formatted_reasoning}")
                
                # Step 4: Risk assessment
                logger.info("\n🛡️  Step 4: Risk assessment...")
                logger.info(f"   Risk score: {risk_result['risk_score']:.1f}/100")
                logger.info(f"   Approved: {risk_result['approved']}")
                logger.info(f"   Position size: {risk_result['recommended_position_size']:.2%}")
                
                if risk_result['approved']:
                    # Step 5: Portfolio allocation
                    logger.info("\n💼 Step 5: Portfolio allocation...")
                    allocation = self.portfolio_manager.allocate(
                        {**analysis, 'recommended_position_size': risk_result['recommended_position_size']},
                        market_context,
                        self.portfolio
                    )
                    
                    if allocation['approved']:
                        logger.info(f"   Symbol: {allocation['symbol']}")
                        logger.info(f"   Action: {allocation['action']}")
                        logger.info(f"   Amount: ${allocation['amount']:.2f}")
                        
                        # Step 6: Execution
                        logger.info("\n⚡ Step 6: Smart execution...")
                        execution_result = await self.execution_agent.execute(
                            allocation,
                            market_context
                        )
                        
                        if execution_result['executed']:
                            logger.info(f"   ✅ Executed: {execution_result['status']}")
                            logger.info(f"   Order ID: {execution_result['order_id']}")
                            logger.info(f"   Strategy: {execution_result.get('strategy', 'immediate')}")
                            
                            # Step 7: Remember
                            logger.info("\n💾 Step 7: Storing in memory...")
                            trade_id = self.trade_history.remember_trade(
                                market_context,
                                analysis,
                                None  # Outcome added when trade closes
                            )
                            logger.info(f"   Trade ID: {trade_id}")
                            logger.info(f"   Total trades in memory: {len(self.trade_history)}")
                    else:
                        logger.info(f"   ⏸️  Allocation rejected: {allocation.get('reason', 'unknown')}")
                else:
                    logger.info("   ⏸️  Trade rejected due to risk concerns")
            else:
                logger.info("   ⏸️  Holding - no clear signal")
            
            # Portfolio summary
            logger.info("\n📈 Portfolio Summary:")
            summary = self.portfolio_manager.get_portfolio_summary(self.portfolio)
            logger.info(f"   Positions: {summary['num_positions']}/{self.portfolio_manager.max_assets}")
            logger.info(f"   Total Capital: ${self.portfolio['total_capital']:.2f}")
            logger.info(f"   Available: ${self.portfolio['available_capital']:.2f}")
            
            # Memory stats
            logger.info("\n🧠 Memory Statistics:")
            stats = self.trade_history.get_statistics()
            logger.info(f"   Total trades: {stats['total_trades']}")
            if stats['trades_with_outcome'] > 0:
                logger.info(f"   Win rate: {stats['win_rate']:.1%}")
                logger.info(f"   Avg PnL: ${stats['avg_pnl']:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error in trading loop: {e}", exc_info=True)
    
    async def _build_context(self, symbol: str) -> dict:
        """Build rich market context."""
        # Get market data
        context = await self.market_data.fetch_market_context(
            symbol,
            include_multi_timeframe=False  # Simplified for demo
        )
        
        # Add orderbook analysis
        try:
            orderbook = await self.orderbook_analyzer.analyze(symbol, depth=50)
            context['orderbook'] = orderbook
        except Exception as e:
            logger.warning(f"Could not fetch orderbook: {e}")
            context['orderbook'] = {}
        
        return context
    
    async def run_continuous(self, symbols: list = ['BTC/USDT'], interval: int = 300):
        """
        Run continuous trading loop.
        
        Args:
            symbols: List of symbols to trade
            interval: Seconds between cycles (default 5 minutes)
        """
        logger.info(f"🚀 Starting continuous trading for {symbols}")
        logger.info(f"   Interval: {interval} seconds")
        
        cycle = 0
        try:
            while True:
                cycle += 1
                logger.info(f"\n{'#'*60}")
                logger.info(f"# Cycle {cycle} - {datetime.now()}")
                logger.info(f"{'#'*60}")
                
                # Trade each symbol
                for symbol in symbols:
                    await self.trading_loop(symbol)
                
                # Wait for next cycle
                logger.info(f"\n⏳ Waiting {interval} seconds for next cycle...")
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)


async def main():
    """Main demo function."""
    logger.info("="*60)
    logger.info("🤖 Autonomous AI Trading Agent Demo")
    logger.info("="*60)
    logger.info("")
    logger.info("This demo shows the complete AI agent architecture:")
    logger.info("  1. Memory System (RAG with vector store)")
    logger.info("  2. AI Agents (Analyst, Risk, Portfolio, Execution)")
    logger.info("  3. Chain-of-Thought Reasoning")
    logger.info("  4. Learning from Past Trades")
    logger.info("")
    logger.info("="*60)
    logger.info("")
    
    # Create agent
    agent = AutonomousAITradingAgent()
    
    # Run single cycle for demo
    logger.info("Running single trading cycle for demonstration...\n")
    await agent.trading_loop('BTC/USDT')
    
    logger.info("\n" + "="*60)
    logger.info("✅ Demo complete!")
    logger.info("="*60)
    logger.info("\nTo run continuous trading, use:")
    logger.info("  await agent.run_continuous(['BTC/USDT', 'ETH/USDT'], interval=300)")
    logger.info("")


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Run demo
    asyncio.run(main())

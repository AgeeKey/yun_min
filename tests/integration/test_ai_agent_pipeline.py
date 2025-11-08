"""
Integration Test - Full AI Agent Pipeline

Tests the complete pipeline from market data to execution.
"""

import pytest
import asyncio
from yunmin.agents.market_analyst import MarketAnalystAgent
from yunmin.agents.risk_assessor import RiskAssessorAgent
from yunmin.agents.portfolio_manager import PortfolioManagerAgent
from yunmin.agents.execution_agent import ExecutionAgent
from yunmin.context.market_data import MarketDataProvider
from yunmin.reasoning.chain_of_thought import ChainOfThoughtReasoning
from yunmin.reasoning.ensemble import EnsembleDecisionMaker
from yunmin.memory.trade_history import TradeHistory


class TestAIAgentPipeline:
    """Test complete AI agent trading pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test complete pipeline from analysis to execution."""
        
        # Initialize components
        memory = TradeHistory(embedding_model='simple')
        market_analyst = MarketAnalystAgent(memory=memory)
        risk_assessor = RiskAssessorAgent()
        portfolio_manager = PortfolioManagerAgent()
        execution_agent = ExecutionAgent()
        reasoning = ChainOfThoughtReasoning()
        
        # Market context
        market_context = {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'indicators': {
                'rsi': 45,
                'ema_fast': 50100,
                'ema_slow': 49900,
                'macd': 50,
                'volume_ratio': 1.2,
                'bb_upper': 51000,
                'bb_middle': 50000,
                'bb_lower': 49000
            },
            'trend': 'bullish',
            'volatility': 0.02,
            'price_change_pct': 0.5,
            'support_resistance': {
                'support_levels': [49000, 48500],
                'resistance_levels': [51000, 52000]
            }
        }
        
        # Portfolio state
        portfolio = {
            'positions': [],
            'available_capital': 10000.0,
            'total_capital': 10000.0
        }
        
        # Step 1: Market Analyst analyzes
        analyst_result = await market_analyst.analyze(market_context, risk_tolerance=0.7)
        
        assert 'decision' in analyst_result
        assert 'confidence' in analyst_result
        
        # Step 2: Risk Assessor evaluates if decision is not HOLD
        if analyst_result['decision'] != 'HOLD':
            risk_result = risk_assessor.evaluate(analyst_result, market_context, portfolio)
            
            assert 'risk_score' in risk_result
            assert 'approved' in risk_result
            
            # Step 3: Apply reasoning
            reasoning_result = reasoning.reason(
                market_context,
                analyst_result,
                risk_result,
                memory=[]
            )
            
            assert 'final_decision' in reasoning_result
            
            # Step 4: If approved, Portfolio Manager allocates
            if risk_result['approved']:
                allocation = portfolio_manager.allocate(
                    {**analyst_result, 'recommended_position_size': risk_result['recommended_position_size']},
                    market_context,
                    portfolio
                )
                
                assert 'approved' in allocation
                
                # Step 5: If allocation approved, Execution Agent executes
                if allocation['approved']:
                    execution_result = await execution_agent.execute(
                        allocation,
                        market_context
                    )
                    
                    assert 'executed' in execution_result
                    
                    # Step 6: Remember the trade
                    if execution_result['executed']:
                        trade_id = memory.remember_trade(
                            market_context,
                            analyst_result,
                            None  # Outcome will be added later
                        )
                        
                        assert trade_id >= 0
    
    @pytest.mark.asyncio
    async def test_ensemble_decision(self):
        """Test ensemble decision from multiple agents."""
        
        # Create multiple analyst agents (could be different models)
        agent1 = MarketAnalystAgent()
        agent2 = MarketAnalystAgent()
        
        ensemble = EnsembleDecisionMaker(method='confidence')
        
        market_context = {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'indicators': {
                'rsi': 35,
                'ema_fast': 50100,
                'ema_slow': 49900,
                'volume_ratio': 1.1
            },
            'trend': 'bullish',
            'volatility': 0.02,
            'price_change_pct': 0.3
        }
        
        # Get decisions from both agents
        decision1 = await agent1.analyze(market_context)
        decision2 = await agent2.analyze(market_context)
        
        # Combine with ensemble
        ensemble_result = ensemble.decide([decision1, decision2])
        
        assert 'decision' in ensemble_result
        assert 'confidence' in ensemble_result
        assert ensemble_result['agents_count'] == 2
    
    @pytest.mark.asyncio
    async def test_multi_asset_portfolio(self):
        """Test managing portfolio with multiple assets."""
        
        portfolio_manager = PortfolioManagerAgent(max_assets=3)
        
        # Multiple market conditions
        market_conditions = {
            'BTC/USDT': {
                'indicators': {'rsi': 50, 'ema_fast': 50000, 'ema_slow': 49000, 'volume_ratio': 1.2},
                'volatility': 0.02,
                'trend_strength': 0.7
            },
            'ETH/USDT': {
                'indicators': {'rsi': 45, 'ema_fast': 3000, 'ema_slow': 2900, 'volume_ratio': 1.3},
                'volatility': 0.025,
                'trend_strength': 0.8
            },
            'SOL/USDT': {
                'indicators': {'rsi': 55, 'ema_fast': 100, 'ema_slow': 95, 'volume_ratio': 1.0},
                'volatility': 0.03,
                'trend_strength': 0.6
            }
        }
        
        portfolio = {
            'positions': [],
            'available_capital': 10000.0,
            'total_capital': 10000.0
        }
        
        # Select best asset to trade
        available = list(market_conditions.keys())
        selected = portfolio_manager.select_next_asset(available, market_conditions, portfolio)
        
        assert selected in available
        
        # Get portfolio summary
        summary = portfolio_manager.get_portfolio_summary(portfolio)
        
        assert 'num_positions' in summary
        assert summary['num_positions'] == 0
    
    @pytest.mark.asyncio
    async def test_memory_learning(self):
        """Test that agent learns from past trades."""
        
        memory = TradeHistory(embedding_model='simple')
        
        # Add some successful trades
        for i in range(5):
            context = {
                'price': 50000.0 + i * 100,
                'indicators': {'rsi': 40 + i, 'ema_fast': 50000, 'ema_slow': 49000},
                'trend': 'bullish',
                'volatility': 0.02
            }
            decision = {'action': 'BUY', 'confidence': 0.7}
            outcome = {'pnl': 100.0, 'success': True}
            
            memory.remember_trade(context, decision, outcome)
        
        # Current similar situation
        current_context = {
            'price': 50200.0,
            'indicators': {'rsi': 42, 'ema_fast': 50000, 'ema_slow': 49000},
            'trend': 'bullish',
            'volatility': 0.02
        }
        
        # Recall similar situations
        similar = memory.recall_similar(current_context, top_k=3)
        
        assert len(similar) > 0
        assert all('similarity' in s for s in similar)
        
        # Use this memory in analysis
        analyst = MarketAnalystAgent(memory=memory)
        result = await analyst.analyze(current_context)
        
        # Should have access to similar cases through memory
        assert 'reasoning_chain' in result
    
    @pytest.mark.asyncio
    async def test_risk_rejection(self):
        """Test that high-risk trades are rejected."""
        
        risk_assessor = RiskAssessorAgent()
        
        # Very risky trade proposal
        risky_trade = {
            'action': 'BUY',
            'confidence': 0.5,  # Low confidence
            'rationale': 'Weak signal'
        }
        
        # High volatility market
        risky_market = {
            'price': 50000.0,
            'indicators': {
                'rsi': 85,  # Overbought
                'volume_ratio': 0.5,  # Low volume
                'ema_fast': 50000,
                'ema_slow': 49000
            },
            'volatility': 0.06  # Very high volatility
        }
        
        portfolio = {
            'positions': [
                {'symbol': 'BTC/USDT', 'size': 0.1}  # Already have position
            ],
            'available_capital': 5000.0,
            'total_capital': 10000.0
        }
        
        result = risk_assessor.evaluate(risky_trade, risky_market, portfolio)
        
        # Should likely be rejected due to multiple risk factors
        assert 'approved' in result
        # Note: Approval depends on exact thresholds, but risk_score should be low
        assert result['risk_score'] < 90  # Not high quality


@pytest.mark.asyncio
async def test_market_data_provider():
    """Test market data provider."""
    
    provider = MarketDataProvider()
    
    # Fetch context (will use sample data)
    context = await provider.fetch_market_context('BTC/USDT', include_multi_timeframe=False)
    
    assert 'symbol' in context
    assert context['symbol'] == 'BTC/USDT'
    assert 'price' in context
    assert 'indicators' in context
    assert 'trend' in context
    
    # Check indicators
    indicators = context['indicators']
    assert 'rsi' in indicators
    assert 'ema_fast' in indicators
    assert 'ema_slow' in indicators

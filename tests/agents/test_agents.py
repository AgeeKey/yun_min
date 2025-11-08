"""
Tests for AI Agents - Market Analyst, Risk Assessor, Portfolio Manager, Execution Agent
"""

import pytest
import asyncio
from yunmin.agents.market_analyst import MarketAnalystAgent
from yunmin.agents.risk_assessor import RiskAssessorAgent
from yunmin.agents.portfolio_manager import PortfolioManagerAgent
from yunmin.agents.execution_agent import ExecutionAgent
from yunmin.memory.trade_history import TradeHistory


class TestMarketAnalystAgent:
    """Test Market Analyst Agent."""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test agent initialization."""
        agent = MarketAnalystAgent(model="gpt-4o-mini")
        
        assert agent.model == "gpt-4o-mini"
        assert agent.memory is not None
    
    @pytest.mark.asyncio
    async def test_analyze(self):
        """Test market analysis."""
        agent = MarketAnalystAgent()
        
        market_context = {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'indicators': {
                'rsi': 45,
                'ema_fast': 50100,
                'ema_slow': 49900,
                'macd': 50,
                'volume_ratio': 1.2
            },
            'trend': 'bullish',
            'volatility': 0.02,
            'price_change_pct': 0.5
        }
        
        result = await agent.analyze(market_context, risk_tolerance=0.7)
        
        assert 'decision' in result
        assert result['decision'] in ['BUY', 'SELL', 'HOLD']
        assert 'confidence' in result
        assert 0 <= result['confidence'] <= 1
        assert 'reasoning_chain' in result
    
    def test_identify_regime(self):
        """Test market regime identification."""
        agent = MarketAnalystAgent()
        
        context = {
            'indicators': {
                'rsi': 65,
                'ema_fast': 51000,
                'ema_slow': 49000,
                'volume_ratio': 1.5
            },
            'volatility': 0.025
        }
        
        regime = agent._identify_regime(context)
        
        assert regime in ['trending_up', 'trending_down', 'ranging', 'high_volatility', 'low_volatility']


class TestRiskAssessorAgent:
    """Test Risk Assessor Agent."""
    
    def test_initialization(self):
        """Test agent initialization."""
        agent = RiskAssessorAgent(max_position_size=0.1, max_leverage=3.0)
        
        assert agent.max_position_size == 0.1
        assert agent.max_leverage == 3.0
    
    def test_evaluate(self):
        """Test risk evaluation."""
        agent = RiskAssessorAgent()
        
        proposed_trade = {
            'action': 'BUY',
            'confidence': 0.8,
            'rationale': 'Strong bullish signal'
        }
        
        market_context = {
            'price': 50000.0,
            'indicators': {
                'rsi': 50,
                'volume_ratio': 1.1,
                'ema_fast': 50100,
                'ema_slow': 49900
            },
            'volatility': 0.02
        }
        
        portfolio = {
            'positions': [],
            'available_capital': 10000.0,
            'total_capital': 10000.0
        }
        
        result = agent.evaluate(proposed_trade, market_context, portfolio)
        
        assert 'risk_score' in result
        assert 0 <= result['risk_score'] <= 100
        assert 'recommended_position_size' in result
        assert result['recommended_position_size'] >= 0
        assert 'approved' in result
        assert isinstance(result['approved'], bool)
    
    def test_calculate_stop_loss(self):
        """Test stop loss calculation."""
        agent = RiskAssessorAgent()
        
        market_context = {
            'price': 50000.0,
            'volatility': 0.02
        }
        
        stop_loss_buy = agent.calculate_stop_loss(50000.0, 'BUY', market_context)
        stop_loss_sell = agent.calculate_stop_loss(50000.0, 'SELL', market_context)
        
        assert stop_loss_buy < 50000.0  # Stop below entry for BUY
        assert stop_loss_sell > 50000.0  # Stop above entry for SELL
    
    def test_calculate_take_profit(self):
        """Test take profit calculation."""
        agent = RiskAssessorAgent()
        
        market_context = {
            'price': 50000.0,
            'volatility': 0.02
        }
        
        tp_buy = agent.calculate_take_profit(50000.0, 'BUY', market_context, risk_reward=2.0)
        tp_sell = agent.calculate_take_profit(50000.0, 'SELL', market_context, risk_reward=2.0)
        
        assert tp_buy > 50000.0  # TP above entry for BUY
        assert tp_sell < 50000.0  # TP below entry for SELL


class TestPortfolioManagerAgent:
    """Test Portfolio Manager Agent."""
    
    def test_initialization(self):
        """Test agent initialization."""
        agent = PortfolioManagerAgent(max_assets=5, max_total_exposure=0.5)
        
        assert agent.max_assets == 5
        assert agent.max_total_exposure == 0.5
    
    def test_allocate(self):
        """Test capital allocation."""
        agent = PortfolioManagerAgent()
        
        trade_proposal = {
            'action': 'BUY',
            'confidence': 0.8,
            'recommended_position_size': 0.05
        }
        
        market_context = {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'trend_strength': 0.7
        }
        
        portfolio = {
            'positions': [],
            'available_capital': 10000.0,
            'total_capital': 10000.0
        }
        
        result = agent.allocate(trade_proposal, market_context, portfolio)
        
        assert 'approved' in result
        if result['approved']:
            assert 'size' in result
            assert 'amount' in result
            assert result['amount'] > 0
    
    def test_max_positions_limit(self):
        """Test maximum positions limit."""
        agent = PortfolioManagerAgent(max_assets=2)
        
        trade_proposal = {
            'action': 'BUY',
            'confidence': 0.8,
            'recommended_position_size': 0.05
        }
        
        market_context = {'symbol': 'BTC/USDT', 'price': 50000.0}
        
        # Portfolio with max positions
        portfolio = {
            'positions': [
                {'symbol': 'ETH/USDT', 'size': 0.1},
                {'symbol': 'SOL/USDT', 'size': 0.1}
            ],
            'available_capital': 8000.0,
            'total_capital': 10000.0
        }
        
        result = agent.allocate(trade_proposal, market_context, portfolio)
        
        assert result['approved'] is False
        assert result['reason'] == 'max_positions_reached'
    
    def test_select_next_asset(self):
        """Test asset selection."""
        agent = PortfolioManagerAgent()
        
        available_assets = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        
        market_conditions = {
            'BTC/USDT': {
                'indicators': {'rsi': 50, 'ema_fast': 50000, 'ema_slow': 49000, 'volume_ratio': 1.2},
                'volatility': 0.025
            },
            'ETH/USDT': {
                'indicators': {'rsi': 45, 'ema_fast': 3000, 'ema_slow': 2900, 'volume_ratio': 1.1},
                'volatility': 0.03
            },
            'SOL/USDT': {
                'indicators': {'rsi': 55, 'ema_fast': 100, 'ema_slow': 95, 'volume_ratio': 0.9},
                'volatility': 0.04
            }
        }
        
        portfolio = {
            'positions': [],
            'total_capital': 10000.0
        }
        
        selected = agent.select_next_asset(available_assets, market_conditions, portfolio)
        
        assert selected in available_assets


class TestExecutionAgent:
    """Test Execution Agent."""
    
    def test_initialization(self):
        """Test agent initialization."""
        agent = ExecutionAgent(default_strategy='adaptive')
        
        assert agent.default_strategy == 'adaptive'
    
    @pytest.mark.asyncio
    async def test_execute_simulation(self):
        """Test simulated execution."""
        agent = ExecutionAgent()
        
        allocation = {
            'approved': True,
            'symbol': 'BTC/USDT',
            'action': 'BUY',
            'size': 0.05,
            'amount': 500.0
        }
        
        market_context = {
            'price': 50000.0,
            'indicators': {'volume_ratio': 1.0},
            'volatility': 0.02
        }
        
        # Execute without exchange connector (simulation)
        result = await agent.execute(allocation, market_context)
        
        assert result['executed'] is True
        assert result['simulated'] is True
        assert 'order_id' in result
    
    def test_select_strategy(self):
        """Test strategy selection."""
        agent = ExecutionAgent(default_strategy='adaptive')
        
        # Large order in low volume should use TWAP
        allocation = {'size': 0.02}
        market_context = {
            'volatility': 0.02,
            'indicators': {'volume_ratio': 0.7}
        }
        
        strategy = agent._select_strategy(allocation, market_context)
        
        assert strategy in ['immediate', 'twap', 'limit', 'iceberg']
    
    def test_calculate_slippage(self):
        """Test slippage calculation."""
        agent = ExecutionAgent()
        
        # Buy slippage (paid more)
        slippage_buy = agent.calculate_slippage(50000.0, 50050.0, 'buy')
        assert slippage_buy > 0
        
        # Sell slippage (got less)
        slippage_sell = agent.calculate_slippage(50000.0, 49950.0, 'sell')
        assert slippage_sell > 0

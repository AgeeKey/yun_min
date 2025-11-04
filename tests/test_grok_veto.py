"""
Тесты для GrokVetoSystem

Используют mock для эмуляции Grok API без реальных запросов
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from yunmin.llm.grok_veto import GrokVetoSystem, SignalAnalysis


@pytest.fixture
def mock_grok_client():
    """Mock Grok API client"""
    with patch('yunmin.llm.grok_veto.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        yield mock_client


class TestSignalAnalysis:
    """Тесты SignalAnalysis dataclass"""
    
    def test_approved_signal(self):
        """Одобренный сигнал"""
        analysis = SignalAnalysis(
            approved=True,
            confidence=0.85,
            reasoning="Strong bullish signal with good risk/reward",
            risk_factors=[],
            market_condition_score=8.0,
            signal_quality_score=9.0,
            risk_reward_ratio=3.5
        )
        
        assert analysis.approved is True
        assert analysis.confidence == 0.85
        assert len(analysis.risk_factors) == 0
    
    def test_vetoed_signal(self):
        """Отклонённый сигнал"""
        analysis = SignalAnalysis(
            approved=False,
            confidence=0.4,
            reasoning="High volatility + weak signal = too risky",
            risk_factors=['HIGH_VOLATILITY', 'WEAK_CONFLUENCE'],
            market_condition_score=3.0,
            signal_quality_score=4.0,
            risk_reward_ratio=1.2
        )
        
        assert analysis.approved is False
        assert len(analysis.risk_factors) == 2
        assert 'HIGH_VOLATILITY' in analysis.risk_factors


class TestGrokVetoSystem:
    """Тесты GrokVetoSystem"""
    
    def test_initialization_with_api_key(self, mock_grok_client):
        """Инициализация с API ключом"""
        veto = GrokVetoSystem(
            api_key="test-key-12345",
            min_approval_confidence=0.7,
            max_risk_score=7.0
        )
        
        assert veto.api_key == "test-key-12345"
        assert veto.min_approval_confidence == 0.7
        assert veto.max_risk_score == 7.0
    
    def test_initialization_without_api_key_raises(self):
        """Ошибка при отсутствии API ключа"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError):
                GrokVetoSystem()
    
    def test_analyze_signal_approval(self, mock_grok_client):
        """Анализ с одобрением сигнала"""
        # Mock Grok response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
          "approved": true,
          "confidence": 0.85,
          "reasoning": "Strong trend + good volume = high probability setup",
          "risk_factors": [],
          "market_condition_score": 8.5,
          "signal_quality_score": 9.0,
          "risk_reward_ratio": 3.2
        }
        '''
        
        mock_grok_client.chat.completions.create.return_value = mock_response
        
        veto = GrokVetoSystem(api_key="test-key")
        
        analysis = veto.analyze_signal(
            symbol='BTC/USDT',
            side='buy',
            current_price=100000.0,
            signal_reason='RSI oversold + MACD crossover',
            market_data={
                'volume_24h': 1000000,
                'volatility': 'Medium',
                'trend': 'Bullish',
                'rsi': 35,
                'macd': 'Bullish'
            }
        )
        
        assert analysis.approved is True
        assert analysis.confidence == 0.85
        assert analysis.market_condition_score == 8.5
        assert len(analysis.risk_factors) == 0
    
    def test_analyze_signal_veto(self, mock_grok_client):
        """Анализ с veto"""
        # Mock Grok response с отказом
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
          "approved": false,
          "confidence": 0.45,
          "reasoning": "Extreme volatility + weak signal quality = too risky",
          "risk_factors": ["HIGH_VOLATILITY", "WEAK_SIGNAL", "LOW_VOLUME"],
          "market_condition_score": 3.0,
          "signal_quality_score": 4.5,
          "risk_reward_ratio": 1.1
        }
        '''
        
        mock_grok_client.chat.completions.create.return_value = mock_response
        
        veto = GrokVetoSystem(api_key="test-key")
        
        analysis = veto.analyze_signal(
            symbol='ETH/USDT',
            side='sell',
            current_price=4000.0,
            signal_reason='Resistance rejection',
            market_data={
                'volume_24h': 50000,
                'volatility': 'High',
                'trend': 'Choppy',
                'rsi': 68,
                'macd': 'Bearish'
            }
        )
        
        assert analysis.approved is False
        assert len(analysis.risk_factors) == 3
        assert 'HIGH_VOLATILITY' in analysis.risk_factors
    
    def test_analyze_signal_api_error(self, mock_grok_client):
        """Обработка ошибки API"""
        # Mock API error
        mock_grok_client.chat.completions.create.side_effect = Exception("API Error")
        
        veto = GrokVetoSystem(api_key="test-key")
        
        analysis = veto.analyze_signal(
            symbol='BTC/USDT',
            side='buy',
            current_price=100000.0,
            signal_reason='Test',
            market_data={}
        )
        
        # При ошибке должен вернуть veto
        assert analysis.approved is False
        assert analysis.confidence == 0.0
        assert 'API_ERROR' in analysis.risk_factors
    
    def test_parse_grok_response_json(self, mock_grok_client):
        """Парсинг JSON ответа"""
        veto = GrokVetoSystem(api_key="test-key")
        
        response = '''
        {
          "approved": true,
          "confidence": 0.9,
          "reasoning": "Excellent setup",
          "risk_factors": [],
          "market_condition_score": 9.0,
          "signal_quality_score": 8.5,
          "risk_reward_ratio": 4.0
        }
        '''
        
        analysis = veto._parse_grok_response(response)
        
        assert analysis.approved is True
        assert analysis.confidence == 0.9
        assert analysis.reasoning == "Excellent setup"
    
    def test_parse_grok_response_markdown_wrapped(self, mock_grok_client):
        """Парсинг JSON обёрнутого в markdown"""
        veto = GrokVetoSystem(api_key="test-key")
        
        response = '''```json
        {
          "approved": false,
          "confidence": 0.6,
          "reasoning": "Moderate risk",
          "risk_factors": ["MEDIUM_RISK"],
          "market_condition_score": 6.0,
          "signal_quality_score": 7.0,
          "risk_reward_ratio": 2.0
        }
        ```'''
        
        analysis = veto._parse_grok_response(response)
        
        assert analysis.approved is False
        assert analysis.confidence == 0.6
    
    def test_parse_grok_response_invalid_json(self, mock_grok_client):
        """Обработка невалидного JSON (fallback parsing)"""
        veto = GrokVetoSystem(api_key="test-key")
        
        response = "I approve this trade because the market looks bullish"
        
        analysis = veto._parse_grok_response(response)
        
        # Fallback парсинг по ключевым словам
        assert analysis.approved is True  # Есть "approve", нет "veto"
        assert 'PARSE_ERROR' in analysis.risk_factors
    
    def test_get_statistics(self, mock_grok_client):
        """Получение статистики"""
        veto = GrokVetoSystem(api_key="test-key")
        
        stats = veto.get_statistics()
        
        assert 'total_signals_analyzed' in stats
        assert 'approved' in stats
        assert 'vetoed' in stats


def test_integration_workflow(mock_grok_client):
    """Полный интеграционный workflow"""
    print("\n" + "=" * 80)
    print("ТЕСТ: Grok Veto System Integration")
    print("=" * 80)
    
    # Mock 2 разных ответа
    responses = [
        # Response 1: Approve BTC buy
        Mock(choices=[Mock(message=Mock(content='''
        {
          "approved": true,
          "confidence": 0.88,
          "reasoning": "Strong momentum + favorable market conditions",
          "risk_factors": [],
          "market_condition_score": 8.5,
          "signal_quality_score": 9.0,
          "risk_reward_ratio": 3.8
        }
        '''))]),
        
        # Response 2: Veto ETH sell
        Mock(choices=[Mock(message=Mock(content='''
        {
          "approved": false,
          "confidence": 0.35,
          "reasoning": "Counter-trend trade + high risk",
          "risk_factors": ["COUNTER_TREND", "HIGH_VOLATILITY"],
          "market_condition_score": 4.0,
          "signal_quality_score": 3.5,
          "risk_reward_ratio": 1.2
        }
        '''))])
    ]
    
    mock_grok_client.chat.completions.create.side_effect = responses
    
    veto = GrokVetoSystem(
        api_key="test-key",
        min_approval_confidence=0.7,
        max_risk_score=7.0
    )
    
    # Test 1: BTC buy approval
    print("\n1️⃣ Анализ BTC buy signal...")
    btc_analysis = veto.analyze_signal(
        symbol='BTC/USDT',
        side='buy',
        current_price=105000.0,
        signal_reason='Strong uptrend + RSI rebound',
        market_data={
            'volume_24h': 2000000,
            'volatility': 'Low',
            'trend': 'Bullish',
            'rsi': 45,
            'macd': 'Bullish'
        }
    )
    
    print(f"   Результат: {'✅ APPROVED' if btc_analysis.approved else '❌ VETO'}")
    print(f"   Confidence: {btc_analysis.confidence*100:.0f}%")
    print(f"   Reasoning: {btc_analysis.reasoning}")
    
    assert btc_analysis.approved is True
    assert btc_analysis.confidence >= 0.7
    
    # Test 2: ETH sell veto
    print("\n2️⃣ Анализ ETH sell signal...")
    eth_analysis = veto.analyze_signal(
        symbol='ETH/USDT',
        side='sell',
        current_price=3900.0,
        signal_reason='Top of range',
        market_data={
            'volume_24h': 100000,
            'volatility': 'High',
            'trend': 'Bullish',
            'rsi': 70,
            'macd': 'Bullish'
        }
    )
    
    print(f"   Результат: {'✅ APPROVED' if eth_analysis.approved else '❌ VETO'}")
    print(f"   Confidence: {eth_analysis.confidence*100:.0f}%")
    print(f"   Reasoning: {eth_analysis.reasoning}")
    print(f"   Risk Factors: {', '.join(eth_analysis.risk_factors)}")
    
    assert eth_analysis.approved is False
    assert len(eth_analysis.risk_factors) > 0
    
    print("\n✅ Integration workflow успешно завершён!")


if __name__ == '__main__':
    # Запустить интеграционный тест
    with patch('yunmin.llm.grok_veto.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        test_integration_workflow(mock_client)
    
    print("\n" + "=" * 80)
    print("🧪 Запуск всех unit тестов...")
    print("=" * 80)
    
    # Запустить pytest
    pytest.main([__file__, '-v'])

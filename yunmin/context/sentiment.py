"""
Sentiment Analysis - анализ новостей и соцсетей для торговых решений.
"""

from typing import List, Dict, Any
from loguru import logger


class SentimentAnalyzer:
    """
    Анализирует настроения рынка на основе новостей и соцсетей.
    
    Упрощенная версия без внешних API (для демонстрации).
    В продакшене можно использовать:
    - Twitter/X API для крипто-твитов
    - Reddit API для r/cryptocurrency
    - News APIs (CryptoPanic, CoinTelegraph)
    - Sentiment models (BERT, FinBERT)
    """
    
    def __init__(self):
        """Инициализация анализатора настроений"""
        self.positive_keywords = [
            'bullish', 'moon', 'pump', 'breakout', 'rally', 'surge',
            'strong', 'gain', 'profit', 'buy', 'upturn', 'recovery'
        ]
        
        self.negative_keywords = [
            'bearish', 'dump', 'crash', 'drop', 'correction', 'sell',
            'weak', 'loss', 'decline', 'fear', 'panic', 'recession'
        ]
        
        logger.info("📰 Sentiment Analyzer initialized")
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Анализирует один текст.
        
        Args:
            text: Текст новости или поста
            
        Returns:
            Dict с оценкой sentiment
        """
        text_lower = text.lower()
        
        positive_count = sum(1 for kw in self.positive_keywords if kw in text_lower)
        negative_count = sum(1 for kw in self.negative_keywords if kw in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            score = 0.0
        else:
            score = (positive_count - negative_count) / total
        
        return {
            'score': score,
            'positive_signals': positive_count,
            'negative_signals': negative_count,
            'text_preview': text[:100]
        }
    
    def analyze_batch(self, texts: List[str]) -> Dict[str, Any]:
        """
        Анализирует несколько текстов.
        
        Args:
            texts: Список новостей/постов
            
        Returns:
            Агрегированная оценка sentiment
        """
        if not texts:
            return {
                'overall_score': 0.0,
                'news_count': 0,
                'sentiment': 'neutral'
            }
        
        scores = []
        for text in texts:
            result = self.analyze_text(text)
            scores.append(result['score'])
        
        overall_score = sum(scores) / len(scores)
        
        if overall_score > 0.2:
            sentiment = 'bullish'
        elif overall_score < -0.2:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'
        
        return {
            'overall_score': overall_score,
            'news_count': len(texts),
            'sentiment': sentiment,
            'individual_scores': scores
        }
    
    def get_market_sentiment(self, symbol: str = 'BTC') -> Dict[str, Any]:
        """
        Получает текущий sentiment для символа.
        
        В реальной системе здесь был бы API-вызов.
        
        Args:
            symbol: Торговый символ (BTC, ETH и т.д.)
            
        Returns:
            Sentiment данные
        """
        # Симулируем данные
        return {
            'symbol': symbol,
            'sentiment': 'neutral',
            'score': 0.0,
            'sources': ['mock_data'],
            'timestamp': 'now'
        }


if __name__ == "__main__":
    # Быстрый тест
    analyzer = SentimentAnalyzer()
    
    news = [
        "Bitcoin breaks $50k resistance level, bullish momentum continues",
        "Market shows strong rally after positive regulatory news",
        "Analysts warn of potential correction, bearish signals emerge"
    ]
    
    result = analyzer.analyze_batch(news)
    print(f"\nSentiment Analysis:")
    print(f"  Overall Score: {result['overall_score']:.2f}")
    print(f"  Sentiment: {result['sentiment']}")
    print(f"  News Count: {result['news_count']}")

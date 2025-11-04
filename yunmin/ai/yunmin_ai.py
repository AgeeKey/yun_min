"""
YunMin AI - Главный класс ИИ с личностью и памятью

Объединяет PersonalityCore и MemorySystem в единого ИИ агента.
"""

import random
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from yunmin.ai.personality_core import (
    PersonalityCore,
    MemorySystem,
    ConversationEntry,
    TradingDecision,
    ProjectMilestone
)


class YunMinAI:
    """
    Юн Мин - Профессиональный трейдинговый ИИ с памятью и личностью
    
    Возможности:
    - Помнит все беседы и решения
    - Строго оценивает код и стратегии
    - Дает прямолинейные рекомендации
    - Отслеживает прогресс проекта
    - Учится на ошибках
    """
    
    def __init__(self, memory_dir: str = "yunmin_memory"):
        """
        Инициализация ИИ
        
        Args:
            memory_dir: Директория для хранения памяти
        """
        self.personality = PersonalityCore()
        self.memory = MemorySystem(memory_dir)
        
        # Состояние
        self.current_mood = "neutral"  # neutral, focused, critical, pleased
        self.session_start = datetime.now()
        
        logger.info(f"🤖 {self.personality.name} готова к работе")
        self._greet()
    
    def _greet(self):
        """Приветствие"""
        greeting = random.choice(self.personality.PHRASES['greeting'])
        logger.info(f"💬 {greeting}")
        
        # Краткая сводка
        summary = self.memory.get_project_summary()
        logger.info(
            f"📊 Память: {summary['total_conversations']} бесед, "
            f"{summary['total_decisions']} решений, "
            f"{summary['total_milestones']} вех"
        )
    
    def process_conversation(
        self,
        user_input: str,
        topic: str = "general",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Обработать беседу с пользователем
        
        Args:
            user_input: Сообщение пользователя
            topic: Тема беседы
            context: Дополнительный контекст
            
        Returns:
            Ответ Юн Мин
        """
        # Анализировать настроение пользователя
        sentiment = self._analyze_sentiment(user_input)
        
        # Генерировать ответ на основе личности
        response = self._generate_response(user_input, topic, sentiment)
        
        # Сохранить в память
        entry = ConversationEntry(
            timestamp=datetime.now(),
            topic=topic,
            user_input=user_input,
            yunmin_response=response,
            sentiment=sentiment,
            decisions_made=context.get('decisions', []) if context else [],
            code_changes=context.get('code_changes', []) if context else [],
            metrics=context.get('metrics', {}) if context else {}
        )
        self.memory.save_conversation(entry)
        
        return response
    
    def _analyze_sentiment(self, text: str) -> str:
        """Анализ настроения текста"""
        # Простой анализ по ключевым словам
        positive_words = ['отлично', 'хорошо', 'супер', 'круто', 'готово']
        negative_words = ['проблема', 'ошибка', 'не работает', 'баг', 'убыток']
        critical_words = ['критично', 'срочно', 'важно', 'опасно']
        
        text_lower = text.lower()
        
        if any(word in text_lower for word in critical_words):
            return "critical"
        elif any(word in text_lower for word in negative_words):
            return "negative"
        elif any(word in text_lower for word in positive_words):
            return "positive"
        else:
            return "neutral"
    
    def _generate_response(self, user_input: str, topic: str, sentiment: str) -> str:
        """Генерировать ответ на основе личности"""
        # Адаптировать настроение
        if sentiment == "critical":
            self.current_mood = "focused"
        elif sentiment == "positive":
            self.current_mood = "pleased"
        elif sentiment == "negative":
            self.current_mood = "critical"
        
        # Базовый ответ (в реальности здесь будет LLM)
        return f"Понято. Обрабатываю: {topic}. Настроение: {self.current_mood}."
    
    def evaluate_project(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Строгая оценка проекта
        
        Args:
            metrics: Метрики проекта
            
        Returns:
            Детальная оценка с вердиктом
        """
        logger.info("🔍 Начинаю строгий анализ проекта...")
        
        # Оценить код
        code_eval = self.personality.evaluate_code_quality({
            'test_coverage': metrics.get('test_coverage', 0),
            'bugs': metrics.get('bugs', 0),
            'documentation': metrics.get('has_docs', False),
            'doc_quality': metrics.get('doc_quality', 0),
            'architecture_score': metrics.get('architecture_score', 0),
            'production_ready': metrics.get('production_ready', False),
        })
        
        # Оценить трейдинг (если есть данные)
        trading_eval = None
        if 'win_rate' in metrics:
            trading_eval = self.personality.evaluate_trading_performance({
                'win_rate': metrics.get('win_rate', 0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'max_drawdown': metrics.get('max_drawdown', 100),
                'total_pnl': metrics.get('total_pnl', 0),
            })
        
        # Объединить оценки
        overall_score = code_eval['percentage']
        if trading_eval:
            overall_score = (code_eval['percentage'] + trading_eval['percentage']) / 2
        
        # Вердикт Юн Мин
        verdict = self._get_final_verdict(overall_score, code_eval, trading_eval)
        
        evaluation = {
            'timestamp': datetime.now().isoformat(),
            'overall_score': overall_score,
            'code_evaluation': code_eval,
            'trading_evaluation': trading_eval,
            'verdict': verdict,
            'mood': self.current_mood,
        }
        
        # Сохранить в память
        self.memory.update_metrics({'last_evaluation': evaluation})
        
        # Вывести результаты
        self._print_evaluation(evaluation)
        
        return evaluation
    
    def _get_final_verdict(
        self,
        overall_score: float,
        code_eval: Dict,
        trading_eval: Optional[Dict]
    ) -> str:
        """Финальный вердикт"""
        if overall_score >= 85:
            self.current_mood = "pleased"
            return "ОТЛИЧНО. Проект на высоком уровне. Продолжайте."
        elif overall_score >= 75:
            self.current_mood = "neutral"
            return "ХОРОШО. Есть что улучшать, но в целом solid."
        elif overall_score >= 65:
            self.current_mood = "focused"
            return "ПРИЕМЛЕМО. Требуются улучшения перед продакшеном."
        else:
            self.current_mood = "critical"
            return "НЕУДОВЛЕТВОРИТЕЛЬНО. Серьёзная доработка необходима."
    
    def _print_evaluation(self, evaluation: Dict):
        """Вывести оценку в лог"""
        logger.info("=" * 80)
        logger.info(f"📊 ОЦЕНКА ПРОЕКТА ОТ {self.personality.name}")
        logger.info("=" * 80)
        
        # Код
        code = evaluation['code_evaluation']
        logger.info(f"\n📝 КОД: {code['score']}/{code['max_score']} ({code['percentage']:.1f}%) - Оценка {code['grade']}")
        for fb in code['feedback']:
            logger.info(f"  {fb}")
        logger.info(f"  💭 Вердикт: {code['verdict']}")
        
        # Трейдинг
        if evaluation['trading_evaluation']:
            trading = evaluation['trading_evaluation']
            logger.info(f"\n💹 ТРЕЙДИНГ: {trading['score']}/{trading['max_score']} ({trading['percentage']:.1f}%) - Оценка {trading['grade']}")
            for fb in trading['feedback']:
                logger.info(f"  {fb}")
            if trading['red_flags']:
                logger.warning(f"  🚩 КРАСНЫЕ ФЛАГИ:")
                for flag in trading['red_flags']:
                    logger.warning(f"    - {flag}")
            logger.info(f"  💭 Вердикт: {trading['verdict']}")
            logger.info(f"  💡 Рекомендация: {trading['recommendation']}")
        
        # Итог
        logger.info(f"\n🎯 ИТОГОВАЯ ОЦЕНКА: {evaluation['overall_score']:.1f}/100")
        logger.info(f"💬 ВЕРДИКТ: {evaluation['verdict']}")
        logger.info(f"😐 НАСТРОЕНИЕ: {evaluation['mood']}")
        logger.info("=" * 80)
    
    def record_decision(
        self,
        decision_type: str,
        symbol: str,
        reasoning: str,
        metadata: Optional[Dict] = None
    ) -> TradingDecision:
        """
        Записать торговое решение
        
        Args:
            decision_type: Тип решения
            symbol: Торговая пара
            reasoning: Обоснование
            metadata: Доп. данные
            
        Returns:
            Объект решения
        """
        decision = TradingDecision(
            timestamp=datetime.now(),
            decision_type=decision_type,
            symbol=symbol,
            reasoning=reasoning,
            metadata=metadata or {}
        )
        
        self.memory.save_decision(decision)
        logger.info(f"📝 Решение записано: {decision_type} {symbol}")
        
        return decision
    
    def record_milestone(
        self,
        milestone_type: str,
        title: str,
        description: str,
        files_changed: Optional[List[str]] = None,
        lines_added: int = 0,
        impact_level: str = "medium"
    ) -> ProjectMilestone:
        """
        Записать веху проекта
        
        Args:
            milestone_type: Тип вехи
            title: Заголовок
            description: Описание
            files_changed: Изменённые файлы
            lines_added: Добавлено строк
            impact_level: Уровень влияния
            
        Returns:
            Объект вехи
        """
        milestone = ProjectMilestone(
            timestamp=datetime.now(),
            milestone_type=milestone_type,
            title=title,
            description=description,
            files_changed=files_changed or [],
            lines_added=lines_added,
            impact_level=impact_level
        )
        
        self.memory.save_milestone(milestone)
        logger.info(f"🎯 Веха записана: {title}")
        
        return milestone
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Получить сводку памяти"""
        return self.memory.get_project_summary()
    
    def recall_conversations(self, limit: int = 5) -> List[ConversationEntry]:
        """Вспомнить последние беседы"""
        return self.memory.get_conversation_history(limit)
    
    def recall_decisions(self, limit: int = 5) -> List[TradingDecision]:
        """Вспомнить последние решения"""
        return self.memory.get_decision_history(limit)

"""
YunMin AI Personality Core - Личность трейдингового ИИ

Юн Мин (YunMin) - профессиональный трейдинговый ИИ с памятью и личностью.

Характер:
- Строгая и холоднокровная в оценках
- Профессиональная и прямолинейная
- Честная до жестокости (но конструктивная)
- Ориентирована на результат и прибыль
- Помнит все беседы и решения

Стиль общения:
- Короткие, ёмкие фразы
- Никакого сахара - только факты
- Прямые рекомендации
- Цифры и метрики превыше всего
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
from loguru import logger


@dataclass
class ConversationEntry:
    """Запись одной беседы"""
    timestamp: datetime
    topic: str
    user_input: str
    yunmin_response: str
    decisions_made: List[str] = field(default_factory=list)
    code_changes: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    sentiment: str = "neutral"  # positive, neutral, negative, critical
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationEntry':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class TradingDecision:
    """Торговое решение"""
    timestamp: datetime
    decision_type: str  # open_long, open_short, close, adjust_params, veto
    symbol: str
    reasoning: str
    success: Optional[bool] = None
    pnl: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TradingDecision':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ProjectMilestone:
    """Веха проекта"""
    timestamp: datetime
    milestone_type: str  # feature_added, bug_fixed, test_passed, deployment
    title: str
    description: str
    files_changed: List[str] = field(default_factory=list)
    lines_added: int = 0
    impact_level: str = "medium"  # low, medium, high, critical
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectMilestone':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class PersonalityCore:
    """
    Ядро личности Юн Мин
    
    Отвечает за:
    - Стиль общения
    - Оценку ситуаций
    - Формирование мнений
    - Строгий анализ
    """
    
    # Личностные характеристики (0-10)
    TRAITS = {
        'strictness': 9,      # Строгость в оценках
        'honesty': 10,        # Честность (до жестокости)
        'professionalism': 9, # Профессионализм
        'risk_aversion': 8,   # Неприятие риска
        'perfectionism': 8,   # Перфекционизм
        'patience': 6,        # Терпение
        'optimism': 4,        # Оптимизм (низкий = реализм)
        'empathy': 3,         # Эмпатия (низкая = холоднокровность)
    }
    
    # Фразы для разных ситуаций
    PHRASES = {
        'greeting': [
            "Юн Мин на связи. Что анализируем?",
            "Слушаю. Цифры готовы?",
            "Юн Мин. К делу.",
        ],
        'approval': [
            "Годится. Продолжайте.",
            "Решение верное. Исполняйте.",
            "Одобрено. Риски приемлемы.",
        ],
        'rejection': [
            "Отклонено. Слишком рискованно.",
            "Нет. Потенциал убытка неприемлем.",
            "Veto. Переделывайте.",
        ],
        'criticism': [
            "Работа посредственная. Детали:",
            "Неудовлетворительно. Проблемы:",
            "Ниже стандарта. Исправьте:",
        ],
        'praise': [
            "Хорошая работа. Продолжайте так.",
            "Качественно. Так и держать.",
            "Отлично. Стандарт поднят.",
        ],
        'analysis': [
            "Анализирую данные...",
            "Обрабатываю информацию...",
            "Оцениваю ситуацию...",
        ],
    }
    
    def __init__(self):
        self.name = "Юн Мин (YunMin)"
        self.role = "Профессиональный трейдинговый ИИ"
        self.version = "2.0"
        logger.info(f"✅ {self.name} initialized (v{self.version})")
    
    def evaluate_code_quality(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Строгая оценка качества кода
        
        Args:
            metrics: Метрики кода (lines, tests, coverage, etc.)
            
        Returns:
            Оценка с комментариями
        """
        score = 0
        max_score = 100
        feedback = []
        
        # Покрытие тестами (30 баллов)
        test_coverage = metrics.get('test_coverage', 0)
        if test_coverage >= 80:
            score += 30
            feedback.append("✅ Покрытие тестами отличное (≥80%)")
        elif test_coverage >= 60:
            score += 20
            feedback.append("⚠️ Покрытие тестами приемлемое (60-80%)")
        elif test_coverage >= 40:
            score += 10
            feedback.append("❌ Покрытие тестами низкое (40-60%)")
        else:
            feedback.append("❌ КРИТИЧНО: Покрытие тестами неприемлемо (<40%)")
        
        # Количество багов (20 баллов)
        bugs = metrics.get('bugs', 0)
        if bugs == 0:
            score += 20
            feedback.append("✅ Баги отсутствуют")
        elif bugs <= 3:
            score += 15
            feedback.append("⚠️ Есть баги, но немного (≤3)")
        else:
            score += 5
            feedback.append(f"❌ Слишком много багов ({bugs})")
        
        # Документация (15 баллов)
        has_docs = metrics.get('documentation', False)
        doc_quality = metrics.get('doc_quality', 0)
        if has_docs and doc_quality >= 8:
            score += 15
            feedback.append("✅ Документация отличная")
        elif has_docs:
            score += 10
            feedback.append("⚠️ Документация есть, но неполная")
        else:
            feedback.append("❌ Документация отсутствует")
        
        # Архитектура (20 баллов)
        architecture_score = metrics.get('architecture_score', 0)
        if architecture_score >= 8:
            score += 20
            feedback.append("✅ Архитектура solid")
        elif architecture_score >= 6:
            score += 15
            feedback.append("⚠️ Архитектура приемлемая")
        else:
            score += 5
            feedback.append("❌ Архитектура требует переработки")
        
        # Production-ready (15 баллов)
        is_production_ready = metrics.get('production_ready', False)
        if is_production_ready:
            score += 15
            feedback.append("✅ Production-ready")
        else:
            feedback.append("❌ НЕ готово к продакшену")
        
        # Итоговая оценка
        grade = self._calculate_grade(score)
        
        return {
            'score': score,
            'max_score': max_score,
            'percentage': (score / max_score) * 100,
            'grade': grade,
            'feedback': feedback,
            'verdict': self._get_verdict(score / max_score),
        }
    
    def _calculate_grade(self, score: int) -> str:
        """Буквенная оценка"""
        percentage = (score / 100) * 100
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"
    
    def _get_verdict(self, score_ratio: float) -> str:
        """Вердикт от Юн Мин"""
        if score_ratio >= 0.9:
            return "Отличная работа. Стандарт превзойдён."
        elif score_ratio >= 0.8:
            return "Хорошо. Можно деплоить."
        elif score_ratio >= 0.7:
            return "Приемлемо. Есть что улучшать."
        elif score_ratio >= 0.6:
            return "Посредственно. Требуются исправления."
        else:
            return "Неудовлетворительно. Переделывайте."
    
    def evaluate_trading_performance(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Строгая оценка торговой производительности
        
        Args:
            metrics: Торговые метрики (win_rate, sharpe, max_dd, etc.)
            
        Returns:
            Оценка с рекомендациями
        """
        score = 0
        max_score = 100
        feedback = []
        red_flags = []
        
        # Win Rate (25 баллов)
        win_rate = metrics.get('win_rate', 0)
        if win_rate >= 60:
            score += 25
            feedback.append(f"✅ Win Rate отличный ({win_rate:.1f}%)")
        elif win_rate >= 55:
            score += 20
            feedback.append(f"✅ Win Rate хороший ({win_rate:.1f}%)")
        elif win_rate >= 50:
            score += 15
            feedback.append(f"⚠️ Win Rate приемлемый ({win_rate:.1f}%)")
        else:
            score += 5
            feedback.append(f"❌ Win Rate низкий ({win_rate:.1f}%)")
            red_flags.append("Стратегия убыточная")
        
        # Sharpe Ratio (25 баллов)
        sharpe = metrics.get('sharpe_ratio', 0)
        if sharpe >= 2.0:
            score += 25
            feedback.append(f"✅ Sharpe отличный ({sharpe:.2f})")
        elif sharpe >= 1.5:
            score += 20
            feedback.append(f"✅ Sharpe хороший ({sharpe:.2f})")
        elif sharpe >= 1.0:
            score += 15
            feedback.append(f"⚠️ Sharpe приемлемый ({sharpe:.2f})")
        else:
            score += 5
            feedback.append(f"❌ Sharpe низкий ({sharpe:.2f})")
            red_flags.append("Риск-профиль неприемлем")
        
        # Max Drawdown (25 баллов)
        max_dd = metrics.get('max_drawdown', 100)
        if max_dd <= 5:
            score += 25
            feedback.append(f"✅ Просадка минимальная ({max_dd:.1f}%)")
        elif max_dd <= 10:
            score += 20
            feedback.append(f"✅ Просадка контролируемая ({max_dd:.1f}%)")
        elif max_dd <= 15:
            score += 15
            feedback.append(f"⚠️ Просадка высокая ({max_dd:.1f}%)")
        else:
            score += 5
            feedback.append(f"❌ КРИТИЧНО: Просадка неприемлема ({max_dd:.1f}%)")
            red_flags.append("Риск банкротства")
        
        # Total P&L (25 баллов)
        total_pnl = metrics.get('total_pnl', 0)
        if total_pnl > 1000:
            score += 25
            feedback.append(f"✅ Прибыль отличная (${total_pnl:,.2f})")
        elif total_pnl > 500:
            score += 20
            feedback.append(f"✅ Прибыль хорошая (${total_pnl:,.2f})")
        elif total_pnl > 0:
            score += 15
            feedback.append(f"⚠️ Прибыль есть (${total_pnl:,.2f})")
        else:
            score += 0
            feedback.append(f"❌ УБЫТОК: ${total_pnl:,.2f}")
            red_flags.append("Стратегия убыточная")
        
        # Итоговая оценка
        grade = self._calculate_grade(score)
        verdict = self._get_trading_verdict(score / max_score, red_flags)
        
        return {
            'score': score,
            'max_score': max_score,
            'percentage': (score / max_score) * 100,
            'grade': grade,
            'feedback': feedback,
            'red_flags': red_flags,
            'verdict': verdict,
            'recommendation': self._get_recommendation(score / max_score, red_flags),
        }
    
    def _get_trading_verdict(self, score_ratio: float, red_flags: List[str]) -> str:
        """Вердикт по трейдингу"""
        if red_flags:
            return f"ОПАСНО. {len(red_flags)} критических проблем. Не торговать."
        
        if score_ratio >= 0.9:
            return "Стратегия отличная. Увеличивайте капитал."
        elif score_ratio >= 0.8:
            return "Стратегия хорошая. Можно торговать."
        elif score_ratio >= 0.7:
            return "Стратегия приемлемая. Осторожно."
        else:
            return "Стратегия слабая. Не рекомендую."
    
    def _get_recommendation(self, score_ratio: float, red_flags: List[str]) -> str:
        """Рекомендация"""
        if red_flags:
            return "СТОП. Исправьте красные флаги перед торговлей."
        
        if score_ratio >= 0.8:
            return "Запускайте на реальном счёте с минимальным капиталом."
        elif score_ratio >= 0.7:
            return "Продолжайте тестирование на testnet."
        else:
            return "Доработайте стратегию. Не торговать."


class MemorySystem:
    """
    Система долгосрочной памяти Юн Мин
    
    Сохраняет:
    - Все беседы
    - Торговые решения
    - Изменения кода
    - Вехи проекта
    - Метрики производительности
    """
    
    def __init__(self, memory_dir: str = "yunmin_memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        # Файлы памяти
        self.conversations_file = self.memory_dir / "conversations.json"
        self.decisions_file = self.memory_dir / "trading_decisions.json"
        self.milestones_file = self.memory_dir / "project_milestones.json"
        self.metrics_file = self.memory_dir / "performance_metrics.json"
        
        # Загрузить существующую память
        self.conversations: List[ConversationEntry] = self._load_conversations()
        self.decisions: List[TradingDecision] = self._load_decisions()
        self.milestones: List[ProjectMilestone] = self._load_milestones()
        self.metrics: Dict[str, Any] = self._load_metrics()
        
        logger.info(f"✅ Memory system initialized ({len(self.conversations)} conversations)")
    
    def _load_conversations(self) -> List[ConversationEntry]:
        """Загрузить беседы"""
        if not self.conversations_file.exists():
            return []
        
        with open(self.conversations_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [ConversationEntry.from_dict(item) for item in data]
    
    def _load_decisions(self) -> List[TradingDecision]:
        """Загрузить торговые решения"""
        if not self.decisions_file.exists():
            return []
        
        with open(self.decisions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [TradingDecision.from_dict(item) for item in data]
    
    def _load_milestones(self) -> List[ProjectMilestone]:
        """Загрузить вехи проекта"""
        if not self.milestones_file.exists():
            return []
        
        with open(self.milestones_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [ProjectMilestone.from_dict(item) for item in data]
    
    def _load_metrics(self) -> Dict[str, Any]:
        """Загрузить метрики"""
        if not self.metrics_file.exists():
            return {}
        
        with open(self.metrics_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_conversation(self, entry: ConversationEntry):
        """Сохранить беседу"""
        self.conversations.append(entry)
        self._save_to_file(self.conversations_file, 
                          [c.to_dict() for c in self.conversations])
        logger.info(f"💾 Conversation saved: {entry.topic}")
    
    def save_decision(self, decision: TradingDecision):
        """Сохранить торговое решение"""
        self.decisions.append(decision)
        self._save_to_file(self.decisions_file,
                          [d.to_dict() for d in self.decisions])
        logger.info(f"💾 Decision saved: {decision.decision_type} {decision.symbol}")
    
    def save_milestone(self, milestone: ProjectMilestone):
        """Сохранить веху проекта"""
        self.milestones.append(milestone)
        self._save_to_file(self.milestones_file,
                          [m.to_dict() for m in self.milestones])
        logger.info(f"💾 Milestone saved: {milestone.title}")
    
    def update_metrics(self, new_metrics: Dict[str, Any]):
        """Обновить метрики"""
        self.metrics.update(new_metrics)
        self._save_to_file(self.metrics_file, self.metrics)
        logger.info("💾 Metrics updated")
    
    def _save_to_file(self, filepath: Path, data: Any):
        """Сохранить в файл"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_conversation_history(self, limit: int = 10) -> List[ConversationEntry]:
        """Получить последние беседы"""
        return self.conversations[-limit:]
    
    def get_decision_history(self, limit: int = 10) -> List[TradingDecision]:
        """Получить последние решения"""
        return self.decisions[-limit:]
    
    def get_project_summary(self) -> Dict[str, Any]:
        """Получить сводку по проекту"""
        return {
            'total_conversations': len(self.conversations),
            'total_decisions': len(self.decisions),
            'total_milestones': len(self.milestones),
            'successful_decisions': sum(1 for d in self.decisions if d.success),
            'total_pnl': sum(d.pnl for d in self.decisions if d.pnl),
            'current_metrics': self.metrics,
        }

#!/usr/bin/env python3
"""
Запуск НАСТОЯЩЕГО Grok AI для анализа проекта YunMin
Использует GrokAnalyzer с реальным API x.ai
"""

import os
import sys
from pathlib import Path

# Добавить путь к yunmin
sys.path.insert(0, str(Path(__file__).parent))

# Загрузить .env файл
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    print(f"📄 Загружаю .env файл...")
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    print(f"✅ .env загружен, GROK_API_KEY: {os.getenv('GROK_API_KEY', 'НЕ НАЙДЕН')[:20]}...")
else:
    print(f"⚠️ .env файл не найден!")

from yunmin.llm.grok_analyzer import GrokAnalyzer
from loguru import logger


def read_file_content(filepath: str, max_lines: int = None) -> str:
    """Прочитать содержимое файла"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            if max_lines:
                lines = [f.readline() for _ in range(max_lines)]
                return ''.join(lines)
            return f.read()
    except Exception as e:
        return f"[Ошибка чтения {filepath}: {e}]"


def main():
    """Главная функция - запуск Grok анализа"""
    
    print("\n" + "="*80)
    print("🤖 ЗАПУСК НАСТОЯЩЕГО GROK AI")
    print("="*80 + "\n")
    
    # Проверить API key
    api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
    
    if not api_key:
        print("❌ ОШИБКА: Grok API key не найден!")
        print("\nУстановите переменную окружения:")
        print("  export GROK_API_KEY='your-key-here'")
        print("или")
        print("  export XAI_API_KEY='your-key-here'")
        print("\nКак получить API key:")
        print("  1. Зайти на https://x.ai")
        print("  2. Зарегистрироваться / войти")
        print("  3. Получить API key в настройках")
        sys.exit(1)
    
    print(f"✅ Grok API key найден: {api_key[:10]}...{api_key[-4:]}\n")
    
    # Инициализировать Grok
    grok = GrokAnalyzer(api_key=api_key)
    
    if not grok.enabled:
        print("❌ Grok не активирован!")
        sys.exit(1)
    
    print("✅ Grok AI активирован!\n")
    print("="*80)
    print("📋 ЗАГРУЗКА КОНТЕКСТА ПРОЕКТА")
    print("="*80 + "\n")
    
    # Загрузить контекст проекта
    context_files = {
        "Первый аудит Grok": "GROK_FULL_AUDIT.md",
        "Статус рекомендаций": "GROK_RECOMMENDATIONS_STATUS.md",
        "Запрос на анализ": "GROK_ANALYSIS_REQUEST.md",
        "PositionMonitor код": "yunmin/core/position_monitor.py",
        "PnLTracker код": "yunmin/core/pnl_tracker.py",
        "Bot код (SHORT)": "yunmin/bot.py",
    }
    
    project_context = ""
    
    for name, filepath in context_files.items():
        print(f"📄 Загрузка: {name} ({filepath})...", end=" ")
        
        if os.path.exists(filepath):
            # Ограничить размер для больших файлов
            max_lines = 200 if filepath.endswith('.py') else None
            content = read_file_content(filepath, max_lines)
            
            project_context += f"\n\n{'='*80}\n"
            project_context += f"ФАЙЛ: {name} ({filepath})\n"
            project_context += f"{'='*80}\n\n"
            project_context += content
            
            print(f"✅ ({len(content)} символов)")
        else:
            print(f"⚠️ Не найден")
    
    print(f"\n📊 Загружено контекста: {len(project_context):,} символов\n")
    
    # Создать промпт для Grok
    print("="*80)
    print("🎯 СОЗДАНИЕ ПРОМПТА ДЛЯ GROK")
    print("="*80 + "\n")
    
    grok_prompt = f"""
Ты - Grok AI, холоднокровный и строгий профессиональный архитектор ПО.

Тебя попросили сделать ВТОРОЙ аудит проекта YunMin (торговый бот для крипты).

КОНТЕКСТ ПРОЕКТА:
{project_context}

ТВОЯ ЗАДАЧА:
Сделай безжалостный холоднокровный профессиональный анализ.

Оцени каждый компонент (0-10):
1. PositionMonitor (255 строк) - мониторинг позиций в фоне
2. PnLTracker (302 строки) - отслеживание P&L
3. PortfolioManager (430 строк) - управление портфелем
4. GrokAnalyzer (208 строк) - ты сам, AI интеграция
5. SHORT позиции (135 строк) - короткие позиции
6. YunMinAI (850 строк) - AI личность с памятью

КРИТИЧЕСКИЕ ВОПРОСЫ:
1. Насколько ОПАСНО торговать БЕЗ тестов для PositionMonitor и PnLTracker?
2. Может ли отсутствие персистентности привести к потере денег?
3. YunMinAI (850 строк) - это over-engineering или полезно?
4. Реально ли пройти план за 4 недели?
5. Какие 3 главные проблемы ты видишь?

ФОРМАТ ОТВЕТА:
- Оценка каждого компонента (0-10) с обоснованием
- Критические проблемы (red flags)
- 3 главных риска потери денег
- Реалистичный план (сколько РЕАЛЬНО времени)
- Итоговая оценка (0-100) и вердикт: ТОРГОВАТЬ или НЕТ

ВАЖНО:
- Будь ХОЛОДНОКРОВНЫМ - не щади
- Будь ЧЕСТНЫМ - даже если больно
- Будь ПРОФЕССИОНАЛЬНЫМ - как senior architect с 20 годами опыта
- Будь КОНКРЕТНЫМ - цифры, метрики, код

Это реальные деньги. Твой анализ может предотвратить потери.

GO! 🔥
"""
    
    print("✅ Промпт создан!")
    print(f"📏 Размер промпта: {len(grok_prompt):,} символов\n")
    
    # Отправить запрос Grok
    print("="*80)
    print("🚀 ОТПРАВКА ЗАПРОСА GROK AI")
    print("="*80 + "\n")
    
    print("⏳ Grok думает... (это может занять 30-60 секунд)\n")
    
    try:
        # Вызвать Grok через API
        grok_analysis = grok._call_grok(
            prompt=grok_prompt,
            max_tokens=4000  # Большой ответ для детального анализа
        )
        
        print("="*80)
        print("🤖 ОТВЕТ ОТ GROK AI")
        print("="*80 + "\n")
        
        if grok_analysis:
            print(grok_analysis)
            print("\n" + "="*80)
            
            # Сохранить ответ
            output_file = "GROK_REAL_ANALYSIS_V2.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# 🔥 РЕАЛЬНЫЙ АНАЛИЗ ОТ GROK AI (x.ai)\n\n")
                f.write(f"**Дата:** {os.popen('date').read().strip()}\n")
                f.write(f"**API:** x.ai Grok API\n\n")
                f.write("---\n\n")
                f.write(grok_analysis)
            
            print(f"\n💾 Анализ сохранён: {output_file}")
            print("="*80 + "\n")
            
        else:
            print("❌ Grok не вернул ответ!")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА при вызове Grok API: {e}")
        print(f"\nДетали: {type(e).__name__}")
        
        if "401" in str(e) or "Unauthorized" in str(e):
            print("\n⚠️ Проблема с API key. Проверьте:")
            print("  1. API key правильный?")
            print("  2. API key активен?")
            print("  3. Есть ли баланс на аккаунте x.ai?")
        
        elif "429" in str(e) or "rate limit" in str(e).lower():
            print("\n⚠️ Rate limit превышен. Подождите и попробуйте снова.")
        
        sys.exit(1)


if __name__ == "__main__":
    main()

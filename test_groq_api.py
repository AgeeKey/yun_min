"""
Тест Groq API - проверка доступа и остатка кредитов
"""
import os
from groq import Groq

def test_groq_api():
    """Проверяет работоспособность Groq API"""
    
    # Проверяем наличие API ключа
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY не найден в переменных окружения")
        print("\nДобавьте ключ одним из способов:")
        print("1. Windows PowerShell: $env:GROQ_API_KEY='ваш_ключ'")
        print("2. Или создайте файл .env с GROQ_API_KEY=ваш_ключ")
        return False
    
    print(f"✅ API ключ найден: {api_key[:20]}...")
    
    try:
        # Создаем клиент
        client = Groq(api_key=api_key)
        print("✅ Groq клиент создан успешно")
        
        # Пробуем простой запрос (самая быстрая модель)
        print("\n🔄 Отправляю тестовый запрос...")
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Самая быстрая и дешевая модель
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Hello' in one word"
                }
            ],
            max_tokens=10,
            temperature=0
        )
        
        # Выводим результат
        answer = response.choices[0].message.content
        print(f"✅ Ответ получен: '{answer}'")
        
        # Проверяем использование токенов
        usage = response.usage
        print(f"\n📊 Использование токенов:")
        print(f"   - Prompt: {usage.prompt_tokens}")
        print(f"   - Completion: {usage.completion_tokens}")
        print(f"   - Всего: {usage.total_tokens}")
        
        # Пробуем второй запрос для анализа трейдинга
        print("\n🔄 Тестирую анализ трейдинга...")
        
        trading_response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a crypto trading expert. Answer in 2-3 short sentences."
                },
                {
                    "role": "user",
                    "content": "What's the key risk in crypto swing trading?"
                }
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        trading_answer = trading_response.choices[0].message.content
        print(f"✅ Ответ AI трейдера:\n{trading_answer}")
        
        trading_usage = trading_response.usage
        print(f"\n📊 Использование токенов:")
        print(f"   - Prompt: {trading_usage.prompt_tokens}")
        print(f"   - Completion: {trading_usage.completion_tokens}")
        print(f"   - Всего: {trading_usage.total_tokens}")
        
        print("\n" + "="*60)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("="*60)
        print(f"Ваш Groq API работает отлично!")
        print(f"Использовано токенов: {usage.total_tokens + trading_usage.total_tokens}")
        print(f"\nБесплатный лимит Groq: 14,400 запросов/день")
        print(f"Скорость: ~500-800 токенов/секунду")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ ОШИБКА: {error_msg}")
        
        # Анализ типичных ошибок
        if "rate_limit" in error_msg.lower():
            print("\n⚠️  Превышен лимит запросов")
            print("   Бесплатный лимит: 14,400 запросов/день")
            print("   Подождите до следующего дня (UTC)")
            
        elif "invalid_api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            print("\n⚠️  Проблема с API ключом")
            print("   Проверьте ключ на: https://console.groq.com/keys")
            
        elif "quota" in error_msg.lower() or "credits" in error_msg.lower():
            print("\n⚠️  Кредиты закончились")
            print("   Groq дает бесплатно 14,400 запросов/день")
            print("   Лимит обновляется каждые 24 часа (UTC)")
            
        else:
            print("\n⚠️  Неизвестная ошибка")
            print("   Полный текст ошибки см. выше")
        
        return False

def check_groq_installation():
    """Проверяет установлен ли пакет groq"""
    try:
        import groq
        print(f"✅ Пакет groq установлен (версия: {groq.__version__ if hasattr(groq, '__version__') else 'неизвестна'})")
        return True
    except ImportError:
        print("❌ Пакет groq не установлен")
        print("\nУстановите: pip install groq")
        return False

if __name__ == "__main__":
    print("="*60)
    print("ТЕСТ GROQ API")
    print("="*60)
    print()
    
    # Сначала проверяем установку
    if not check_groq_installation():
        exit(1)
    
    print()
    
    # Затем тестируем API
    success = test_groq_api()
    
    if not success:
        print("\n💡 Что попробовать:")
        print("1. Проверить API ключ: https://console.groq.com/keys")
        print("2. Убедиться что не превышен дневной лимит (14,400 req/day)")
        print("3. Подождать до завтра если лимит исчерпан")
        print("4. Создать новый API ключ если текущий не работает")
        exit(1)
    else:
        print("\n🚀 Готово использовать Groq для анализа стратегий!")

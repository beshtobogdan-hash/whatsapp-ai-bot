import requests
import time
import os 
import threading
from flask import Flask
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Загружаем переменные из .env
load_dotenv()

# Создаем Flask приложение
app = Flask(__name__)

# Маршруты для Render
@app.route('/')
def home():
    return "Бот-ассистент Богдана активен | Режим: автоответчик при оффлайне", 200

@app.route('/ping')
def ping():
    return "Pong! Bot is alive", 200

@app.route('/status')
def status():
    return f"""
    <h3>🤖 Бот-ассистент Богдана</h3>
    <p>Статус: <span style='color:green'>✅ Активен</span></p>
    <p>Режим: Отвечает когда Богдан оффлайн в WhatsApp</p>
    <p>Номер: +79994929247</p>
    <p>Время сервера: {datetime.now().strftime('%H:%M:%S')}</p>
    """, 200

# --- ТВОИ ДАННЫЕ ИЗ .env ---
GREEN_ID = os.getenv("GREEN_ID")
GREEN_TOKEN = os.getenv("GREEN_TOKEN")
FOLDER_ID = os.getenv("FOLDER_ID")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

# ТВОЙ НОМЕР WhatsApp
MY_PHONE_NUMBER = "79994929247"  # Без + и @c.us
MY_CHAT_ID = f"{MY_PHONE_NUMBER}@c.us"

# Проверяем, что все переменные загружены
if not all([GREEN_ID, GREEN_TOKEN, FOLDER_ID, YANDEX_API_KEY]):
    print("❌ ОШИБКА: Не все переменные окружения загружены!")
    exit(1)

# Глобальные переменные для отслеживания статуса
last_online_time = None
user_status_cache = {}  # Кэш статусов пользователей

print("=" * 60)
print("🤖 БОТ-АССИСТЕНТ БОГДАНА")
print(f"📱 Мой номер: +{MY_PHONE_NUMBER}")
print("⚡ Режим: Отвечает ТОЛЬКО когда я оффлайн в WhatsApp")
print("=" * 60)

def get_yandex_gpt_answer(text, sender_name=""):
    """Запрос к YandexGPT - ассистент Богдана."""
    print(f"[AI] Запрос от {sender_name}: {text[:50]}...")
    
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Промпт для ассистента
    system_prompt = """Ты ассистент Богдана. Богдан сейчас не в сети в WhatsApp, и ты временно отвечаешь за него.

Твои правила:
1. Представься как ассистент Богдана
2. Объясни, что Богдан сейчас оффлайн
3. Отвечай кратко и по делу (1-2 предложения)
4. Предложи связаться позже или оставить сообщение
5. Будь вежливым и профессиональным

Не говори что ты ИИ или бот - ты ассистент."""
    
    payload = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "temperature": 0.6,
            "maxTokens": 120
        },
        "messages": [
            {
                "role": "system",
                "text": system_prompt
            },
            {
                "role": "user",
                "text": f"Сообщение для Богдана от {sender_name}: {text}"
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['result']['alternatives'][0]['message']['text']
            print(f"[AI] Ответ: {answer[:50]}...")
            return answer
        else:
            return "Привет! Богдан сейчас не в сети. Я его ассистент, передам ему ваше сообщение когда он появится. 📱"
    except Exception as e:
        return "Богдан временно недоступен. Сообщение сохранено, он ответит вам позже. ✨"

def check_if_user_is_online():
    """
    Проверяет, онлайн ли ты (Богдан) в WhatsApp.
    Логика: если был активен в последние 2 минуты - считаем онлайн.
    """
    global last_online_time
    
    # В реальной системе здесь должен быть вызов API WhatsApp
    # Но так как его нет, используем упрощенную логику:
    
    # 1. Проверяем, не было ли активности в последнее время
    if last_online_time:
        time_diff = datetime.now() - last_online_time
        if time_diff < timedelta(minutes=2):
            print(f"🟢 Богдан был онлайн {time_diff.seconds//60} мин назад")
            return True
    
    # 2. Можно добавить проверку через Green API получения статуса
    # Но для простоты считаем, что если бот запущен - ты оффлайн
    
    print("🔴 Богдан оффлайн (бот отвечает)")
    return False

def should_reply_to_message(sender, chat_id, message_text):
    """Определяет, должен ли бот отвечать на это сообщение."""
    
    # 1. Игнорируем группы
    if "@g.us" in chat_id:
        print(f"👥 Игнорируем групповой чат: {chat_id}")
        return False
    
    # 2. Игнорируем сообщения от самого себя
    if sender == MY_CHAT_ID:
        print(f"🔄 Игнорируем собственное сообщение")
        return False
    
    # 3. Игнорируем пустые/очень короткие сообщения
    if not message_text or len(message_text.strip()) < 2:
        print(f"📝 Игнорируем пустое сообщение")
        return False
    
    # 4. Проверяем, онлайн ли Богдан
    if check_if_user_is_online():
        print(f"⏸️ Богдан онлайн - бот не отвечает")
        return False
    
    # 5. Все проверки пройдены - отвечаем
    return True

def update_online_status():
    """
    Обновляет статус "онлайн" когда ты пишешь сообщения.
    Вызывается когда обнаруживаем исходящие сообщения от тебя.
    """
    global last_online_time
    last_online_time = datetime.now()
    print(f"⏰ Обновлен статус онлайн: {last_online_time.strftime('%H:%M:%S')}")

def whatsapp_bot():
    """Основной цикл WhatsApp бота."""
    print("📱 WhatsApp ассистент запущен...")
    
    message_counter = 0
    
    while True:
        try:
            # Получаем новые сообщения
            receive_url = f"https://api.green-api.com/waInstance{GREEN_ID}/receiveNotification/{GREEN_TOKEN}"
            response = requests.get(receive_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data:  # Есть новые сообщения
                    receipt_id = data['receiptId']
                    body = data.get('body', {})
                    webhook_type = body.get('typeWebhook', '')
                    
                    # 🔄 ОБНОВЛЯЕМ СТАТУС ОНЛАЙН если это ИСХОДЯЩЕЕ сообщение (ты пишешь)
                    if webhook_type == 'outgoingMessageReceived':
                        sender_data = body.get('senderData', {})
                        if sender_data.get('sender') == MY_CHAT_ID:
                            update_online_status()
                    
                    # 📨 ОБРАБАТЫВАЕМ ВХОДЯЩИЕ сообщения
                    elif webhook_type == 'incomingMessageReceived':
                        sender_data = body.get('senderData', {})
                        sender = sender_data.get('sender', '')
                        chat_id = sender_data.get('chatId', '')
                        sender_name = sender_data.get('senderName', 'Клиент')
                        
                        message_data = body.get('messageData', {})
                        if 'textMessageData' in message_data:
                            message_text = message_data['textMessageData']['textMessage']
                            
                            message_counter += 1
                            print(f"\n📨 [{message_counter}] От {sender_name}: {message_text}")
                            
                            # Проверяем, нужно ли отвечать
                            if should_reply_to_message(sender, chat_id, message_text):
                                # Получаем ответ от ассистента
                                ai_response = get_yandex_gpt_answer(message_text, sender_name)
                                
                                # Добавляем временную метку
                                final_response = f"{ai_response}\n\n🕒 {datetime.now().strftime('%H:%M')} | Ассистент Богдана"
                                
                                # Отправляем ответ
                                send_url = f"https://api.green-api.com/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
                                send_data = {
                                    "chatId": sender,
                                    "message": final_response
                                }
                                
                                send_response = requests.post(send_url, json=send_data, timeout=10)
                                if send_response.status_code == 200:
                                    print(f"✅ Ответ отправлен {sender_name}")
                                else:
                                    print(f"❌ Ошибка отправки")
                            else:
                                print(f"⏸️ Пропускаем (Богдан онлайн или группа)")
                    
                    # Удаляем уведомление
                    delete_url = f"https://api.green-api.com/waInstance{GREEN_ID}/deleteNotification/{GREEN_TOKEN}/{receipt_id}"
                    requests.delete(delete_url, timeout=5)
                    
            elif response.status_code in [400, 401]:
                print(f"⚠️ Ошибка API: {response.status_code}")
                time.sleep(10)
            else:
                # Нет сообщений
                time.sleep(1)
                
        except requests.exceptions.Timeout:
            print("⏰ Таймаут запроса")
            time.sleep(5)
        except Exception as e:
            print(f"🔥 Ошибка: {e}")
            time.sleep(10)

def keep_alive():
    """Keep-Alive для Render + периодическая проверка статуса."""
    print("🔄 Keep-Alive сервис запущен")
    
    while True:
        try:
            # Пингуем сами себя
            requests.get("https://whatsapp-ai-bot-h176.onrender.com/ping", timeout=10)
            current_time = time.strftime('%H:%M:%S')
            print(f"🔄 Ping в {current_time}: OK")
            
            # Периодически сбрасываем статус онлайн (если долго не было активности)
            global last_online_time
            if last_online_time:
                time_diff = datetime.now() - last_online_time
                if time_diff > timedelta(minutes=10):
                    print(f"🔄 Сброс статуса (неактивен {time_diff.seconds//60} мин)")
                    last_online_time = None
        
        except Exception as e:
            print(f"⚠️ Ping не удался: {e}")
        
        # Ждем 5 минут
        time.sleep(300)

def main():
    """Основная функция запуска."""
    print("=" * 60)
    print("🚀 ЗАПУСК СИСТЕМЫ АССИСТЕНТА...")
    print("=" * 60)
    
    # Запускаем Keep-Alive
    threading.Thread(target=keep_alive, daemon=True).start()
    
    # Запускаем WhatsApp бота
    threading.Thread(target=whatsapp_bot, daemon=True).start()
    
    # Запускаем Flask
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Веб-сервер на порту {port}")
    print(f"📡 Режим: Бот отвечает когда ты оффлайн")
    print(f"🔗 Статус: https://whatsapp-ai-bot-h176.onrender.com/status")
    print("=" * 60)
    print("✅ СИСТЕМА АКТИВИРОВАНА")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()

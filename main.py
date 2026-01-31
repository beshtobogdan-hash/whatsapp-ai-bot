import requests
import time
import os 
import threading
from flask import Flask
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Создаем Flask приложение
app = Flask(__name__)

# Маршруты для Render
@app.route('/')
def home():
    return "Бот Богдана активен", 200

@app.route('/ping')
def ping():
    return "Pong! Bot is alive", 200

# --- ТВОИ ДАННЫЕ ИЗ .env ---
GREEN_ID = os.getenv("GREEN_ID")
GREEN_TOKEN = os.getenv("GREEN_TOKEN")
FOLDER_ID = os.getenv("FOLDER_ID")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

# Проверяем, что все переменные загружены
if not all([GREEN_ID, GREEN_TOKEN, FOLDER_ID, YANDEX_API_KEY]):
    print("❌ ОШИБКА: Не все переменные окружения загружены!")
    print("Проверь .env файл или настройки Render")
    exit(1)

print("=" * 40)
print("🤖 БОТ БОГДАНА ИНИЦИАЛИЗИРОВАН")
print(f"📱 GREEN_ID: {GREEN_ID}")
print(f"🔑 Токен: {GREEN_TOKEN[:10]}...")
print(f"📁 FOLDER_ID: {FOLDER_ID}")
print("=" * 40)

def get_yandex_gpt_answer(text):
    """Запрос к YandexGPT."""
    print(f"[AI] Запрос: {text[:50]}...")
    
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "temperature": 0.3,
            "maxTokens": 1000
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты Богдан. Отвечай кратко, по-мужски и вежливо."
            },
            {
                "role": "user",
                "text": text
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
            print(f"[AI] Ошибка {response.status_code}: {response.text}")
            return "Я сейчас занят, отвечу позже!"
    except Exception as e:
        print(f"[AI] Ошибка подключения: {e}")
        return "На связи! Скоро буду."

def whatsapp_bot():
    """Основной цикл WhatsApp бота."""
    print("📱 WhatsApp бот запущен...")
    
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
                    
                    # Проверяем тип сообщения
                    if body.get('typeWebhook') == 'incomingMessageReceived':
                        sender_data = body.get('senderData', {})
                        sender = sender_data.get('sender', '')
                        chat_id = sender_data.get('chatId', '')
                        
                        # Проверяем текстовое сообщение
                        message_data = body.get('messageData', {})
                        if 'textMessageData' in message_data:
                            message_text = message_data['textMessageData']['textMessage']
                            
                            print(f"📨 Сообщение от {sender}: {message_text}")
                            
                            # Отвечаем только в личные чаты
                            if "@c.us" in sender:
                                # Получаем ответ от ИИ
                                ai_response = get_yandex_gpt_answer(message_text)
                                
                                # Отправляем ответ
                                send_url = f"https://api.green-api.com/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
                                send_data = {
                                    "chatId": sender,
                                    "message": ai_response
                                }
                                
                                send_response = requests.post(send_url, json=send_data, timeout=10)
                                if send_response.status_code == 200:
                                    print(f"✅ Ответ отправлен {sender}")
                                else:
                                    print(f"❌ Ошибка отправки: {send_response.status_code}")
                    
                    # Удаляем обработанное уведомление
                    delete_url = f"https://api.green-api.com/waInstance{GREEN_ID}/deleteNotification/{GREEN_TOKEN}/{receipt_id}"
                    requests.delete(delete_url, timeout=5)
                    
            elif response.status_code in [400, 401]:
                print(f"⚠️  Ошибка API: {response.status_code}")
                time.sleep(10)
            else:
                time.sleep(2)
                
        except requests.exceptions.Timeout:
            print("⏰ Таймаут запроса")
            time.sleep(5)
        except Exception as e:
            print(f"🔥 Ошибка в боте: {e}")
            time.sleep(10)

def keep_alive():
    """Keep-Alive для предотвращения сна Render."""
    print("🔄 Keep-Alive сервис запущен")
    
    while True:
        try:
            # Пингуем сами себя
            requests.get("https://whatsapp-ai-bot-h176.onrender.com/ping", timeout=10)
            print(f"🔄 Self-ping в {time.strftime('%H:%M:%S')}: OK")
        except Exception as e:
            print(f"⚠️  Self-ping не удался: {e}")
        
        # Ждем 8 минут (480 секунд)
        time.sleep(480)

def main():
    """Основная функция запуска."""
    print("=" * 40)
    print("🚀 ЗАПУСК СИСТЕМЫ...")
    print("=" * 40)
    
    # Запускаем Keep-Alive в отдельном потоке
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    
    # Запускаем WhatsApp бота в отдельном потоке
    bot_thread = threading.Thread(target=whatsapp_bot, daemon=True)
    bot_thread.start()
    
    # Получаем порт из переменных окружения
    port = int(os.environ.get("PORT", 10000))
    
    print(f"🌐 Веб-сервер запускается на порту {port}")
    print(f"📡 Keep-Alive активен (пинг каждые 8 минут)")
    print(f"🔗 Основная страница: https://whatsapp-ai-bot-h176.onrender.com")
    print(f"🔗 Ping: https://whatsapp-ai-bot-h176.onrender.com/ping")
    print("=" * 40)
    print("✅ ВСЕ СИСТЕМЫ ЗАПУЩЕНЫ")
    print("=" * 40)
    
    # Запускаем Flask сервер (блокирующая операция)
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Точка входа
if __name__ == "__main__":
    main()

import requests
import time
import os 
import threading
import atexit
import sys
from flask import Flask
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Бот Богдана активен", 200

@app.route('/ping')
def ping():
    return "Pong! Bot is alive", 200

# --- ТВОИ ДАННЫЕ ИЗ .env ---
GREEN_ID = os.getenv("GREEN_ID")
GREEN_TOKEN = os.getenv("GREEN_TOKEN")
FOLDER_ID = os.getenv("FOLDER_ID")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

print(f"=== НАСТРОЙКИ БОТА ===")
print(f"GREEN_ID: {GREEN_ID}")
print(f"FOLDER_ID: {FOLDER_ID}")
print(f"YANDEX_API_KEY: {YANDEX_API_KEY[:10]}...")
print(f"======================")

def get_yandex_gpt_answer(text):
    """Запрос к YandexGPT."""
    print(f"[YandexGPT] Запрос: {text[:50]}...")
    
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
        print(f"[YandexGPT] Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            answer = result['result']['alternatives'][0]['message']['text']
            print(f"[YandexGPT] Ответ: {answer[:50]}...")
            return answer
        else:
            print(f"[YandexGPT] Ошибка: {response.text}")
            return "Я сейчас занят, отвечу позже!"
    except Exception as e:
        print(f"[YandexGPT] Исключение: {e}")
        return "На связи! Скоро буду."

def run_bot():
    """Основной цикл WhatsApp бота."""
    print(">>> БОТ БОГДАНА ЗАПУЩЕН...")
    
    while True:
        try:
            # URL для получения уведомлений
            receive_url = f"https://api.green-api.com/waInstance{GREEN_ID}/receiveNotification/{GREEN_TOKEN}"
            
            # Получаем уведомления
            resp = requests.get(receive_url, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                
                if data is not None:  # Есть новые уведомления
                    receipt_id = data['receiptId']
                    body = data.get('body', {})
                    webhook_type = body.get('typeWebhook', '')
                    
                    print(f"[GreenAPI] Тип вебхука: {webhook_type}")
                    
                    # Обрабатываем ТОЛЬКО входящие сообщения к боту
                    if webhook_type == 'incomingMessageReceived':
                        sender_data = body.get('senderData', {})
                        message_data = body.get('messageData', {})
                        
                        # Извлекаем данные
                        chat_id = sender_data.get('chatId', '')
                        sender = sender_data.get('sender', '')
                        
                        # Проверяем, что это текстовое сообщение
                        if 'textMessageData' in message_data:
                            msg_text = message_data['textMessageData']['textMessage']
                            
                            print(f"💬 ВХОДЯЩЕЕ от {sender}: {msg_text}")
                            
                            # Проверяем, что это не группа
                            if "@g.us" not in chat_id:
                                # Получаем ответ от ИИ
                                ai_text = get_yandex_gpt_answer(msg_text)
                                
                                # Отправляем ответ
                                send_url = f"https://api.green-api.com/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
                                send_data = {
                                    "chatId": sender,
                                    "message": ai_text
                                }
                                
                                send_resp = requests.post(send_url, json=send_data)
                                if send_resp.status_code == 200:
                                    print(f"✅ Ответ отправлен {sender}")
                                else:
                                    print(f"❌ Ошибка отправки: {send_resp.status_code}")
                    
                    # ВСЕГДА удаляем уведомление после обработки
                    delete_url = f"https://api.green-api.com/waInstance{GREEN_ID}/deleteNotification/{GREEN_TOKEN}/{receipt_id}"
                    requests.delete(delete_url)
                    print(f"[GreenAPI] Уведомление {receipt_id} удалено")
                    
                else:
                    # Нет новых сообщений
                    print("[GreenAPI] Нет новых сообщений")
            
            elif resp.status_code == 400:
                print("[GreenAPI] Ошибка 400: Неверный запрос. Проверь токен.")
                time.sleep(10)
            elif resp.status_code == 401:
                print("[GreenAPI] Ошибка 401: Не авторизован. Проверь ID и токен.")
                time.sleep(10)
            else:
                print(f"[GreenAPI] Неожиданный статус: {resp.status_code}")
                time.sleep(10)
            
            # Пауза между проверками
            time.sleep(2)
            
        except requests.exceptions.Timeout:
            print("[GreenAPI] Таймаут запроса")
            time.sleep(10)
        except Exception as e:
            print(f"[GreenAPI] Критическая ошибка: {e}")
            time.sleep(10)

def keep_render_awake():
    """Фоновая задача для self-ping каждые 8 минут."""
    import datetime
    
    print("🔄 Keep-Alive сервис запущен")
    
    while True:
        try:
            # Пингуем сами себя
            response = requests.get("https://whatsapp-ai-bot-h176.onrender.com/ping", timeout=10)
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"🔄 Self-ping в {current_time}: Статус {response.status_code}")
        except Exception as e:
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"⚠️  Self-ping не удался в {current_time}: {e}")
        
        # Ждем 8 минут (480 секунд) - меньше 15 минут сна Render
        time.sleep(480)

def on_exit():
    """Функция при завершении работы."""
    print("⚠️  Бот завершает работу...")

# Регистрируем функцию завершения
atexit.register(on_exit)

if __name__ == "__main__":
    # Проверка переменных окружения
    if not all([GREEN_ID, GREEN_TOKEN, FOLDER_ID, YANDEX_API_KEY]):
        print("❌ ОШИБКА: Не все переменные окружения загружены!")
        print("Проверь .env файл или настройки Render")
        exit(1)
    
    # Запуск Keep-Alive в отдельном потоке
    print("🔄 Запуск Keep-Alive сервиса...")
    keep_alive_thread = threading.Thread(target=keep_render_awake, daemon=True)
    keep_alive_thread.start()
    
    # Запуск WhatsApp бота в отдельном потоке
    print("🤖 Запуск WhatsApp бота...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запуск Flask сервера для Render
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Веб-сервер запускается на порту {port}")
    print(f"📡 Keep-Alive активен (пинг каждые 8 минут)")
    print(f"🔗 Основной URL: https://whatsapp-ai-bot-h176.onrender.com")
    print(f"🔗 Ping URL: https://whatsapp-ai-bot-h176.onrender.com/ping")
    print("========================================")
    print("✅ ВСЕ СИСТЕМЫ ЗАПУЩЕНЫ")
    print("========================================")
    
    try:
        # Бесконечный цикл для предотвращения завершения
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен вручную")
        sys.exit(0)

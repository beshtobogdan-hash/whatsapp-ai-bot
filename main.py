import requests
import time
import os 
import threading
from flask import Flask
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# --- СЕРВЕР ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Бот Богдана активен", 200

# --- ТВОИ ДАННЫЕ ИЗ .env ---
GREEN_ID = os.getenv("GREEN_ID")
GREEN_TOKEN = os.getenv("GREEN_TOKEN")
FOLDER_ID = os.getenv("FOLDER_ID")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

def get_yandex_gpt_answer(text):
    """Запрос к YandexGPT."""
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
            return result['result']['alternatives'][0]['message']['text']
        else:
            print(f"Ошибка YandexGPT: {response.status_code}")
            return "Я сейчас занят, отвечу позже!"
    except Exception as e:
        print(f"Ошибка подключения к YandexGPT: {e}")
        return "На связи! Скоро буду."

def run_bot():
    """Цикл WhatsApp."""
    print(">>> БОТ БОГДАНА ЗАПУЩЕН...")
    
    while True:
        try:
            # ПРАВИЛЬНЫЙ URL для получения сообщений
            receive_url = f"https://api.green-api.com/waInstance{GREEN_ID}/receiveNotification/{GREEN_TOKEN}"
            
            resp = requests.get(receive_url, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                
                if data is not None:  # Проверяем, что есть сообщения
                    receipt_id = data['receiptId']
                    body = data.get('body', {})
                    
                    if body.get('typeWebhook') == 'incomingMessageReceived':
                        chat_id = body['senderData']['chatId']
                        
                        # Проверяем наличие текстового сообщения
                        message_data = body.get('messageData', {})
                        if 'textMessageData' in message_data:
                            msg_text = message_data['textMessageData']['textMessage']
                            
                            if "@c.us" in chat_id:  # Только личные сообщения
                                print(f"Вопрос от {chat_id}: {msg_text}")
                                
                                # Получаем ответ от ИИ
                                ai_text = get_yandex_gpt_answer(msg_text)
                                print(f"Ответ ИИ: {ai_text}")
                                
                                # Отправляем ответ
                                send_url = f"https://api.green-api.com/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
                                send_data = {
                                    "chatId": chat_id,
                                    "message": ai_text
                                }
                                
                                send_resp = requests.post(send_url, json=send_data)
                                if send_resp.status_code == 200:
                                    print("Сообщение отправлено успешно")
                                else:
                                    print(f"Ошибка отправки: {send_resp.status_code}")
                        
                        # Удаляем уведомление после обработки
                        delete_url = f"https://api.green-api.com/waInstance{GREEN_ID}/deleteNotification/{GREEN_TOKEN}/{receipt_id}"
                        requests.delete(delete_url)
                
                time.sleep(2)  # Небольшая пауза между проверками
            
            else:
                print(f"Ошибка получения сообщений: {resp.status_code}")
                time.sleep(10)
                
        except requests.exceptions.Timeout:
            print("Таймаут запроса к Green API")
            time.sleep(10)
        except Exception as e:
            print(f"Общая ошибка в run_bot: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # Проверяем, что все переменные загружены
    if not all([GREEN_ID, GREEN_TOKEN, FOLDER_ID, YANDEX_API_KEY]):
        print("ОШИБКА: Не все переменные окружения загружены!")
        print("Проверь .env файл или настройки Render")
    
    # Запуск бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запуск Flask сервера для Render
    port = int(os.environ.get("PORT", 10000))
    print(f"Запуск веб-сервера на порту {port}")
    app.run(host='0.0.0.0', port=port)

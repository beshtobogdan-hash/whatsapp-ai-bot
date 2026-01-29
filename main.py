import requests
import time
import os 
import threading
from flask import Flask
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Бот Богдана активен", 200

# --- ТВОИ ДАННЫЕ ИЗ .env ---
GREEN_ID = os.getenv("GREEN_ID")
GREEN_TOKEN = os.getenv("GREEN_TOKEN")
FOLDER_ID = os.getenv("FOLDER_ID")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

print(f"=== НАСТРОЙКИ ===")
print(f"GREEN_ID: {GREEN_ID}")
print(f"GREEN_TOKEN: {GREEN_TOKEN[:10]}...")  # Показываем только начало токена
print(f"FOLDER_ID: {FOLDER_ID}")
print(f"YANDEX_API_KEY: {YANDEX_API_KEY[:10]}...")
print(f"=================")

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
    """Цикл WhatsApp."""
    print(">>> БОТ БОГДАНА ЗАПУЩЕН...")
    
    while True:
        try:
            # ПРАВИЛЬНЫЙ URL для получения сообщений
            receive_url = f"https://api.green-api.com/waInstance{GREEN_ID}/receiveNotification/{GREEN_TOKEN}"
            print(f"[GreenAPI] Проверяем сообщения: {receive_url}")
            
            resp = requests.get(receive_url, timeout=30)
            print(f"[GreenAPI] Статус запроса: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"[GreenAPI] Получены данные: {data}")
                
                if data is not None:  # Проверяем, что есть сообщения
                    receipt_id = data['receiptId']
                    body = data.get('body', {})
                    print(f"[GreenAPI] Тип вебхука: {body.get('typeWebhook')}")
                    
                    if body.get('typeWebhook') == 'incomingMessageReceived':
                        chat_id = body['senderData']['chatId']
                        print(f"[GreenAPI] Сообщение от: {chat_id}")
                        
                        # Проверяем наличие текстового сообщения
                        message_data = body.get('messageData', {})
                        if 'textMessageData' in message_data:
                            msg_text = message_data['textMessageData']['textMessage']
                            print(f"[GreenAPI] Текст: {msg_text}")
                            
                            if "@c.us" in chat_id:  # Только личные сообщения
                                print(f"💬 ВОПРОС от {chat_id}: {msg_text}")
                                
                                # Получаем ответ от ИИ
                                ai_text = get_yandex_gpt_answer(msg_text)
                                
                                # Отправляем ответ
                                send_url = f"https://api.green-api.com/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
                                send_data = {
                                    "chatId": chat_id,
                                    "message": ai_text
                                }
                                
                                print(f"[GreenAPI] Отправка: {send_url}")
                                send_resp = requests.post(send_url, json=send_data)
                                print(f"[GreenAPI] Статус отправки: {send_resp.status_code}")
                                
                                if send_resp.status_code == 200:
                                    print("✅ Сообщение отправлено успешно")
                                else:
                                    print(f"❌ Ошибка отправки: {send_resp.text}")
                        
                        # Удаляем уведомление после обработки
                        delete_url = f"https://api.green-api.com/waInstance{GREEN_ID}/deleteNotification/{GREEN_TOKEN}/{receipt_id}"
                        print(f"[GreenAPI] Удаление уведомления: {delete_url}")
                        requests.delete(delete_url)
                else:
                    print("[GreenAPI] Нет новых сообщений")
                
                time.sleep(2)  # Небольшая пауза между проверками
            
            elif resp.status_code == 404:
                print("❌ ОШИБКА 404: Проверь GREEN_ID и GREEN_TOKEN!")
                time.sleep(10)
            else:
                print(f"⚠️ Ошибка получения сообщений: {resp.status_code}")
                time.sleep(10)
                
        except requests.exceptions.Timeout:
            print("⏰ Таймаут запроса к Green API")
            time.sleep(10)
        except Exception as e:
            print(f"🔥 Общая ошибка в run_bot: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # Проверяем, что все переменные загружены
    if not all([GREEN_ID, GREEN_TOKEN, FOLDER_ID, YANDEX_API_KEY]):
        print("❌ ОШИБКА: Не все переменные окружения загружены!")
        print("Проверь .env файл или настройки Render")
    else:
        print("✅ Все переменные окружения загружены")
    
    # Запуск бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запуск Flask сервера для Render
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Запуск веб-сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

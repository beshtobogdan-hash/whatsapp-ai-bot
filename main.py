import requests
import time
import json 
import os 
import threading
from flask import Flask # Нужно добавить в requirements.txt

# --- ИНИЦИАЛИЗАЦИЯ FLASK (чтобы Render не ругался) ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running", 200

# --- ОСНОВНАЯ ЛОГИКА БОТА ---

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

FOLDER_ID = os.environ.get("FOLDER_ID")
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY") 
GREEN_ID = os.environ.get("GREEN_ID")
GREEN_TOKEN = os.environ.get("GREEN_TOKEN")

def get_yandex_gpt_answer(text):
    """Запрос к YandexGPT с ролью Богдана."""
    url = "https://llm.api.cloud.yandex.net"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "temperature": 0.3, # Меньше температура — более четкие ответы
            "maxTokens": 1000
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты — Богдан. Ты отвечаешь в WhatsApp. Пиши коротко, по делу и вежливо. Если спрашивают что-то, в чем ты не уверен, скажи: 'Я сейчас занят, отвечу лично позже'. Не веди себя как робот, отвечай как человек."
            },
            {
                "role": "user",
                "text": text
            }
        ]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            result = res.json().get('result', {})
            alternatives = result.get('alternatives', [])
            if alternatives:
                return alternatives[0]['message']['text']
        return "Я сейчас немного занят, напишу чуть позже!"
    except Exception as e:
        print(f"Ошибка GPT: {e}")
        return "На связи! Скоро отвечу."

def run_bot():
    """Цикл проверки сообщений."""
    print("Бот Богдана запущен...")
    while True:
        receive_url = f"https://api.green-api.com{GREEN_ID}/receiveNotification/{GREEN_TOKEN}"
        try:
            resp = requests.get(receive_url, timeout=20)
            if resp.status_code == 200 and resp.json():
                data = resp.json()
                receipt_id = data['receiptId']
                body = data['body']
                
                if body.get('typeWebhook') == 'incomingMessageReceived':
                    chat_id = body['senderData']['chatId']
                    
                    # Проверка: не отвечаем самим себе и в группы (на бесплатном тарифе)
                    if 'messageData' in body and 'textMessageData' in body['messageData']:
                        msg_text = body['messageData']['textMessageData']['textMessage']
                        
                        # Если это личное сообщение (не группа)
                        if "@c.us" in chat_id:
                            print(f"Новое сообщение от {chat_id}: {msg_text}")
                            ai_text = get_yandex_gpt_answer(msg_text)
                            
                            send_url = f"https://api.green-api.com{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
                            requests.post(send_url, json={"chatId": chat_id, "message": ai_text})
                
                # Удаляем уведомление, чтобы не обрабатывать его дважды
                delete_url = f"https://api.green-api.com{GREEN_ID}/deleteNotification/{GREEN_TOKEN}/{receipt_id}"
                requests.delete(delete_url)
            
            time.sleep(1)
        except Exception as e:
            print(f"Ошибка цикла: {e}")
            time.sleep(5)

# --- ЗАПУСК ---

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Запускаем веб-сервер для Render (порт берется из системы)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

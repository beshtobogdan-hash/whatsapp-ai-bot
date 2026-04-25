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

@app.route('/')
def home():
    return "Бот-ассистент Богдана активен | Режим: один ответ на сессию", 200

@app.route('/ping')
def ping():
    return "Pong! Bot is alive", 200

@app.route('/status')
def status():
    return f"""
    <h3>🤖 Бот-ассистент Богдана</h3>
    <p>Статус: <span style='color:green'>✅ Активен</span></p>
    <p>Режим: Один ответ на пользователя, пока Богдан не появится онлайн</p>
    <p>Номер: +79994929247</p>
    <p>Время сервера: {datetime.now().strftime('%H:%M:%S')}</p>
    """, 200

# --- Данные из .env ---
GREEN_ID = os.getenv("GREEN_ID")
GREEN_TOKEN = os.getenv("GREEN_TOKEN")
FOLDER_ID = os.getenv("FOLDER_ID")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

MY_PHONE_NUMBER = "79994929247"
MY_CHAT_ID = f"{MY_PHONE_NUMBER}@c.us"

# Проверка переменных
if not all([GREEN_ID, GREEN_TOKEN, FOLDER_ID, YANDEX_API_KEY]):
    print("❌ ОШИБКА: Не все переменные окружения загружены!")
    exit(1)

# Глобальные состояния
last_online_time = None          # время последнего обнаружения вашего онлайна
replied_users = {}                # { chatId: timestamp_ответа } кто уже получил ответ в текущей офлайн-сессии
processed_receipts = set()        # для защиты от дублей уведомлений

print("=" * 60)
print("🤖 БОТ-АССИСТЕНТ БОГДАНА (обновлённая версия)")
print(f"📱 Мой номер: +{MY_PHONE_NUMBER}")
print("⚡ Режим: отвечаю только один раз на пользователя, пока хозяин не вернётся онлайн")
print("=" * 60)

def get_yandex_gpt_answer(text, sender_name, current_datetime_str):
    """Запрос к YandexGPT с учётом текущей даты/времени."""
    print(f"[AI] Запрос от {sender_name}: {text[:50]}...")
    
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_prompt = f"""Ты ассистент Богдана. Сейчас {current_datetime_str}. Богдан в данный момент не в сети WhatsApp, и ты временно отвечаешь за него.

Правила:
1. Ответь один раз и чётко.
2. Скажи, что Богдан сейчас офлайн, но ты его ассистент.
3. Ответь по существу сообщения (если вопрос требует ответа) или просто вежливо сообщи, что передашь сообщение.
4. Не повторяй одну и ту же информацию в разных сообщениях одному пользователю — ты отвечаешь только один раз за его обращение.
5. Учитывай текущую дату и время, если это важно (например, если спрашивают "сегодня вечером").
6. Не пиши длинные тексты, достаточно 1-2 предложений.
Будь полезным и кратким."""
    
    user_prompt = f"Сообщение для Богдана от {sender_name}: {text}"
    
    payload = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "temperature": 0.5,
            "maxTokens": 200
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": user_prompt}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            answer = result['result']['alternatives'][0]['message']['text']
            print(f"[AI] Ответ: {answer[:80]}...")
            return answer
        else:
            return "Привет! Богдан сейчас не в сети. Я его ассистент, обязательно передам сообщение, когда он вернётся. 📱"
    except Exception as e:
        return "Богдан временно недоступен. Ваше сообщение сохранено, он ответит позже. ✨"

def update_online_status():
    """Обновить время последнего онлайна (вызвано при исходящем сообщении от вас)."""
    global last_online_time
    last_online_time = datetime.now()
    # Когда вы онлайн — очищаем список отвеченных пользователей, чтобы бот снова мог отвечать новым сообщениям после вашего ухода
    global replied_users
    replied_users.clear()
    print(f"🟢 ОНЛАЙН обновлён: {last_online_time.strftime('%H:%M:%S')}, список отвеченных сброшен")

def is_user_online():
    """Определяет, были ли вы онлайн в последний час."""
    global last_online_time
    if last_online_time is None:
        return False
    time_diff = datetime.now() - last_online_time
    # Если вы были активны в течение последнего часа — считаем, что онлайн (не нужно отвечать)
    return time_diff < timedelta(hours=1)

def should_reply_to_user(chat_id, message_text):
    """Проверка, нужно ли отвечать этому пользователю сейчас."""
    # Игнорируем группы
    if "@g.us" in chat_id:
        return False
    # Игнорируем себя
    if chat_id == MY_CHAT_ID:
        return False
    # Пустые сообщения
    if not message_text or len(message_text.strip()) < 2:
        return False
    
    # Если вы онлайн в течение часа — не отвечаем
    if is_user_online():
        print(f"⏸️ Богдан онлайн (активен менее часа назад) — бот не отвечает")
        return False
    
    # Если вы офлайн больше часа, проверяем, не отвечали ли уже этому пользователю в текущей офлайн-сессии
    if chat_id in replied_users:
        last_reply_time = replied_users[chat_id]
        print(f"⏸️ Пользователю {chat_id} уже отвечали в {last_reply_time.strftime('%H:%M')}, пропускаем")
        return False
    
    # Все проверки пройдены: офлайн, и пользователю ещё не отвечали
    return True

def mark_replied(chat_id):
    """Запоминаем, что этому пользователю уже ответили."""
    replied_users[chat_id] = datetime.now()
    # Очистка старых записей (чтобы словарь не рос бесконечно)
    now = datetime.now()
    to_delete = [c for c, t in replied_users.items() if now - t > timedelta(days=1)]
    for c in to_delete:
        del replied_users[c]

def send_whatsapp_message(chat_id, text):
    """Отправка сообщения через Green API."""
    send_url = f"https://api.green-api.com/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
    send_data = {
        "chatId": chat_id,
        "message": text
    }
    try:
        resp = requests.post(send_url, json=send_data, timeout=10)
        if resp.status_code == 200:
            print(f"✅ Сообщение отправлено {chat_id}")
            return True
        else:
            print(f"❌ Ошибка отправки {chat_id}: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Исключение при отправке: {e}")
        return False

def whatsapp_bot():
    """Основной цикл получения и обработки сообщений."""
    print("📱 WhatsApp ассистент запущен...")
    message_counter = 0
    
    while True:
        try:
            receive_url = f"https://api.green-api.com/waInstance{GREEN_ID}/receiveNotification/{GREEN_TOKEN}"
            response = requests.get(receive_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    receipt_id = data['receiptId']
                    
                    # Проверка дублей уведомлений
                    if receipt_id in processed_receipts:
                        print(f"⚠️ Дубль receiptId {receipt_id}, удаляем и пропускаем")
                        delete_url = f"https://api.green-api.com/waInstance{GREEN_ID}/deleteNotification/{GREEN_TOKEN}/{receipt_id}"
                        requests.delete(delete_url, timeout=5)
                        continue
                    processed_receipts.add(receipt_id)
                    # Ограничим размер множества
                    if len(processed_receipts) > 1000:
                        processed_receipts.clear()
                    
                    body = data.get('body', {})
                    webhook_type = body.get('typeWebhook', '')
                    
                    # Обработка исходящих сообщений (от вас) для обновления статуса онлайн
                    if webhook_type == 'outgoingMessageReceived':
                        sender_data = body.get('senderData', {})
                        sender = sender_data.get('sender', '')
                        if sender == MY_CHAT_ID:
                            update_online_status()
                    
                    # Обработка входящих сообщений
                    elif webhook_type == 'incomingMessageReceived':
                        sender_data = body.get('senderData', {})
                        sender_chat_id = sender_data.get('sender', '')
                        sender_name = sender_data.get('senderName', 'Клиент')
                        message_data = body.get('messageData', {})
                        
                        if 'textMessageData' in message_data:
                            message_text = message_data['textMessageData']['textMessage']
                            message_counter += 1
                            print(f"\n📨 [{message_counter}] От {sender_name} ({sender_chat_id}): {message_text[:60]}")
                            
                            # Решаем, нужно ли отвечать
                            if should_reply_to_user(sender_chat_id, message_text):
                                current_datetime = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
                                ai_response = get_yandex_gpt_answer(message_text, sender_name, current_datetime)
                                final_response = f"{ai_response}\n\n🕒 {datetime.now().strftime('%H:%M')} | Ассистент Богдана"
                                
                                if send_whatsapp_message(sender_chat_id, final_response):
                                    mark_replied(sender_chat_id)
                            else:
                                print(f"⏸️ Пропускаем (онлайн или уже отвечали)")
                    
                    # Удаляем уведомление, чтобы оно не приходило снова
                    delete_url = f"https://api.green-api.com/waInstance{GREEN_ID}/deleteNotification/{GREEN_TOKEN}/{receipt_id}"
                    requests.delete(delete_url, timeout=5)
                    
            elif response.status_code in [400, 401, 403]:
                print(f"⚠️ Ошибка API: {response.status_code}")
                time.sleep(30)
            else:
                time.sleep(1)
                
        except requests.exceptions.Timeout:
            print("⏰ Таймаут запроса, повтор через 5 сек")
            time.sleep(5)
        except Exception as e:
            print(f"🔥 Ошибка в цикле бота: {e}")
            time.sleep(10)

def keep_alive():
    """Keep-Alive сервис для Render."""
    while True:
        try:
            requests.get("https://whatsapp-ai-bot-h176.onrender.com/ping", timeout=10)
            print(f"🔄 Ping в {time.strftime('%H:%M:%S')}: OK")
        except:
            pass
        time.sleep(300)

def main():
    print("=" * 60)
    print("🚀 ЗАПУСК СИСТЕМЫ АССИСТЕНТА (исправленная версия)")
    print("=" * 60)
    
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=whatsapp_bot, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Веб-сервер на порту {port}")
    print("✅ СИСТЕМА АКТИВИРОВАНА")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()

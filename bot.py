import requests
import time
import json 
import os 
try:
    from dotenv import load_dotenv # Подключаем библиотеку для чтения .env файла локально
    load_dotenv() # Загружаем переменные из .env файла
except ImportError:
    print("Библиотека dotenv не установлена. Установите: pip install python-dotenv")
    exit()

# ТЕПЕРЬ ВСЕ ДАННЫЕ БЕРУТСЯ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
FOLDER_ID = os.environ.get("FOLDER_ID")
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY") 
GREEN_ID = os.environ.get("GREEN_ID")
GREEN_TOKEN = os.environ.get("GREEN_TOKEN")

def get_yandex_gpt_answer(text):
    """Отправляет запрос к YandexGPT и возвращает ответ."""
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"  # ИСПРАВЛЕННЫЙ URL!
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "temperature": 0.6,
            "maxTokens": 1000
        },
        "messages": [
            {
                "role": "user",
                "text": text
            }
        ]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload)
        
        if res.status_code == 200:
            response_data = res.json()
            print(f"Ответ YandexGPT: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            
            # Извлекаем текст ответа (ПРАВИЛЬНЫЙ ПУТЬ ДОСТУПА)
            if 'result' in response_data and 'alternatives' in response_data['result']:
                # alternatives - это список, берем первый элемент
                if len(response_data['result']['alternatives']) > 0:
                    return response_data['result']['alternatives'][0]['message']['text']
                else:
                    return "Пустой ответ от ИИ"
            else:
                print(f"Неожиданная структура ответа: {response_data}")
                return "Прости, ИИ ответил странно."
        else:
            print(f"Ошибка YandexGPT: {res.status_code}, {res.text}")
            return "Прости, я приболел. Скоро вернусь!"
            
    except Exception as e:
        print(f"Ошибка при запросе к YandexGPT: {e}")
        return "Прости, проблемы с подключением."


def run_bot():
    print("Бот запущен и слушает WhatsApp...")
    while True:
        receive_url = f"https://api.green-api.com/waInstance{GREEN_ID}/receiveNotification/{GREEN_TOKEN}"  # ИСПРАВЛЕННЫЙ URL
        try:
            resp = requests.get(receive_url)
            
            if resp.status_code == 200:
                data = resp.json()
                if data:  # Если есть данные
                    receipt_id = data['receiptId']
                    body = data['body']
                    
                    if body.get('typeWebhook') == 'incomingMessageReceived':
                        chat_id = body['senderData']['chatId']
                        
                        # Проверяем наличие текстового сообщения
                        if 'messageData' in body and 'textMessageData' in body['messageData']:
                            msg_text = body['messageData']['textMessageData']['textMessage']
                            
                            print(f"Пришло сообщение от {chat_id}: {msg_text}")
                            
                            # Получаем ответ от ИИ
                            ai_text = get_yandex_gpt_answer(msg_text)
                            
                            # Отправляем ответ
                            send_url = f"https://api.green-api.com/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}"  # ИСПРАВЛЕННЫЙ URL
                            send_data = {
                                "chatId": chat_id,
                                "message": ai_text
                            }
                            
                            send_resp = requests.post(send_url, json=send_data)
                            if send_resp.status_code == 200:
                                print(f"✅ Ответ отправлен в {chat_id}")
                            else:
                                print(f"❌ Ошибка отправки: {send_resp.text}")
                        
                    # Удаляем уведомление
                    delete_url = f"https://api.green-api.com/waInstance{GREEN_ID}/deleteNotification/{GREEN_TOKEN}/{receipt_id}"  # ИСПРАВЛЕННЫЙ URL
                    requests.delete(delete_url)
                    print(f"Уведомление {receipt_id} удалено")
            
            time.sleep(2)  # Пауза между проверками

        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети: {e}")
            time.sleep(5)
        except json.decoder.JSONDecodeError:
            print("Ошибка парсинга JSON")
        except Exception as e:
            print(f"Произошла непредвиденная ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # Тестовый запуск YandexGPT
    print("Тестируем подключение к YandexGPT...")
    test = get_yandex_gpt_answer("Привет! Ответь коротко: как дела?")
    print(f"Тестовый ответ: {test}")
    
    # Запускаем бота
    run_bot()
# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
#bot = telebot.TeleBot('6383118899:AAEO0xs0M8NU4vOaXeimR152ilwY1j59Ov8')
# https://signipa.ru/download/

import telebot
import requests
from bs4 import BeautifulSoup
import uuid
import json
import datetime
from telebot import types
from datetime import datetime


# Здесь будут храниться данные пользователей
user_data = {}

# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
bot = telebot.TeleBot('6383118899:AAEO0xs0M8NU4vOaXeimR152ilwY1j59Ov8')

# URL вашего Django API
django_api_url = 'https://signipa.ru/app-names'

# ID пользователей, которым разрешен доступ
ADMIN_USER_IDS = [1850974084, 5145425036]

class UserState:
    WAITING_FOR_NAME = 0
    WAITING_FOR_URL = 1

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    btn_UDID = types.InlineKeyboardButton("Получить ссылки", callback_data='get_data')
    markup.add(btn_UDID)

    if message.from_user.id in ADMIN_USER_IDS:
        register_button = types.InlineKeyboardButton("Новая ссылка", callback_data='new_data')
        markup.add(register_button)

    bot.reply_to(message, f"👋Привет  {message.from_user.first_name}. \nЭто бот для получения ссылок для установки приложений\nНажмите Получить ссылки для просмотра ссылок.", reply_markup=markup)

@bot.callback_query_handler(func=lambda callback: True)
def on_callback_query(callback):
    if callback.data == 'get_data':
        try:

            response = requests.get(f"{django_api_url}")
            app_data = response.json()  # Assuming the response is a JSON array of dictionaries
            
            if not app_data:
                bot.send_message(callback.message.chat.id, "На данный момент нет данных о приложениях.")
                return
            
            response_text = "Список приложений:\n"
            for idx, app_info in enumerate(app_data, start=1):
                app_name = app_info.get('app_name', 'Неизвестное приложение')
                app_token = app_info.get('app_token', '')
                app_data = app_info.get('app_data', '')
                app_link = f"Ссылка: https://signipa.ru/download/{app_token}"
                
                response_text += f"{idx} - ({app_name}) - {app_data}\n\n{app_link}\n\n"
            markup = types.InlineKeyboardMarkup()
            btn_UDID = types.InlineKeyboardButton("Получить ссылки", callback_data='get_data')
            markup.add(btn_UDID)

            if callback.message.from_user.id in ADMIN_USER_IDS:
                register_button = types.InlineKeyboardButton("Новая ссылка", callback_data='new_data')
                markup.add(register_button)

            bot.send_message(callback.message.chat.id, response_text, reply_markup=markup)
            if "Повторить🔄" ==callback.message.text:
                bot.register_callback_query_handler = 'get_data'
        except Exception as e:
            bot.send_message(callback.message.chat.id, f"Произошла ошибка: {str(e)}")

    elif callback.data == 'new_data':

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        cencelBtn = types.KeyboardButton("Отменить⛔")
        markup.add(cencelBtn)

        bot.send_message(callback.message.chat.id, "Привет босс введите название приложения для регистрации.📥", reply_markup=markup)
        bot.register_next_step_handler(callback.message, get_task_name)

# Обработчик ввода названия приложения
@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get('state') == UserState.WAITING_FOR_NAME)
def get_task_name(message):
    user_id = message.chat.id
    task_name = message.text
    token = str(uuid.uuid4())  # Генерируем уникальный токен
    
    user_data[user_id] = {'task_name': task_name, 'app_token': token}
    
    bot.send_message(user_id, f"Название приложения: {task_name}")
    bot.send_message(user_id, f"Токен: {generate_download_link(token)}\n\nСейчас введите ссылку для извлечения значения.")
    user_data[user_id]['state'] = UserState.WAITING_FOR_URL

# Функция для создания ссылки с токеном
def generate_download_link(token):
    return f"https://signipa.ru/download/{token}"

# Обработчик ввода ссылки и извлечения значения
@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get('state') == UserState.WAITING_FOR_URL)
def get_value_from_url(message):
    user_id = message.chat.id
    
    if user_id not in user_data:
        bot.send_message(user_id, "Для начала работы, пожалуйста, введите название приложения.")
        return
    
    url = message.text
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            input_tags = soup.find_all('input')
            try:
                if len(input_tags) >= 3:
                    value = input_tags[2].get('value')
                    task_name = user_data[user_id]['task_name']
                    token = user_data[user_id]['app_token']
                    
                    bot.send_message(user_id, f"Название приложения: {task_name}\n\nvalue: {value}\n\nТокен: {(token)}\n\nВремя создания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    bot.send_message(user_id, f"ССЫЛКА ДЛЯ СКАЧИВАНИЯ: \n\nhttps://signipa.ru/download/{(token)}")
                    
                    
                    # Отправляем данные на сервер Django через API
                    data = {
                        'app_name': task_name,
                        'app_value': value,
                        'app_token': token,
                        'app_data' : datetime.now().strftime('%m-%d %H:%M')
                    }

                    response = requests.post(url=django_api_url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
                    if response.status_code == 201:
                        markup = types.InlineKeyboardMarkup()
                        btn_UDID = types.InlineKeyboardButton("Получить ссылки", callback_data='get_data')
                        markup.add(btn_UDID)

                        if message.from_user.id in ADMIN_USER_IDS:
                            register_button = types.InlineKeyboardButton("Новая ссылка", callback_data='new_data')
                            markup.add(register_button)
                        bot.send_message(message.chat.id, "Данные успешно отправлены в Django.",reply_markup=markup)
                        if user_id in user_data:
                            del user_data[user_id]
                            return send_welcome
                    else:
                        bot.send_message(message.chat.id, "Не удалось отправить данные в Django.(Zayebal padajdi)")
                        if user_id in user_data:
                            del user_data[user_id]
                        return
                else:
                    bot.send_message(user_id, "На странице нет третьего тега <input>.")
            except Exception as e:
                bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")
                
        else:
            bot.send_message(user_id, "Не удалось получить HTML-код страницы.")
    
    except Exception as e:
        bot.send_message(user_id, f"Произошла ошибка: {str(e)}")

@bot.message_handler(commands=['get_data'])
def get_data_callback(message):
    user_id = message.from_user.id
    
    try:

            response = requests.get(f"{django_api_url}")
            app_data = response.json()  # Assuming the response is a JSON array of dictionaries
            
            if not app_data:
                bot.send_message(message.chat.id, "На данный момент нет данных о приложениях.")
                return
            
            response_text = "Список приложений:\n"
            for idx, app_info in enumerate(app_data, start=1):
                app_name = app_info.get('app_name', 'Неизвестное приложение')
                app_token = app_info.get('app_token', '')
                app_link = f"Ссылка: https://signipa.ru/download/{app_token}"
                
                response_text += f"{idx} - ({app_name})\n\n{app_link}\n\n"
            markup = types.InlineKeyboardMarkup()
            btn_UDID = types.InlineKeyboardButton("Получить ссылки", callback_data='get_data')
            markup.add(btn_UDID)

            if message.from_user.id in ADMIN_USER_IDS:
                register_button = types.InlineKeyboardButton("Новая ссылка", callback_data='new_data')
                markup.add(register_button)

            bot.send_message(message.chat.id, response_text, reply_markup=markup)
            if "Повторить🔄" == message.text:
                bot.register_callback_query_handler = 'get_data'
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    bot.polling()

# Запускаем бота
bot.polling()

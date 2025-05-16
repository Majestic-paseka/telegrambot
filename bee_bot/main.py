import os
from dotenv import load_dotenv
import telebot
from telebot import types
import sqlite3


load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = telebot.TeleBot(TOKEN)

# Инициализация БД
def init_db():
    conn = sqlite3.connect('bees.db')
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            surname TEXT,
            position TEXT,
            password TEXT
        )
    ''')
    # Таблица пчелиных семей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS families (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_number TEXT,
            birth_year INTEGER,
            breed TEXT,
            species TEXT
        )
    ''')
    conn.commit()
    conn.close()


init_db()

# Временное хран. данных пользователей при регистрации и добавлении семей
user_data = {}


@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    user_data.pop(user_id, None)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("Регистрация", "Помощь")
    keyboard.row("Начать заново", "Добавить пчелиную семью", "Удалить пчелиную семью")
    bot.send_message(user_id, "Приветствую! Чем могу тебе помочь?", reply_markup=keyboard)


@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "/start - Начать взаимодействие с ботом\n"
        "/add_family - Добавить новую пчелиную семью\n"
        "/delete_family - Удалить пчелиную семью\n"
        "/reg - Зарегистрироваться\n"
    )
    bot.send_message(message.chat.id, help_text)


# Обр текста "Помощь"
@bot.message_handler(func=lambda m: m.text == "Помощь")
def help_button(message):
    help_command(message)


# Обр текста "Регистрация"
@bot.message_handler(func=lambda m: m.text == "Регистрация")
def registration_command(message):
    user_id = message.chat.id
    user_data[user_id] = {}
    bot.send_message(user_id,
                     "Введите ваше Имя, Фамилию и Должность через пробел (например: Иванов Иван руководитель):")
    bot.register_next_step_handler(message, get_name_surname_position)


def get_name_surname_position(message):
    user_id = message.chat.id
    parts = message.text.strip().split()
    if len(parts) >= 3:
        name = parts[0]
        surname = parts[1]
        position = ' '.join(parts[2:])
        user_data[user_id]['name'] = name
        user_data[user_id]['surname'] = surname
        user_data[user_id]['position'] = position

        bot.send_message(user_id, "Введите пароль для регистрации:")
        bot.register_next_step_handler(message, get_password)
    else:
        bot.send_message(user_id, "Пожалуйста, введите Имя, Фамилию и Должность через пробел.")
        bot.register_next_step_handler(message, get_name_surname_position)


def get_password(message):
    user_id = message.chat.id
    password = message.text.strip()
    user_data[user_id]['password'] = password

    save_user_to_db(user_id)

    bot.send_message(user_id, "Регистрация завершена! Добро пожаловать.")


def save_user_to_db(user_id):
    data = user_data.get(user_id)
    if data:
        conn = sqlite3.connect('bees.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, name, surname, position, password)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, data['name'], data['surname'], data['position'], data['password']))
        conn.commit()
        conn.close()



@bot.message_handler(commands=['add_family'])
def add_family_command(message):
    bot.send_message(
        message.chat.id,
        "Пожалуйста, введите данные в следующем формате:\n"
        "номер семьи, год рождения, порода, вид\n"
        "например:\n12345, 2020, Карпатка, Медонос"
    )
    bot.register_next_step_handler(message, process_family_input)


def process_family_input(message):
    input_text = message.text.strip()
    # Разделяем по запятым
    parts = [part.strip() for part in input_text.split(',')]

    if len(parts) != 4:
        bot.send_message(
            message.chat.id,
            "Некорректный формат. Пожалуйста, попробуйте снова и следуйте примеру."
        )
        return

    family_number = parts[0]
    try:
        birth_year = int(parts[1])
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Год рождения должен быть числом. Попробуйте снова."
        )
        return
    breed = parts[2]
    species = parts[3]

    # Сохраняем в базу данных
    conn = sqlite3.connect('bees.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO families (family_number, birth_year, breed, species)
        VALUES (?, ?, ?, ?)
    ''', (family_number, birth_year, breed, species))

    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, f"Пчелиная семья '{family_number}' успешно добавлена.")


# Команда для удаления существующей пчелиной семьи
@bot.message_handler(commands=['delete_family'])
def delete_family_command(message):
    # Запрос номера семьи для удаления
    msg = bot.send_message(message.chat.id, "Введите номер семьи для удаления:")
    bot.register_next_step_handler(msg, delete_family_by_number)


def delete_family_by_number(m):
    family_number = m.text.strip()

    conn = sqlite3.connect('bees.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM families WHERE family_number=?", (family_number,))
    result = cursor.fetchone()

    if result:
        cursor.execute("DELETE FROM families WHERE family_number=?", (family_number,))
        conn.commit()
        bot.send_message(m.chat.id, f"Пчелиная семья '{family_number}' успешно удалена.")
    else:
        bot.send_message(m.chat.id, f"Семья с номером '{family_number}' не найдена.")

    conn.close()


# Обр сообщ с документами или аудио
@bot.message_handler(content_types=['document', 'audio'])
def handle_other_messages(m):
    bot.send_message(m.chat.id, "Я пчелка и не умею обрабатывать такие сообщения.")


# Запуск бота
bot.polling(none_stop=True)

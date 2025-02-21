import sqlite3
from logger import setup_logger

logger = setup_logger()

# Подключение к базе данных
def connect_db():
    try:
        connection = sqlite3.connect("identifier.sqlite")
        if connection is None:
            raise Exception("Не удалось подключиться к базе данных")
        return connection
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return None

# Создание необходимых таблиц
def create_tables():
    connection = connect_db()
    cursor = connection.cursor()

    # Таблица для хранения ID чатов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_type TEXT NOT NULL,
            chat_id INTEGER NOT NULL UNIQUE
        )
    """)

    # Таблица для хранения пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            username TEXT,
            full_name TEXT,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            chat_id INTEGER,
            FOREIGN KEY(chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    """)

    # Таблица для хранения сообщений
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message_text TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица для отслеживания активности пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            request_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()

# Загрузка конфигурации
def load_config():
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT chat_type, chat_id FROM chats")
    chats = {row[0]: row[1] for row in cursor.fetchall()}
    connection.close()
    return chats

# Сохранение ID чата
def save_chat(chat_type, chat_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO chats (chat_type, chat_id) VALUES (?, ?)
    """, (chat_type, chat_id))
    connection.commit()
    connection.close()

# Добавление пользователя в базу данных
def add_user(user_id, username, full_name, chat_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, full_name, chat_id)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, full_name, chat_id))
    connection.commit()
    connection.close()

# Добавление сообщения в базу данных
def add_message(user_id, message_text):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO messages (user_id, message_text)
        VALUES (?, ?)
    """, (user_id, message_text))
    cursor.execute("""
        DELETE FROM messages
        WHERE id NOT IN (
            SELECT id FROM messages
            ORDER BY sent_at DESC
            LIMIT 100
        )
    """)
    connection.commit()
    connection.close()

# Логирование активности пользователя
def log_user_activity(user_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO user_activity (user_id)
        VALUES (?)
    """, (user_id,))
    cursor.execute("""
        DELETE FROM user_activity
        WHERE id NOT IN (
            SELECT id
            FROM user_activity
            WHERE user_id = ?
            ORDER BY request_time DESC
            LIMIT 50
        )
    """, (user_id,))
    connection.commit()
    connection.close()

# Очистка неактивных пользователей
def cleanup_inactive_users():
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        DELETE FROM users 
        WHERE chat_id NOT IN (SELECT chat_id FROM chats)
    """)
    connection.commit()
    connection.close()

# Получение всех пользователей из чата
def get_users_in_chat(chat_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT username, full_name FROM users WHERE chat_id = ?", (chat_id,))
    users = cursor.fetchall()
    connection.close()
    return users

# Обновление данных о чатах
def update_chat_data(inviting_chat_id, invited_chat_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE users
        SET chat_id = ?
        WHERE chat_id = ?
    """, (inviting_chat_id, invited_chat_id))
    connection.commit()
    connection.close()

# Добавление существующих пользователей из чата в базу данных
async def add_existing_users_to_db(app, chat_id):
    connection = connect_db()

    try:
        members = []
        async for member in app.get_chat_members(chat_id):
            if member.user.is_bot or member.status == "kicked":
                continue  # Пропускаем ботов и заблокированных пользователей

            add_user(
                user_id=member.user.id,
                username=member.user.username,
                full_name=member.user.first_name + (f" {member.user.last_name}" if member.user.last_name else ""),
                chat_id=chat_id
            )
            members.append(member)

        connection.commit()
        logger.info(f"Добавлено {len(members)} пользователей из чата {chat_id}.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении существующих пользователей: {e}")
    finally:
        connection.close()

# Получение списка участников чата
async def get_chat_members(app, chat_id):
    members = []
    try:
        async for member in app.get_chat_members(chat_id):
            if member.user and member.status != "left":
                members.append(member)
    except Exception as e:
        logger.error(f"Ошибка при получении участников чата: {e}")
    return members
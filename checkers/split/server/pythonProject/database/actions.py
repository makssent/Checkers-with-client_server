import os
import sqlite3

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
database_path = os.path.join(base_dir, 'database')
database_file = os.path.join(database_path, 'users.db')

def initialize_database():
    if not os.path.exists(database_path):
        os.makedirs(database_path)

    conn = sqlite3.connect(database_file)
    c = conn.cursor()

    # Создаем таблицу, если она еще не создана
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            score INTEGER DEFAULT 500
        )
    ''')

    conn.commit()
    conn.close()

def delete_user_by_id(user_id):
    conn = sqlite3.connect(database_file)
    c = conn.cursor()

    # Удаляем пользователя по id
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))

    conn.commit()
    conn.close()

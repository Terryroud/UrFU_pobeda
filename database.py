import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional


class TelegramDatabase:
    def __init__(self, db_name: str = "telegram_bot.db"):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        """Инициализация базы данных с объединенной таблицей"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            # ЕДИНАЯ таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    custom_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица сообщений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message_text TEXT,
                    bot_response TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            conn.commit()

    def add_user(self, user_id: int, username: str = None,
                 first_name: str = None, last_name: str = None):
        """Добавление/обновление пользователя БЕЗ потери custom_name"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            # Сначала проверяем, есть ли пользователь и его custom_name
            cursor.execute('SELECT custom_name FROM users WHERE user_id = ?', (user_id,))
            existing_user = cursor.fetchone()
            current_custom_name = existing_user[0] if existing_user else None

            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, custom_name, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, first_name, last_name, current_custom_name))
            conn.commit()

    def update_user_name(self, user_id: int, name: str):
        """Обновление кастомного имени пользователя"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET custom_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (name, user_id))
            conn.commit()

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение полной информации о пользователе"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, first_name, last_name, custom_name, created_at
                FROM users 
                WHERE user_id = ?
            ''', (user_id,))

            result = cursor.fetchone()
            if result:
                return {
                    'user_id': result[0],
                    'username': result[1],
                    'first_name': result[2],
                    'last_name': result[3],
                    'custom_name': result[4],
                    'created_at': result[5]
                }
            return None

    def get_user_name(self, user_id: int) -> Optional[str]:
        """Получение имени пользователя (кастомное или из профиля)"""
        user = self.get_user(user_id)
        if user:
            # Возвращаем кастомное имя, либо first_name, либо username
            return user.get('custom_name') or user.get('first_name') or user.get('username')
        return None

    def add_message(self, user_id: int, message_text: str, bot_response: str):
        """Добавление сообщения в историю с автоматической очисткой старых"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO messages (user_id, message_text, bot_response)
                VALUES (?, ?, ?)
            ''', (user_id, message_text, bot_response))

            # Очищаем старые сообщения после добавления нового
            cursor.execute('''
                DELETE FROM messages 
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM messages 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 30
                )
            ''', (user_id, user_id))

            conn.commit()

    def get_recent_messages(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Получение последних сообщений пользователя"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message_text, bot_response, timestamp 
                FROM messages 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_id, limit))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'user_message': row[0],
                    'bot_response': row[1],
                    'timestamp': row[2]
                })

            return messages[::-1]  # возвращаем в хронологическом порядке

    def get_conversation_history(self, user_id: int, limit: int = 30) -> str:
        """Получение истории переписки в формате для RAG"""
        messages = self.get_recent_messages(user_id, limit)

        history = []
        for msg in messages:
            history.append(f"User: {msg['user_message']}")
            history.append(f"Bot: {msg['bot_response']}")

        return "\n".join(history)

    def get_user_stats(self, user_id: int) -> Dict:
        """Статистика пользователя"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            # Количество сообщений
            cursor.execute('SELECT COUNT(*) FROM messages WHERE user_id = ?', (user_id,))
            message_count = cursor.fetchone()[0]

            # Первое сообщение
            cursor.execute('SELECT MIN(timestamp) FROM messages WHERE user_id = ?', (user_id,))
            first_message = cursor.fetchone()[0]

            return {
                'message_count': message_count,
                'first_interaction': first_message
            }

    def cleanup_old_messages(self, days: int = 30):
        """Очистка старых сообщений"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM messages 
                WHERE timestamp < datetime('now', ?)
            ''', (f'-{days} days',))
            conn.commit()

    def cleanup_old_messages_per_user(self, user_id: int, keep_count: int = 30):
        """Оставляет только последние keep_count сообщений для пользователя"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            # Находим ID keep_count-го сообщения по времени
            cursor.execute('''
                SELECT id FROM messages 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1 OFFSET ?
            ''', (user_id, keep_count - 1))

            result = cursor.fetchone()
            if result:
                # Удаляем все сообщения старше этого ID
                cursor.execute('''
                    DELETE FROM messages 
                    WHERE user_id = ? AND id < ?
                ''', (user_id, result[0]))

            conn.commit()

    def delete_user_data(self, user_id: int):
        """Удаление всех данных пользователя (сообщений и имени)"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            # Удаляем сообщения пользователя
            cursor.execute('DELETE FROM messages WHERE user_id = ?', (user_id,))

            # Сбрасываем кастомное имя (остальные данные оставляем)
            cursor.execute('''
                UPDATE users 
                SET custom_name = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (user_id,))

            conn.commit()
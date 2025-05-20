import sqlite3
from typing import Optional
from datetime import datetime

DB_PATH = "users.db"


def initialize_db():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            vpn_username TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()
    print("База данных инициализирована.")


def save_user_link(telegram_id: int, vpn_username: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT OR REPLACE INTO accounts (telegram_id, vpn_username) 
            VALUES (?, ?)
            """,
            (telegram_id, vpn_username)
        )
        conn.commit()
        print(f"Связка {telegram_id} - {vpn_username} сохранена.")
    except Exception as e:
        print(f"Ошибка при сохранении связки в БД: {str(e)}")
    finally:
        conn.close()


def get_vpn_username(telegram_id: int) -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT vpn_username FROM accounts WHERE telegram_id = ?", (telegram_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"Ошибка при получении связки из БД: {str(e)}")
        return None
    finally:
        conn.close()


def remove_user_link(username: str):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM accounts WHERE vpn_username = ?", (username,))
        connection.commit()
        print(f"Связка {username} удалена из БД.")
    except Exception as e:
        print(f"Ошибка при удалении связки из БД: {str(e)}")
    finally:
        connection.close()


def get_all_user_links() -> list[tuple[int, str]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT telegram_id, vpn_username FROM accounts")
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        print(f"Ошибка при получении всех связок из БД: {str(e)}")
        return []
    finally:
        conn.close()


if __name__ == "__main__":
    initialize_db()

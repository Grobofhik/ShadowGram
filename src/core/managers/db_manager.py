import sqlite3
import json
from pathlib import Path
from src.core.logger import logger

def mirror_to_sqlite(config_file: Path, data: dict):
    """Синхронизирует данные из JSON в SQLite для аналитики и быстрых выборок."""
    db_path = config_file.with_suffix('.db')
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Инициализация схемы
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    workdir TEXT PRIMARY KEY,
                    name TEXT,
                    proxy_url TEXT,
                    api_id TEXT,
                    api_hash TEXT,
                    device_name TEXT,
                    phone TEXT,
                    username TEXT,
                    data_json TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workdir TEXT,
                    action TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            ''')
            
            # Очищаем старые настройки и аккаунты для зеркала
            cursor.execute("DELETE FROM settings")
            for k, v in data.get("settings", {}).items():
                cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (k, json.dumps(v)))
                
            cursor.execute("DELETE FROM accounts")
            
            accs = []
            for acc in data.get("accounts", []):
                accs.append((
                    str(acc.get("workdir", "")),
                    acc.get("name"),
                    acc.get("proxy_url"),
                    str(acc.get("api_id", "")),
                    acc.get("api_hash"),
                    acc.get("device_name"),
                    acc.get("phone"),
                    acc.get("username"),
                    json.dumps(acc)
                ))
            
            cursor.executemany('''
                INSERT INTO accounts (workdir, name, proxy_url, api_id, api_hash, device_name, phone, username, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', accs)
            
            conn.commit()
    except Exception as e:
        logger.error(f"SQLite Mirror Error: {e}")

def log_analytics_action(config_file: Path, workdir: str, action: str, details: str = ""):
    """Записывает действие в таблицу аналитики."""
    db_path = config_file.with_suffix('.db')
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workdir TEXT,
                    action TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            ''')
            cursor.execute(
                "INSERT INTO analytics (workdir, action, details) VALUES (?, ?, ?)",
                (workdir, action, details)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Analytics Error: {e}")

from typing import Any, Optional
import sqlite3
import os
from src.core.base_module import BaseModule

"""
Модуль извлечения номера телефона аккаунта.
Функции:

- run: чтение sqlite-файла сессии и вывод привязанного номера телефона в лог.
"""

class GetPhoneNumberPlugin(BaseModule):
    MODULE_NAME: str = "📱 Получить номер телефона"
    MODULE_DESC: str = "Мгновенно извлекает привязанный к сессии номер телефона напрямую из базы данных без подключения к сети."
    
    async def run(self, **kwargs: Any) -> None:
        """Извлечение номера телефона из локальной базы данных сессии"""
        if not self.workdir:
            self.log("Рабочая директория не указана!", "error")
            return

        # Находим файл сессии
        from src.core.utils import find_session_file
        session_path = find_session_file(self.workdir)
        if not session_path:
            self.log("Файл сессии (.session) не найден!", "error")
            return

        try:
            self.log("Считываю локальную базу данных сессии...", "info")
            phone, err = self._get_phone_from_db(session_path)
            
            if phone:
                self.log(f"Успешно извлечен номер телефона: +{phone}", "success")
            else:
                self.log(f"Не удалось получить номер: {err}", "error")
                
        except Exception as e:
            self.log(f"Критическая ошибка: {e}", "error")

    def _get_phone_from_db(self, db_path: str) -> tuple[Optional[str], Optional[str]]:
        """Прямой sqlite3 запрос к базе данных Pyrogram/Hydrogram сессии"""
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 1. Извлекаем user_id владельца сессии
            cursor.execute("SELECT user_id FROM sessions WHERE user_id IS NOT NULL LIMIT 1")
            row = cursor.fetchone()
            if not row or not row[0]:
                return None, "user_id не найден в sessions (возможно, сессия не авторизована)"
            
            user_id = row[0]
            
            # 2. По найденному ID ищем номер телефона в таблице пиров (peers)
            cursor.execute("SELECT phone_number FROM peers WHERE id = ?", (user_id,))
            row_phone = cursor.fetchone()
            
            if row_phone and row_phone[0]:
                return str(row_phone[0]).strip("+"), None
            else:
                return None, f"Номер отсутствует в peers для владельца сессии (ID: {user_id})"
                
        except sqlite3.Error as se:
            return None, f"Ошибка SQLite: {se}"
        finally:
            if conn:
                conn.close()

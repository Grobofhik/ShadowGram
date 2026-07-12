import os
import sys
import asyncio
from pathlib import Path
import json

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from hydrogram import Client
from src.core.managers import config_manager
from src.core.constants import CONFIG_FILE

class TelegramScout:
    """
    Скаут для сбора информации об аккаунтах (Фаза 1.2).
    В целях безопасности фермы (антибан) НЕ ПОДКЛЮЧАЕТСЯ к Telegram напрямую.
    Вместо этого читает всю известную информацию из локальной SQLite базы (config.db).
    """
    def __init__(self, file_state: dict):
        self.file_state = file_state
        self.db_path = Path(CONFIG_FILE).with_suffix('.db')
        
    async def run_audit(self):
        """Проходит по всем active аккаунтам из FileScout и обогащает их данными из БД."""
        import sqlite3
        from src.core.logger import logger
        
        # Если БД не существует, возвращаем как есть (чтобы не упало)
        if not self.db_path.exists():
            logger.warning("SQLite DB not found, skipping TelegramScout audit")
            return self.file_state
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                for acc_name, state in self.file_state.items():
                    if state["status"] == "active":
                        workdir_str = str(state["workdir"])
                        cursor.execute("SELECT * FROM accounts WHERE workdir = ?", (workdir_str,))
                        row = cursor.fetchone()
                        
                        if not row:
                            continue
                            
                        # Читаем данные из колонок SQLite
                        state["first_name"] = row["first_name"] or ""
                        state["username"] = row["username"] or ""
                        state["bio"] = row["bio"]
                        
                        # Проверяем наличие аватара
                        workdir = Path(state["workdir"])
                        has_avatar = False
                        if workdir.exists():
                            if list(workdir.glob("avatar*.jpg")) or list(workdir.glob("profile*.jpg")):
                                has_avatar = True
                        state["has_avatar"] = has_avatar
                        
                        # Проверяем личный канал
                        channel_link = row["channel_link"]
                        bound_channel = row["bound_channel"]
                        if channel_link or bound_channel:
                            state["has_personal_channel"] = True
                        else:
                            state["has_personal_channel"] = False
                            
                        # Заглушки для будущих функций безопасности
                        state["has_2fa"] = bool(row["password"])
                        state["privacy_setup"] = bool(row["privacy_guard"])
                        
        except Exception as e:
            logger.error(f"TelegramScout DB read error: {e}")

        return self.file_state

if __name__ == "__main__":
    from src.ai_agents.scouts.file_scout import FileScout
    
    # 1. Запускаем File Scout
    print("Running File Scout...")
    file_scout = FileScout()
    base_state = file_scout.run_audit()
    
    # 2. Запускаем Telegram Scout
    print("Running Telegram Scout...")
    tg_scout = TelegramScout(base_state)
    final_state = asyncio.run(tg_scout.run_audit())
    
    print(json.dumps(final_state, indent=2, ensure_ascii=False))

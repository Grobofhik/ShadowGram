import re
import asyncio
from typing import Any
from src.core.base_module import BaseModule

"""
Модуль перехвата кодов подтверждения Telegram.
Функции:

- run: ожидание входящих сообщений от сервисного аккаунта 777000 и поиск кодов
"""

class AuthCodePlugin(BaseModule):
    MODULE_NAME: str = "🔑 Получить код"
    MODULE_DESC: str = "Ожидает входящий код подтверждения от Telegram (777000)."

    async def run(self, **kwargs: Any) -> None:
        """Ожидание входящих сообщений от сервисного аккаунта 777000 и поиск кодов"""
        timeout: int = kwargs.get("timeout", 60)
        
        if not await self.init_client():
            return

        try:
            self.log("Слушаю сообщения от 777000...", "info")
            telegram_id = 777000
            
            # Сначала проверим последние сообщения (вдруг уже пришел)
            if await self._check_recent_messages(telegram_id):
                return

            # Если нет — ждем в реальном времени
            await self._wait_for_new_messages(telegram_id, timeout)
                
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")
        finally:
            await self.cleanup()
    
    async def _check_recent_messages(self, telegram_id: int) -> bool:
        """Проверяет последние сообщения на наличие кода"""
        async for message in self.client.get_chat_history(telegram_id, limit=3):
            if message.text:
                code = re.findall(r"\b(\d{5})\b", message.text)
                if code:
                    self.log(f"КОД НАЙДЕН: {code[0]}", "success")
                    return True
        return False
    
    async def _wait_for_new_messages(self, telegram_id: int, timeout: int) -> None:
        """Ожидает новые сообщения в реальном времени"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            if await self._check_new_message(telegram_id):
                return
            await asyncio.sleep(2)
                
        self.log("Время ожидания истекло. Код не найден.", "warning")
    
    async def _check_new_message(self, telegram_id: int) -> bool:
        """Проверяет новое сообщение на наличие кода"""
        async for message in self.client.get_chat_history(telegram_id, limit=1):
            if message.text:
                code = re.findall(r"\b(\d{5})\b", message.text)
                if code:
                    self.log(f"ПОЛУЧЕН НОВЫЙ КОД: {code[0]}", "success")
                    return True
        return False

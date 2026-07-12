import asyncio
from typing import Any, Optional
from src.core.base_module import BaseModule
from hydrogram.errors import UsernameOccupied, UsernameInvalid

class SetUsernamePlugin(BaseModule):
    MODULE_NAME: str = "📝 Установить Юзернейм"
    MODULE_DESC: str = "Устанавливает юзернейм на аккаунт. Берет один из списка и удаляет его для предотвращения дублей."
    SINGLE_ACCOUNT: bool = False
    
    _lock = asyncio.Lock()
    
    PARAMS = [
        {"name": "usernames_text", "type": "textarea", "label": "Список юзернеймов (по 1 в строку, без @)"}
    ]

    async def run(self, **kwargs: Any) -> None:
        if not await self.init_client():
            return

        usernames_text = kwargs.get("usernames_text", "").strip()
        if not usernames_text:
            self.log("Поле со списком юзернеймов пустое!", "error")
            return

        target_username = None

        # Блокировка для извлечения уникального юзернейма из общего словаря kwargs
        async with self._lock:
            # Превращаем текст в список и сохраняем его в kwargs (который разделяется между потоками в Python)
            if "_parsed_usernames" not in kwargs:
                def extract_un(u: str) -> str:
                    u = u.strip().replace('@', '')
                    if "/" in u: u = u.rstrip('/').split('/')[-1]
                    return u
                kwargs["_parsed_usernames"] = [extract_un(u) for u in usernames_text.split('\n') if u.strip()]
            
            if not kwargs["_parsed_usernames"]:
                self.log("Свободные юзернеймы в списке закончились!", "error")
                return
            
            target_username = kwargs["_parsed_usernames"].pop(0)

        try:
            self.log(f"Установка юзернейма: @{target_username}...", "info")
            await self.client.set_username(target_username)
            self.log(f"Юзернейм @{target_username} успешно установлен!", "success")
            
            # Сохранение юзернейма в конфигурацию аккаунта
            from src.core.managers import account_manager
            from src.core.constants import CONFIG_FILE
            
            if self.workdir:
                account_manager.update_account_profile_data(CONFIG_FILE, self.workdir, username=target_username)
                
        except UsernameOccupied:
            self.log(f"Юзернейм @{target_username} уже занят!", "error")
        except UsernameInvalid:
            self.log(f"Юзернейм @{target_username} недопустим!", "error")
        except Exception as e:
            self.log(f"Ошибка при установке юзернейма: {e}", "error")
        finally:
            await self.cleanup()

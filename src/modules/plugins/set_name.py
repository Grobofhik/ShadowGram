import asyncio
from typing import Any, Optional
from src.core.base_module import BaseModule

class SetNamePlugin(BaseModule):
    MODULE_NAME: str = "📝 Установить Имя и Фамилию"
    MODULE_DESC: str = "Устанавливает имя и фамилию на аккаунт. Берет строку из списка по очереди."
    SINGLE_ACCOUNT: bool = False
    
    _lock = asyncio.Lock()
    
    PARAMS = [
        {"name": "names_text", "type": "textarea", "label": "Список имен (по 1 в строку. Если нужно без фамилии - просто пиши Имя)"}
    ]

    async def run(self, **kwargs: Any) -> None:
        if not await self.init_client():
            return

        names_text = kwargs.get("names_text", "").strip()
        if not names_text:
            self.log("Поле со списком имен пустое!", "error")
            return

        target_name_line = None

        # Блокировка для извлечения уникального имени из общего словаря kwargs
        async with self._lock:
            if "_parsed_names" not in kwargs:
                kwargs["_parsed_names"] = [n.strip() for n in names_text.split('\n') if n.strip()]
            
            if not kwargs["_parsed_names"]:
                self.log("Имена в списке закончились!", "error")
                return
            
            target_name_line = kwargs["_parsed_names"].pop(0)

        parts = target_name_line.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        try:
            self.log(f"Установка имени: {first_name} {last_name}...", "info")
            await self.client.update_profile(first_name=first_name, last_name=last_name)
            self.log(f"Имя {first_name} {last_name} успешно установлено!", "success")
            
            # Сохранение имени в конфигурацию аккаунта
            from src.core.managers import account_manager
            from src.core.constants import CONFIG_FILE
            
            if self.workdir:
                account_manager.update_account_profile_data(CONFIG_FILE, self.workdir, first_name=first_name, last_name=last_name)
                
        except Exception as e:
            self.log(f"Ошибка при установке имени: {e}", "error")
        finally:
            await self.cleanup()

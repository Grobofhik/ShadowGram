import asyncio
from typing import Any
from src.core.base_module import BaseModule

class SetBioPlugin(BaseModule):
    MODULE_NAME: str = "📝 Установить Био (О себе)"
    MODULE_DESC: str = "Устанавливает биографию (о себе) на аккаунт. Берет строку из списка по очереди."
    SINGLE_ACCOUNT: bool = False
    
    _lock = asyncio.Lock()
    
    PARAMS = [
        {"name": "bios_text", "type": "textarea", "label": "Список био (по 1 в строку)"}
    ]

    async def run(self, **kwargs: Any) -> None:
        if not await self.init_client():
            return

        bios_text = kwargs.get("bios_text", "").strip()
        if not bios_text:
            self.log("Поле со списком био пустое!", "error")
            return

        target_bio = None

        # Блокировка для извлечения уникального био из общего словаря kwargs
        async with self._lock:
            if "_parsed_bios" not in kwargs:
                kwargs["_parsed_bios"] = [b.strip() for b in bios_text.split('\n') if b.strip()]
            
            if not kwargs["_parsed_bios"]:
                self.log("Био в списке закончились!", "error")
                return
            
            target_bio = kwargs["_parsed_bios"].pop(0)

        try:
            self.log(f"Установка био: {target_bio}...", "info")
            await self.client.update_profile(bio=target_bio)
            self.log(f"Био успешно установлено!", "success")
            
            # Сохранение био в конфигурацию аккаунта
            from src.core.managers import account_manager
            from src.core.constants import CONFIG_FILE
            
            if self.workdir:
                account_manager.update_account_profile_data(CONFIG_FILE, self.workdir, bio=target_bio)
                
        except Exception as e:
            self.log(f"Ошибка при установке био: {e}", "error")
        finally:
            await self.cleanup()

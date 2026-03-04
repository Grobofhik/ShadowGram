import shutil
from typing import Any, Optional
from pathlib import Path
from src.core.base_module import BaseModule

"""
Модуль установки новой аватарки для профиля.
Функции:

- run: подключение к клиенту и установка фото из указанного пути
"""

class SetAvatarPlugin(BaseModule):
    MODULE_NAME: str = "🖼️ Установить аватарку"
    MODULE_DESC: str = "Устанавливает новое фото профиля из выбранного файла."
    SINGLE_ACCOUNT: bool = True
    
    # Описываем параметры для UI
    PARAMS = [
        {"name": "photo_path", "type": "file", "label": "Выбрать изображение"}
    ]

    async def run(self, **kwargs: Any) -> None:
        """Подключение к клиенту и установка фото из указанного пути"""
        photo_path: Optional[str] = kwargs.get("photo_path")
        
        if not photo_path or not Path(photo_path).exists():
            self.log("Путь к фото не указан или файл не существует!", "error")
            return

        if not await self.init_client():
            return

        try:
            photo_path_obj = Path(photo_path)
            self.log(f"Установка новой аватарки: {photo_path_obj.name}...", "info")
            await self.client.set_profile_photo(photo=str(photo_path_obj))
            self.log("Аватарка успешно установлена!", "success")
            
            # Также обновим локальную аватарку в папке профиля для UI
            await self._update_local_avatar(photo_path_obj)
            
        except Exception as e:
            self.log(f"Ошибка при установке фото: {e}", "error")
        finally:
            await self.cleanup()
    
    async def _update_local_avatar(self, photo_path: Path) -> None:
        """Обновляет локальную аватарку в папке профиля"""
        if self.workdir:
            local_dest = Path(self.workdir) / "avatar.jpg"
            try:
                shutil.copy2(photo_path, local_dest)
            except Exception:
                pass

import shutil
import os
import asyncio
from typing import Any, Optional
from pathlib import Path
from src.core.base_module import BaseModule

class SetAvatarPlugin(BaseModule):
    MODULE_NAME: str = "🖼️ Установить аватарку"
    MODULE_DESC: str = "Устанавливает уникальное фото профиля из папки 'avatars'. Защищено от дублей."
    SINGLE_ACCOUNT: bool = False
    
    # Блокировка для безопасного взятия аватарки при многопоточности (Оркестраторе)
    _lock = asyncio.Lock()
    
    PARAMS = [
        {"name": "avatars_dir", "type": "folder", "label": "Папка с аватарками (по умолчанию 'avatars')"}
    ]

    async def run(self, **kwargs: Any) -> None:
        """Подключение к клиенту и установка фото из указанного пути"""
        
        # Получаем директорию из параметров или берем по умолчанию корень/avatars
        avatars_dir = kwargs.get("avatars_dir")
        if not avatars_dir:
            avatars_dir = os.path.join(os.getcwd(), "avatars")
            
        avatars_path = Path(avatars_dir)
        
        # Создаем папки если их нет
        if not avatars_path.exists():
            avatars_path.mkdir(parents=True, exist_ok=True)
            
        photo_path = None
        
        # Безопасно для всех потоков берем уникальную аватарку
        async with self._lock:
            valid_exts = {".jpg", ".jpeg", ".png"}
            # Ищем все файлы
            available_files = [f for f in avatars_path.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
            
            if not available_files:
                self.log(f"В папке {avatars_path} нет картинок для установки!", "error")
                return
                
            # Берем первую попавшуюся
            photo_path_obj = available_files[0]
            
            # Перемещаем её в папку used, чтобы другие аккаунты её не взяли
            used_dir = avatars_path / "used"
            used_dir.mkdir(exist_ok=True)
            
            new_path = used_dir / photo_path_obj.name
            counter = 1
            while new_path.exists():
                new_path = used_dir / f"{photo_path_obj.stem}_{counter}{photo_path_obj.suffix}"
                counter += 1
                
            try:
                shutil.move(str(photo_path_obj), str(new_path))
                photo_path = new_path
            except Exception as e:
                self.log(f"Не удалось переместить фото: {e}", "error")
                return

        if not await self.init_client():
            return

        try:
            self.log(f"Установка новой аватарки: {photo_path.name}...", "info")
            await self.client.set_profile_photo(photo=str(photo_path))
            self.log("Аватарка успешно установлена!", "success")
            
            # Также обновим локальную аватарку в папке профиля для интерфейса
            await self._update_local_avatar(photo_path)
            
        except Exception as e:
            self.log(f"Ошибка при установке фото: {e}", "error")
        finally:
            await self.cleanup()
    
    async def _update_local_avatar(self, photo_path: Path) -> None:
        """Обновляет локальную аватарку в папке профиля (чтоб крутилась в интерфейсе)"""
        if self.workdir:
            local_dest = Path(self.workdir) / "avatar.jpg"
            try:
                shutil.copy2(photo_path, local_dest)
            except Exception:
                pass

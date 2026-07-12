import asyncio
import os
import random
from pathlib import Path
from hydrogram import Client
from src.core.logger import logger

async def run(client: Client, params: dict, context: dict) -> bool:
    """
    Воркер: Устанавливает случайный аватар.
    Берет картинки из папки assets/avatars/
    """
    try:
        me = await client.get_me()
        logger.info(f"[{me.first_name}] Воркер task_set_avatar запущен.")

        avatars_dir = Path("assets/avatars")
        if not avatars_dir.exists():
            avatars_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"[{me.first_name}] Папка {avatars_dir} была пуста. Сначала закиньте туда картинки (.jpg, .png).")
            return False

        valid_exts = {".jpg", ".jpeg", ".png"}
        images = [f for f in avatars_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
        
        if not images:
            logger.warning(f"[{me.first_name}] Нет картинок в {avatars_dir}.")
            return False

        random_image = random.choice(images)
        logger.info(f"[{me.first_name}] Выбрана аватарка: {random_image.name}")
        
        await client.set_profile_photo(photo=str(random_image))
        logger.info(f"[{me.first_name}] ✅ Аватар успешно установлен!")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка в task_set_avatar: {e}")
        return False

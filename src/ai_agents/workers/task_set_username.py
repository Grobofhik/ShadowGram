import asyncio
import random
import string
from hydrogram import Client
from src.core.logger import logger


async def run(client: Client, params: dict, context: dict) -> bool:
    """
    Воркер: Устанавливает случайный/сгенерированный юзернейм аккаунту.
    """
    try:
        me = await client.get_me()
        logger.info(f"[{me.first_name}] Воркер task_set_username запущен.")

        if me.username:
            logger.info(f"[{me.first_name}] Юзернейм уже установлен: @{me.username}. Пропуск.")
            return True

        target_username = params.get("username")
        
        if target_username:
            try:
                await client.set_username(target_username)
                logger.info(f"[{me.first_name}] ✅ Успешно установлен заданный юзернейм: @{target_username}")
                return True
            except Exception as e:
                logger.error(f"[{me.first_name}] Ошибка установки заданного юзернейма @{target_username}: {e}")
                return False

        # Если юзернейм не передан в параметрах, генерируем случайный
        base_name = me.first_name.lower().replace(" ", "") if me.first_name else "user"
        base_name = ''.join(c for c in base_name if c.isalnum())
        
        for _ in range(5):
            # Добавляем случайные символы/цифры к имени
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            new_username = f"{base_name}_{random_suffix}"
            
            try:
                await client.set_username(new_username)
                logger.info(f"[{me.first_name}] ✅ Успешно установлен юзернейм: @{new_username}")
                return True
            except Exception as e:
                if "USERNAME_OCCUPIED" in str(e):
                    logger.warning(f"[{me.first_name}] Юзернейм {new_username} занят. Пробуем другой...")
                    await asyncio.sleep(2)
                elif "USERNAME_INVALID" in str(e):
                    logger.warning(f"[{me.first_name}] Юзернейм {new_username} невалидный.")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"[{me.first_name}] Ошибка установки юзернейма: {e}")
                    return False
                    
        logger.error(f"[{me.first_name}] Не удалось подобрать юзернейм за 5 попыток.")
        return False
        
    except Exception as e:
        logger.error(f"Ошибка в task_set_username: {e}")
        return False

import asyncio
from hydrogram import Client
from src.core.logger import logger

async def run(client: Client, params: dict, context: dict) -> bool:
    """
    Воркер: Устанавливает имя и/или фамилию аккаунту.
    """
    try:
        me = await client.get_me()
        logger.info(f"[{me.first_name}] Воркер task_set_name запущен.")

        first_name = params.get("first_name")
        last_name = params.get("last_name")

        if not first_name and not last_name:
            logger.warning(f"[{me.first_name}] Ошибка: ни first_name, ни last_name не переданы для изменения.")
            return False
            
        # Если last_name не передан явно, мы его очищаем (по требованию - фамилии почти не используются)
        new_first_name = first_name if first_name is not None else me.first_name
        new_last_name = last_name if last_name is not None else ""
        
        try:
            await client.update_profile(first_name=new_first_name, last_name=new_last_name)
            logger.info(f"[{me.first_name}] ✅ Имя успешно обновлено: {new_first_name} {new_last_name or ''}")
            return True
        except Exception as e:
            logger.error(f"[{me.first_name}] Ошибка при обновлении профиля: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка в task_set_name: {e}")
        return False

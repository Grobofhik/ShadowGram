import asyncio
from hydrogram import Client
from src.core.logger import logger

async def run(client: Client, params: dict, context: dict) -> bool:
    """
    Воркер: Подписывается на каналы/группы.
    Ожидает в params список "channels".
    """
    try:
        me = await client.get_me()
        logger.info(f"[{me.first_name}] Воркер task_subscribe запущен.")

        channels = params.get("channels", [])
        if not channels:
            logger.warning(f"[{me.first_name}] Список каналов пуст. Нечего делать.")
            return True

        success_count = 0
        for channel in channels:
            # Очистка имени пользователя
            target = channel.strip().replace(" ", "")
            if not target:
                continue
                
            try:
                await client.join_chat(target)
                logger.info(f"[{me.first_name}] ✅ Успешно подписался на: {target}")
                success_count += 1
                await asyncio.sleep(5) # Антиспам
            except Exception as e:
                logger.error(f"[{me.first_name}] ❌ Ошибка подписки на {target}: {e}")
                
        return success_count > 0 or len(channels) == 0
        
    except Exception as e:
        logger.error(f"Ошибка в task_subscribe: {e}")
        return False

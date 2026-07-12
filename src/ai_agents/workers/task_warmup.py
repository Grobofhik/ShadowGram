import asyncio
import random
import time
from hydrogram import Client
from src.core.logger import logger

async def run(client: Client, params: dict, context: dict) -> bool:
    """
    Воркер: Имитация прогрева аккаунта (листание диалогов, открытие ботов).
    Параметр duration_sec задает сколько секунд греть аккаунт.
    """
    try:
        me = await client.get_me()
        duration = params.get("duration_sec", 60)
        logger.info(f"[{me.first_name}] Воркер task_warmup запущен (Прогрев {duration} сек).")

        start_time = time.time()
        
        # Получаем список диалогов для имитации чтения
        dialogs = []
        async for dialog in client.get_dialogs(limit=20):
            dialogs.append(dialog)
            
        bots_to_start = ["@gamee", "@QuizBot", "@vkmusic_bot"]

        while time.time() - start_time < duration:
            action = random.choice(["read_chat", "start_bot", "sleep"])
            
            if action == "read_chat" and dialogs:
                target = random.choice(dialogs)
                logger.info(f"[{me.first_name}] 🧐 'Читаем' чат: {target.chat.title or target.chat.first_name}")
                await asyncio.sleep(random.uniform(2, 5)) # "Чтение"
                
            elif action == "start_bot":
                target_bot = random.choice(bots_to_start)
                try:
                    logger.info(f"[{me.first_name}] 🤖 Открываем бота {target_bot}")
                    await client.send_message(target_bot, "/start")
                    await asyncio.sleep(random.uniform(3, 7))
                except Exception as e:
                    logger.debug(f"[{me.first_name}] Не удалось запустить бота {target_bot}: {e}")
                    
            elif action == "sleep":
                pause = random.uniform(2, 10)
                logger.info(f"[{me.first_name}] ☕ Пьем кофе ({pause:.1f} сек)...")
                await asyncio.sleep(pause)
                
        logger.info(f"[{me.first_name}] ✅ Прогрев завершен!")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка в task_warmup: {e}")
        return False

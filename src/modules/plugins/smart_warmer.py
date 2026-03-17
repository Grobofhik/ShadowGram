import asyncio
import random
from src.core.base_module import BaseModule
from hydrogram.errors import FloodWait, RPCError

"""
Модуль «Умный прогрев» (Smart Warmer).
Функции:

- run: вступление в чаты, чтение сообщений с задержками и пересылка постов в Избранное
"""

class SmartWarmerPlugin(BaseModule):
    MODULE_NAME = "🔥 Умный прогрев"
    MODULE_DESC = "Имитирует активность: вступает в чаты, читает сообщения и пересылает посты."
    
    PARAMS = [
        {"name": "chat_links", "type": "textarea", "label": "Ссылки на чаты (по одной в строке)"},
        {"name": "min_delay", "type": "text", "label": "Мин. задержка (сек)"},
        {"name": "max_delay", "type": "text", "label": "Макс. задержка (сек)"}
    ]

    async def run(self, **kwargs):
        # Получаем параметры
        links_raw = kwargs.get("chat_links", "")
        links = [l.strip() for l in links_raw.split("\n") if l.strip()]
        
        try:
            d_min = int(kwargs.get("min_delay", 5))
            d_max = int(kwargs.get("max_delay", 15))
        except:
            d_min, d_max = 5, 15

        if not links:
            self.log("Список чатов пуст!", "error")
            return

        if not await self.init_client():
            return

        try:
            random.shuffle(links) # Рандомизируем порядок чатов
            self.log(f"Начинаю прогрев на {len(links)} чатах...", "info")

            for link in links:
                try:
                    # 1. Пытаемся вступить или получить инфу о чате
                    self.log(f"Обработка: {link}...", "info")
                    chat = await self.client.join_chat(link)
                    self.log(f"Вступил в чат: {chat.title}", "success")
                    
                    # 2. Имитируем чтение сообщений (прокрутка)
                    # Читаем последние 5-10 сообщений
                    read_count = random.randint(5, 10)
                    async for message in self.client.get_chat_history(chat.id, limit=read_count):
                        await self.client.read_chat_history(chat.id, message.id)
                        await self.sleep(random.uniform(1, 3)) # Маленькая пауза между сообщениями
                    
                    self.log(f"Прочитано {read_count} сообщений в {chat.title}", "info")

                    # 3. Шанс 20% переслать пост в Избранное
                    if random.random() < 0.2:
                        # Берем случайное сообщение из последних 20
                        msgs = []
                        async for m in self.client.get_chat_history(chat.id, limit=20):
                            if m.text or m.photo: msgs.append(m)
                        
                        if msgs:
                            target = random.choice(msgs)
                            await target.forward("me")
                            self.log("Случайный пост переслан в Избранное!", "success")

                    # Пауза перед следующим чатом
                    wait_time = random.randint(d_min, d_max)
                    self.log(f"Жду {wait_time} сек. перед следующим действием...", "info")
                    await self.sleep(wait_time)

                except FloodWait as e:
                    self.log(f"Флуд-вейт {e.value} сек. Пропускаю чат.", "warning")
                    continue
                except RPCError as e:
                    self.log(f"Ошибка с чатом {link}: {e.MESSAGE}", "error")
                    continue
                except Exception as e:
                    self.log(f"Непредвиденная ошибка: {e}", "error")

            self.log("Прогрев для этого аккаунта завершен!", "success")
            
        finally:
            await self.cleanup()

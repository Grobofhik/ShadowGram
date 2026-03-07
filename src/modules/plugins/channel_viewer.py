import asyncio
import random
from src.core.base_module import BaseModule
from hydrogram.raw import functions

"""
Модуль «Channel Viewer» (Просмотр постов).
Функции:

- run: массовый просмотр сообщений в указанном канале с эмуляцией поведения человека
"""

class ChannelViewerPlugin(BaseModule):
    MODULE_NAME = "👁️ Накрутка просмотров"
    MODULE_DESC = "Параллельно просматривает посты в канале, имитируя активность."
    
    # Новая система жизненного цикла:
    IS_CYCLIC = True
    START_DELAY = (60, 7200) # Стартовая задержка от 1 до 120 минут
    CYCLE_DELAY = (10800, 21600) # Сон между циклами от 3 до 6 часов
    
    PARAMS = [
        {"name": "channel_link", "type": "text", "label": "Ссылка на канал (или ID)"},
        {"name": "post_limit", "type": "text", "label": "Лимит постов (60)"}
    ]

    async def run(self, **kwargs):
        channel_raw = kwargs.get("channel_link", "").strip()
        try:
            # Если передали числовой ID (например, -100...), приводим к int
            channel_id = int(channel_raw)
        except ValueError:
            # Иначе это текстовая ссылка (@username или t.me/...)
            channel_id = channel_raw

        try:
            limit = int(kwargs.get("post_limit", 60))
        except:
            limit = 60

        if not channel_id:
            self.log("ID или ссылка на канал не указана!", "error")
            return

        try:
            self.log(f"Начинаю сессию просмотра канала {channel_id}...", "info")

            # 1. Имитация живого присутствия: смотрим список чатов
            try:
                count = 0
                async for _ in self.client.get_dialogs(limit=5):
                    count += 1
            except Exception as e:
                self.log(f"Не удалось получить диалоги: {e}", "warning")
            
            start_delay = random.uniform(2, 5)
            self.log(f"Случайная микро-пауза: {start_delay:.1f} сек...", "info")
            await asyncio.sleep(start_delay)

            chat = None
            # 2. Получаем объект чата (с обработкой PEER_ID_INVALID)
            try:
                if isinstance(channel_id, str):
                    try:
                        chat = await self.client.join_chat(channel_id)
                    except Exception as join_err:
                        if "USER_ALREADY_PARTICIPANT" in str(join_err):
                            chat = await self.client.get_chat(channel_id)
                        else:
                            chat = await self.client.get_chat(channel_id)
                else:
                    chat = await self.client.get_chat(channel_id)
            except Exception as e:
                # Если сессия еще "не знает" этот чат (особенно актуально для приватных каналов по ID)
                if "PEER_ID_INVALID" in str(e):
                    self.log("Канал неизвестен локальному кешу. Ищу в диалогах...", "warning")
                    found = False
                    async for dialog in self.client.get_dialogs(limit=200):
                        if dialog.chat.id == channel_id or dialog.chat.username == channel_id:
                            chat = dialog.chat
                            found = True
                            break
                    if not found:
                        self.log("Канал не найден в последних диалогах. Аккаунт точно подписан?", "error")
                        return
                else:
                    self.log(f"Ошибка доступа к каналу: {e}", "error")
                    return

            if not chat:
                self.log("Не удалось получить объект чата.", "error")
                return

            self.log(f"Целевой чат определен: {chat.title} (ID: {chat.id})", "success")

            # 3. Собираем ID последних сообщений
            messages_ids = []
            async for message in self.client.get_chat_history(chat.id, limit=limit):
                if message.id:
                    messages_ids.append(message.id)

            if not messages_ids:
                self.log("В канале нет постов для просмотра.", "warning")
                return

            self.log(f"Найдено {len(messages_ids)} постов. Начинаю эмуляцию...", "info")
            random.shuffle(messages_ids)

            # Получение peer для низкоуровневого вызова
            target_peer = await self.client.resolve_peer(chat.id)
            
            # 4. Просмотр блоками (чанками)
            for i in range(0, len(messages_ids), random.randint(2, 5)):
                chunk = messages_ids[i : i + 5]
                if not chunk: continue 

                try:
                    # Сначала "загружаем" сообщения
                    await self.client.get_messages(chat.id, chunk)
                    await asyncio.sleep(random.uniform(1, 2))

                    # Накручиваем "глазик" через API
                    await self.client.invoke(
                        functions.messages.GetMessagesViews(
                            peer=target_peer,
                            id=chunk,
                            increment=True
                        )
                    )
                    # Читаем историю до макс. ID в блоке
                    await self.client.read_chat_history(chat.id, max_id=max(chunk)) 
                    
                except Exception as e:
                    self.log(f"Ошибка в блоке просмотров: {e}", "warning")
                    break

                # Имитируем долгое чтение: пауза 10-20 сек
                delay = random.uniform(10, 25)
                self.log(f"Читаю блок постов... пауза {delay:.1f} сек.", "info")
                await asyncio.sleep(delay)

            self.log(f"Просмотры для {channel_id} успешно завершены!", "success")

        except Exception as e:
            self.log(f"Критическая ошибка: {e}", "error")

import asyncio
import random
import os
from typing import Any, List, Union
from src.core.base_module import BaseModule
from hydrogram.errors import FloodWait, RPCError
from hydrogram import raw

class AutoReactor(BaseModule):
    MODULE_NAME = "💬 Авто-Реакции"
    MODULE_DESC = "Умный модуль: сам определяет разрешенные реакции (в т.ч. кастомные) и ставит их."
    
    PARAMS = [
        {"name": "channel_url", "type": "text", "label": "Ссылка на канал (@username или https://t.me/...)"},
        {"name": "posts_count", "type": "text", "label": "Сколько последних постов обработать (например: 5)"},
        {"name": "reaction_chance", "type": "text", "label": "Шанс поставить реакцию (в %, от 0 до 100)"}
    ]
    
    START_DELAY = (1, 15)
    IS_CYCLIC = False

    # Список безопасных дефолтных реакций
    DEFAULT_REACTIONS = ["👍", "❤", "🔥", "👏", "🎉", "🤩", "🙏", "👌"]

    async def run(self, channel_url: str, posts_count: str, reaction_chance: str, **kwargs: Any) -> Any:
        try:
            limit = int(posts_count.strip())
            r_chance = int(reaction_chance.strip())
        except ValueError:
            self.log("Ошибка: 'Количество постов' и 'Шанс' должны быть числами.", "error")
            return

        channel_url = channel_url.strip().replace("https://t.me/", "").replace("@", "")
        
        try:
            chat = await self.client.get_chat(channel_url)
            self.log(f"Начинаю работу с каналом: {chat.title}", "info")
            
            # Определяем список доступных реакций
            allowed_reactions = self._get_allowed_reactions(chat)
            
            if not allowed_reactions:
                self.log("В канале не найдено доступных реакций (возможно, они отключены).", "warning")
                return

            # Читаем историю
            messages = []
            async for msg in self.client.get_chat_history(chat.id, limit=limit):
                messages.append(msg)
                
            if not messages:
                self.log("В канале не найдено сообщений.", "warning")
                return

            self.log(f"Найдено {len(messages)} постов. Доступно реакций: {len(allowed_reactions)}", "info")

            # Обрабатываем сообщения снизу вверх
            for msg in reversed(messages):
                if getattr(msg, "service", False):
                    continue

                if random.randint(1, 100) <= r_chance:
                    choice = random.choice(allowed_reactions)
                    if not choice: continue

                    try:
                        # Используем raw API, так как высокоуровневый send_reaction в этой версии 
                        # плохо поддерживает кастомные эмодзи и типы
                        reaction_obj = None
                        if isinstance(choice, int):
                            reaction_obj = [raw.types.ReactionCustomEmoji(document_id=choice)]
                        else:
                            reaction_obj = [raw.types.ReactionEmoji(emoticon=choice)]

                        await self.client.invoke(
                            raw.functions.messages.SendReaction(
                                peer=await self.client.resolve_peer(chat.id),
                                msg_id=msg.id,
                                reaction=reaction_obj
                            )
                        )
                        
                        display_val = choice if isinstance(choice, str) else f"custom:{choice}"
                        self.log(f"Поставил реакцию {display_val} на пост ID: {msg.id}", "success")
                        
                        await asyncio.sleep(random.uniform(2.0, 5.0))
                    except FloodWait as e:
                        self.log(f"FloodWait: жду {e.value} сек...", "warning")
                        await asyncio.sleep(e.value)
                    except RPCError as e:
                        self.log(f"Ошибка реакции {choice}: {e.MESSAGE}", "warning")

                await asyncio.sleep(random.uniform(1.5, 4.0))

        except FloodWait as e:
            self.log(f"Лимит запросов Telegram, нужно подождать {e.value} сек.", "error")
        except Exception as e:
            self.log(f"Ошибка при работе: {e}", "error")

    def _get_allowed_reactions(self, chat: Any) -> List[Union[str, int]]:
        """
        Парсит объект Chat и возвращает список эмодзи (str) или ID кастомных эмодзи (int).
        """
        available = getattr(chat, "available_reactions", None)
        
        if available is None:
            return self.DEFAULT_REACTIONS

        # Проверяем флаги из ChatReactions (hydrogram 0.2.x)
        all_enabled = getattr(available, "all_are_enabled", False)
        # В некоторых версиях поле может называться all_are_allowed
        if not all_enabled:
            all_enabled = getattr(available, "all_are_allowed", False)

        if all_enabled:
            return self.DEFAULT_REACTIONS

        # Пробуем достать список реакций
        raw_list = getattr(available, "reactions", [])
        if not raw_list and isinstance(available, list):
            raw_list = available
        
        result = []
        for r in raw_list:
            val = None
            if hasattr(r, "emoji") and r.emoji:
                val = r.emoji
            elif hasattr(r, "custom_emoji_id") and r.custom_emoji_id:
                val = r.custom_emoji_id
            elif isinstance(r, (str, int)):
                val = r
            
            if val:
                result.append(val)
        
        return result if result else self.DEFAULT_REACTIONS

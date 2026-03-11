import asyncio
import random
import os
from typing import Any
from src.core.base_module import BaseModule
from hydrogram.errors import FloodWait, RPCError

class AICommenter(BaseModule):
    MODULE_NAME = "🤖 Умный AI-Комментер"
    MODULE_DESC = "Читает посты в канале и генерирует уникальные комментарии через бесплатный API нейросетей, используя индивидуальные промпты аккаунтов."
    
    PARAMS = [
        {"name": "channel_url", "type": "text", "label": "Ссылка на канал (@username или https://t.me/...)"},
        {"name": "api_key", "type": "text", "label": "Ваш API ключ (например, от Groq или OpenRouter)"},
        {"name": "api_base_url", "type": "text", "label": "Base URL API (например: https://api.groq.com/openai/v1)"},
        {"name": "model_name", "type": "text", "label": "Название модели (например: llama-3.1-8b-instant)"},
        {"name": "posts_count", "type": "text", "label": "Сколько последних постов обработать (например: 3)"},
        {"name": "comment_chance", "type": "text", "label": "Вероятность оставить комментарий (0-100%)"}
    ]
    
    START_DELAY = (1, 15)
    IS_CYCLIC = False

    async def _generate_comment(self, post_text: str, system_prompt: str, api_key: str, api_url: str, model_name: str) -> str:
        """Обращение к OpenAI-совместимому API для генерации текста"""
        import requests
        
        # Обрезаем пост, если он слишком длинный, чтобы сэкономить токены
        short_post = post_text[:1000] if post_text else "[Фото/Видео без текста]"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Напиши ответ на этот пост:\n\n{short_post}"}
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }
        
        try:
            # Выполняем синхронный запрос в отдельном потоке, чтобы не блокировать цикл
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(f"{api_url}/chat/completions", headers=headers, json=payload, timeout=15)
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
            else:
                self.log(f"Ошибка API {response.status_code}: {response.text}", "error")
                return ""
        except Exception as e:
            self.log(f"Ошибка сети при запросе к AI: {e}", "error")
            return ""

    async def run(self, channel_url: str, api_key: str, api_base_url: str, model_name: str, posts_count: str, comment_chance: str, **kwargs: Any) -> Any:
        try:
            limit = int(posts_count.strip())
            c_chance = int(comment_chance.strip())
        except ValueError:
            self.log("Ошибка: 'Количество постов' и 'Вероятность' должны быть числами.", "error")
            return

        api_key = api_key.strip()
        api_base_url = api_base_url.strip().rstrip("/")
        model_name = model_name.strip()
        channel_url = channel_url.strip().replace("https://t.me/", "").replace("@", "")
        
        # Получаем индивидуальный промпт аккаунта
        system_prompt = self.acc.get("ai_prompt")
        if not system_prompt:
            self.log("У этого аккаунта нет индивидуального AI промпта! Использую стандартный.", "warning")
            system_prompt = "Напиши короткий, позитивный и естественный комментарий (от 2 до 8 слов) на пост пользователя. Без хештегов, без приветствий."

        if not api_key:
            self.log("Ошибка: API ключ не указан.", "error")
            return

        try:
            chat = await self.client.get_chat(channel_url)
            self.log(f"Начинаю работу с каналом: {chat.title}", "info")
            
            messages = []
            async for msg in self.client.get_chat_history(chat.id, limit=limit):
                messages.append(msg)
                
            if not messages:
                self.log("В канале не найдено сообщений.", "warning")
                return

            self.log(f"Найдено {len(messages)} сообщений. Начинаю генерацию.", "info")

            for msg in reversed(messages):
                if getattr(msg, "service", False):
                    continue

                if random.randint(1, 100) <= c_chance:
                    # Читаем пост (имитация)
                    await asyncio.sleep(random.uniform(2.0, 5.0))
                    
                    self.log(f"Генерирую комментарий для поста ID: {msg.id}...", "info")
                    comment_text = await self._generate_comment(msg.text or msg.caption or "", system_prompt, api_key, api_base_url, model_name)
                    
                    if comment_text:
                        try:
                            # Очищаем ответ от возможных кавычек, если нейросеть их добавила
                            comment_text = comment_text.strip('"\'')
                            
                            # Получаем системное сообщение из привязанной группы комментариев
                            discussion_msg = await self.client.get_discussion_message(chat.id, msg.id)
                            
                            try:
                                await discussion_msg.reply(comment_text)
                            except RPCError as e:
                                if "CHAT_GUEST_SEND_FORBIDDEN" in str(e):
                                    self.log("Требуется вступление в группу комментариев. Вступаем...", "warning")
                                    await self.client.join_chat(discussion_msg.chat.id)
                                    await asyncio.sleep(random.uniform(2.0, 5.0))
                                    await discussion_msg.reply(comment_text)
                                else:
                                    raise e
                            
                            self.log(f"💬 Отправлено: '{comment_text}'", "success")
                            
                            # Большая пауза после комментария
                            await asyncio.sleep(random.uniform(10.0, 30.0))
                        except FloodWait as e:
                            self.log(f"FloodWait: жду {e.value} сек...", "warning")
                            await asyncio.sleep(e.value)
                        except RPCError as e:
                            self.log(f"Не удалось оставить коммент (возможно закрыты): {e}", "warning")
                    else:
                        self.log("Нейросеть не вернула текст комментария.", "warning")
                        
                else:
                    self.log(f"Пропуск комментария для поста {msg.id} (шанс)", "info")
                    await asyncio.sleep(random.uniform(1.0, 3.0))

        except FloodWait as e:
            self.log(f"Лимит запросов Telegram, нужно подождать {e.value} сек.", "error")
        except Exception as e:
            self.log(f"Ошибка при работе: {e}", "error")
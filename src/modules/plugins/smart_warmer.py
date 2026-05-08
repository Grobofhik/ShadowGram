import asyncio
import random
from src.core.base_module import BaseModule
from hydrogram.errors import FloodWait, RPCError
from hydrogram import raw

"""
Модуль «🔥 Умный прогрев 2.0» (Smart Warmer).
Улучшенная версия:
- Имитация чтения постов с задержкой, зависящей от длины текста.
- Автоматическая расстановка реакций (лайки, огоньки).
- Пересылка интересных постов в Избранное (Saved Messages).
- Взаимодействие с ботами (отправка команд /start, /help).
- Умное общение в чатах с помощью AI.
"""

class SmartWarmerPlugin(BaseModule):
    MODULE_NAME = "🔥 Умный прогрев"
    MODULE_DESC = "Имитирует человеческое поведение: чтение каналов с реакциями, пересылка в избранное, общение с ботами и AI-общение в чатах."
    
    PARAMS = [
        {"name": "chat_links", "type": "textarea", "label": "Ссылки на группы/чаты (по одной в строке)"},
        {"name": "use_bots", "type": "checkbox", "label": "Взаимодействовать с ботами"},
        {"name": "reactions_chance", "type": "text", "label": "Шанс реакции (%) (0-100)"},
        {"name": "write_chance", "type": "text", "label": "Шанс написать сообщение в чат (%) (0-100)"},
        {"name": "api_key", "type": "text", "label": "API Ключ (Groq/OpenRouter)"},
        {"name": "api_base_url", "type": "text", "label": "Base URL API"},
        {"name": "model_name", "type": "text", "label": "Название модели"},
        {"name": "min_delay", "type": "text", "label": "Мин. задержка между действиями (сек)"},
        {"name": "max_delay", "type": "text", "label": "Макс. задержка между действиями (сек)"}
    ]

    COMMON_REACTIONS = ["👍", "🔥", "❤️", "🤩", "👏", "🎉", "🤔", "👌"]
    WUP_BOTS = ["@GifsItBot", "@pic", "@bing", "@StorageBot", "@vkmusic_bot", "@Sticker", "@QuizBot"]

    async def _generate_message(self, context_messages: list, system_prompt: str, api_key: str, api_url: str, model_name: str) -> str:
        """Генерация сообщения на основе контекста чата"""
        import requests
        
        # Собираем последние сообщения для понимания контекста
        context_text = "\n".join([f"{m.from_user.first_name if m.from_user else 'User'}: {m.text}" for m in context_messages if m.text])
        short_context = context_text[-1500:] if context_text else "Привет всем!"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt + "\nПиши коротко, как обычный человек в живом чате Telegram. Не используй хештеги и длинные приветствия. Отвечай органично в контекст беседы."},
                {"role": "user", "content": f"Вот последние сообщения в чате:\n{short_context}\n\nНапиши уместное короткое сообщение в этот чат от своего лица."}
            ],
            "max_tokens": 100,
            "temperature": 0.8
        }
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(f"{api_url}/chat/completions", headers=headers, json=payload, timeout=15)
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content'].strip(' "\'')
            else:
                self.log(f"Ошибка API {response.status_code}: {response.text}", "error")
                return ""
        except Exception as e:
            self.log(f"Ошибка сети при запросе к AI: {e}", "error")
            return ""

    async def run(self, **kwargs):
        links_raw = kwargs.get("chat_links", "")
        links = [l.strip() for l in links_raw.split("\n") if l.strip()]
        
        use_bots = kwargs.get("use_bots", False)
        
        try:
            r_chance = float(kwargs.get("reactions_chance", 15)) / 100
        except: r_chance = 0.15
        
        try:
            w_chance = float(kwargs.get("write_chance", 0)) / 100
        except: w_chance = 0.0

        try:
            d_min = int(kwargs.get("min_delay", 5))
            d_max = int(kwargs.get("max_delay", 15))
        except: d_min, d_max = 5, 15

        api_key = kwargs.get("api_key", "").strip()
        api_base_url = kwargs.get("api_base_url", "").strip().rstrip("/")
        model_name = kwargs.get("model_name", "").strip()

        if not await self.init_client():
            return

        try:
            if use_bots:
                bot_username = random.choice(self.WUP_BOTS)
                self.log(f"Прогрев через бота: {bot_username}", "info")
                try:
                    await self.client.send_message(bot_username, "/start")
                    await self.sleep(random.randint(2, 5))
                    if random.random() < 0.5:
                        await self.client.send_message(bot_username, "/help")
                    self.log(f"Отправлены команды боту {bot_username}", "success")
                except Exception as e:
                    self.log(f"Не удалось пообщаться с ботом: {e}", "warning")

            if links:
                random.shuffle(links)
                self.log(f"Начинаю обход {len(links)} чатов...", "info")

                for link in links:
                    try:
                        self.log(f"Захожу в: {link}", "info")
                        chat = await self.client.join_chat(link)
                        
                        read_count = random.randint(3, 7)
                        context_msgs = []
                        
                        async for message in self.client.get_chat_history(chat.id, limit=read_count):
                            context_msgs.append(message)
                            
                            text_len = len(message.text or "") + len(message.caption or "")
                            read_time = min(max(2, text_len // 50), 10) 
                            
                            self.log(f"Читаю пост {message.id} ({read_time} сек.)...", "info")
                            await self.client.read_chat_history(chat.id, message.id)
                            await self.sleep(read_time)

                            if random.random() < r_chance:
                                try:
                                    reaction = random.choice(self.COMMON_REACTIONS)
                                    await self.client.send_reaction(chat.id, message.id, reaction)
                                    self.log(f"Поставил реакцию {reaction} на пост {message.id}", "success")
                                except: pass 

                            if random.random() < 0.05:
                                try:
                                    await message.forward("me")
                                    self.log("Пост сохранен в Избранное", "success")
                                except: pass

                        # Пишем сообщение в чат с шансом w_chance
                        if w_chance > 0 and api_key and random.random() < w_chance:
                            try:
                                self.log(f"Генерирую AI-сообщение для чата...", "info")
                                context_msgs.reverse() # Старые сообщения первыми
                                sys_prompt = self.acc.get("ai_prompt") or "Ты обычный пользователь Telegram. Участвуешь в беседе. Твой стиль общения повседневный и расслабленный."
                                
                                reply_text = await self._generate_message(context_msgs, sys_prompt, api_key, api_base_url, model_name)
                                if reply_text:
                                    # Имитируем набор текста
                                    typing_time = min(len(reply_text) / 10, 10.0) # 1 сек на 10 символов, макс 10 сек
                                    await self.sleep(max(1.0, typing_time))
                                    
                                    await self.client.send_message(chat.id, reply_text)
                                    self.log(f"💬 Отправлено в чат: '{reply_text}'", "success")
                                    await self.sleep(random.uniform(3, 8))
                            except RPCError as e:
                                self.log(f"Не удалось написать в чат (мут/закрыт): {e}", "warning")
                            except Exception as e:
                                self.log(f"Ошибка отправки сообщения: {e}", "error")

                        await self.sleep(random.randint(d_min, d_max))

                    except FloodWait as e:
                        self.log(f"Флуд-вейт {e.value} сек. Ожидаю...", "warning")
                        await self.sleep(e.value)
                    except RPCError as e:
                        self.log(f"Ошибка канала {link}: {e}", "warning")
                        continue
                    except Exception as e:
                        self.log(f"Ошибка при обработке {link}: {e}", "error")

            self.log("Сессия умного прогрева завершена!", "success")
            
        finally:
            await self.cleanup()


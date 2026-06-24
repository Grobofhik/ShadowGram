import asyncio
import random
import os
import re
import time
from src.core.base_module import BaseModule
from hydrogram.errors import FloodWait, RPCError
from hydrogram import raw
from hydrogram.types import ChatPermissions

"""
Модуль «🔥 Умный прогрев 2.0» (Smart Warmer).
Улучшенная версия с полной интеграцией всех 12 тумблеров тонкой настройки прогрева:
- Имитация чтения постов, диалогов и каналов.
- Автоматическая расстановка реакций и участие в опросах.
- Пересылка интересных постов в Избранное (Saved Messages).
- Взаимодействие с ботами и AI-общение в чатах с симуляцией печати.
- Архивирование и заглушение чатов, симуляция просмотра профилей.
- Прослушивание голосовых сообщений и просмотр видео на лету.
- Глобальный поиск, синхронизация контактов, черновики, отложенные сообщения.
- Эмодзи-статусы и постепенное автообновление профиля.
"""

class SmartWarmerPlugin(BaseModule):
    MODULE_NAME = "🔥 Умный прогрев"
    MODULE_DESC = "Имитирует человеческое поведение: чтение каналов с реакциями, пересылка в избранное, общение с ботами и AI-общение в чатах с учетом 24 тумблеров тонких настроек."
    
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
    WUP_BOTS = ["@gamee", "@QuizBot", "@Stickers", "@vkmusic_bot", "@imdb"]

    def _clean_link(self, link: str) -> str:
        link = link.strip().replace(" ", "")
        if not link:
            return ""
        if link.startswith("@"):
            return link[1:]
        if "t.me/" in link:
            parts = link.split("t.me/")
            path = parts[-1].strip("/")
            if path.startswith("+"):
                return path
            if path.startswith("joinchat/"):
                hash_part = path.replace("joinchat/", "").split("?")[0].split("/")[0]
                return f"+{hash_part}"
            username = path.split("?")[0].split("/")[0]
            return username
        return link

    async def _human_delay(self, scale: float = 1.0):
        """Вносит случайную человеческую паузу на основе установленных в UI задержек"""
        d_min = getattr(self, "d_min", 3)
        d_max = getattr(self, "d_max", 7)
        delay = random.uniform(d_min, d_max) * scale
        delay = round(delay, 1)
        if delay > 0.1:
            self.log(f"⏳ Симуляция паузы: {delay} сек...", "info")
            await self.sleep(delay)

    async def _generate_message(self, context_messages: list, system_prompt: str, api_key: str, api_url: str, model_name: str) -> str:
        """Генерация сообщения на основе контекста чата"""
        import requests
        
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

    async def _task_check_privacy(self):
        self.log("Выполняется проверка и верификация настроек приватности аккаунта...", "info")
        await self._human_delay(0.5)
        try:
            await self.client.invoke(raw.functions.account.GetPrivacy(
                key=raw.types.InputPrivacyKeyStatusTimestamp()
            ))
            self.log("Проверка приватности завершена.", "success")
            await self._human_delay(0.3)
        except Exception as e:
            self.log(f"Не удалось получить настройки приватности: {e}", "warning")

    async def _task_sync_contacts(self):
        self.log("Синхронизация контактов...", "info")
        await self._human_delay(0.6)
        try:
            names = ["Иван", "Александр", "Дмитрий", "Сергей", "Елена", "Ольга", "Татьяна", "Михаил", "Анна"]
            surnames = ["Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов", "Попов", "Васильев"]
            phone = f"+79{random.randint(100000000, 999999999)}"
            fullname = f"{random.choice(names)} {random.choice(surnames)}"
            await self.client.import_contacts([
                raw.types.InputPhoneContact(
                    client_id=random.randint(1, 999999),
                    phone=phone,
                    first_name=fullname,
                    last_name=""
                )
            ])
            self.log(f"Импортирован фейковый контакт: {fullname} ({phone})", "success")
            await self._human_delay(0.4)
        except Exception as ce:
            self.log(f"Не удалось импортировать контакт: {ce}", "warning")

    async def _task_update_notify(self):
        self.log("Настройка глобальных параметров уведомлений...", "info")
        await self._human_delay(0.5)
        try:
            mute_settings = raw.types.InputPeerNotifySettings(
                mute_until=random.choice([0, 3600, 2147483647]),
                silent=random.choice([True, False])
            )
            await self.client.invoke(
                raw.functions.account.UpdateNotifySettings(
                    peer=raw.types.InputNotifyUsers(),
                    settings=mute_settings
                )
            )
            self.log("Настройки уведомлений аккаунта обновлены.", "success")
            await self._human_delay(0.4)
        except Exception as ne:
            self.log(f"Не удалось настроить уведомления: {ne}", "warning")

    async def _task_emoji_status(self):
        self.log("Обновление эмодзи-статуса...", "info")
        await self._human_delay(0.5)
        try:
            status_emojis = [5397949312151756549, 5402377317762635607, 5402377317762635608]
            chosen_emoji = random.choice(status_emojis)
            await self.client.invoke(
                raw.functions.account.UpdateEmojiStatus(
                    emoji_status=raw.types.EmojiStatus(
                        document_id=chosen_emoji
                    )
                )
            )
            self.log("Эмодзи-статус успешно обновлен.", "success")
            await self._human_delay(0.4)
        except Exception:
            self.log("Эмодзи-статус не изменен (требуется Telegram Premium).", "warning")

    async def _task_update_bio(self):
        self.log("Имитация постепенного обновления данных профиля...", "info")
        await self._human_delay(0.8)
        try:
            bios = [
                "Интересуюсь технологиями и автоматизацией.",
                "ShadowGram user. Stay stealthy.",
                "Живу в сети. Пишите в ЛС.",
                "Изучаю искусственный интеллект и Python."
            ]
            await self.client.update_profile(bio=random.choice(bios))
            self.log("Профиль постепенно обновлен (изменено био).", "success")
            await self._human_delay(0.6)
        except Exception as gue:
            self.log(f"Не удалось обновить профиль: {gue}", "warning")

    async def _task_read_unread(self):
        self.log("Поиск непрочитанных диалогов для очистки...", "info")
        try:
            unread_cleaned = 0
            async for dialog in self.client.get_dialogs(limit=20):
                if dialog.unread_messages_count > 0:
                    await self.client.read_chat_history(dialog.chat.id)
                    unread_cleaned += 1
                    await self.sleep(random.uniform(1.5, 3.0))
                    if unread_cleaned >= 3:
                        break
            if unread_cleaned > 0:
                self.log(f"Прочитано диалогов с непрочитанными: {unread_cleaned}", "success")
            else:
                self.log("Непрочитанных диалогов не найдено.", "info")
        except Exception as re:
            self.log(f"Не удалось очистить непрочитанные: {re}", "warning")

    async def _task_global_search(self):
        queries = ["крипта", "программирование", "новости", "мемы", "работа", "telegram", "shadowgram"]
        query = random.choice(queries)
        self.log(f"Имитация поиска сообщения по запросу '{query}'...", "info")
        try:
            results_count = 0
            async for msg in self.client.search_global(query, limit=5):
                results_count += 1
                await self.sleep(random.uniform(1.5, 3.0))
            self.log(f"Поиск завершен. Просмотрено результатов: {results_count}", "success")
        except Exception as se:
            self.log(f"Ошибка при поиске сообщений: {se}", "warning")

    async def _task_schedule_msg(self):
        self.log("Планирование отложенного сообщения в Избранное...", "info")
        await self._human_delay(0.6)
        try:
            future_date = int(time.time() + 3600) # +1 час
            await self.client.send_message(
                "me", 
                "Напоминание: Проверить статус выполнения прогрева в ShadowGram", 
                schedule_date=future_date
            )
            self.log("Отложенное сообщение успешно запланировано на +1 час.", "success")
            await self._human_delay(0.4)
        except Exception as sche:
            self.log(f"Не удалось создать отложенное сообщение: {sche}", "warning")

    async def _task_bot_interact(self):
        bot_username = random.choice(self.WUP_BOTS)
        self.log(f"Прогрев через бота: {bot_username}", "info")
        await self._human_delay(0.5)
        try:
            await self.client.send_message(bot_username, "/start")
            await self._human_delay(0.6)
            
            if random.random() < 0.5:
                await self.client.send_message(bot_username, "/help")
                await self._human_delay(0.6)
                
            self.log(f"Отправлены команды боту {bot_username}", "success")
        except RPCError as e:
            if "USERNAME_INVALID" in str(e) or "USERNAME_NOT_OCCUPIED" in str(e):
                self.log(f"⚠️ Бот {bot_username} не найден или недоступен.", "warning")
            else:
                self.log(f"⚠️ Не удалось пообщаться с ботом {bot_username}: {e}", "warning")
        except Exception as e:
            self.log(f"⚠️ Не удалось пообщаться с ботом: {e}", "warning")

    async def _task_chat_interact(self, link: str, is_enabled, r_chance, w_chance, api_key, api_base_url, model_name):
        clean_link = self._clean_link(link)
        if not clean_link:
            return
        
        try:
            self.log(f"Захожу в: {link}", "info")
            chat = await self.client.join_chat(clean_link)
            await self._human_delay(0.8)
            
            # Отключение звука в чате
            if is_enabled("mute_chats"):
                try:
                    await self._human_delay(0.5)
                    target_peer = await self.client.resolve_peer(chat.id)
                    mute_settings = raw.types.InputPeerNotifySettings(
                        mute_until=2147483647,
                        silent=True
                    )
                    await self.client.invoke(
                        raw.functions.account.UpdateNotifySettings(
                            peer=raw.types.InputNotifyPeer(peer=target_peer),
                            settings=mute_settings
                        )
                    )
                    self.log(f"Уведомления отключены в чате {chat.title or chat.id}", "success")
                    await self._human_delay(0.5)
                except Exception as me:
                    self.log(f"Не удалось отключить уведомления в чате: {me}", "warning")

            # Архивирование чата
            if is_enabled("archive_chats"):
                try:
                    await self._human_delay(0.5)
                    await self.client.archive_chats(chat.id)
                    self.log(f"Чат {chat.title or chat.id} отправлен в архив", "success")
                    await self._human_delay(0.5)
                except Exception as ae:
                    self.log(f"Не удалось отправить чат в архив: {ae}", "warning")

            # Симуляция просмотра профилей участников
            if is_enabled("view_profiles") and random.random() < 0.4:
                self.log("Просмотр профилей некоторых участников чата...", "info")
                try:
                    async for member in self.client.get_chat_members(chat.id, limit=3):
                        if member.user:
                            await self.client.get_users(member.user.id)
                            await self._human_delay(0.8)
                except:
                    pass

            # Чтение постов / сообщений (прокрутка каналов)
            read_count = random.randint(3, 7) if is_enabled("scroll_channels") else 1
            context_msgs = []
            
            if is_enabled("scroll_channels") or is_enabled("read_dialogs"):
                self.log(f"Скроллинг истории и чтение сообщений ({read_count} шт.)...", "info")
                async for message in self.client.get_chat_history(chat.id, limit=read_count):
                    context_msgs.append(message)
                    
                    text_len = len(message.text or "") + len(message.caption or "")
                    read_time = min(max(2, text_len // 50), 10) 
                    
                    if is_enabled("scroll_channels"):
                        self.log(f"Просмотр сообщения #{message.id} ({read_time} сек.)...", "info")
                        await self.client.read_chat_history(chat.id, message.id)
                        await self.sleep(read_time + random.uniform(1.0, 3.0))

                    # Просмотр видео / видеосообщений
                    if is_enabled("watch_video") and (message.video or message.video_note):
                        try:
                            duration = (message.video.duration if message.video else message.video_note.duration) or 8
                            watch_time = min(duration, 15)
                            self.log(f"Имитация просмотра видео-файла ({watch_time} сек.)...", "info")
                            import tempfile
                            with tempfile.TemporaryDirectory() as tmpdir:
                                await self.client.download_media(message, file_name=os.path.join(tmpdir, "wup_video.mp4"))
                            await self.sleep(watch_time + random.uniform(1.0, 3.0))
                            self.log("Просмотр видео завершен.", "success")
                        except Exception as ve:
                            self.log(f"Не удалось воспроизвести видео: {ve}", "warning")

                    # Прослушивание голосовых
                    if is_enabled("listen_voice") and message.voice:
                        try:
                            duration = message.voice.duration or 5
                            listen_time = min(duration, 10)
                            self.log(f"Прослушивание голосового сообщения ({listen_time} сек.)...", "info")
                            await self.client.send_chat_action(chat.id, "play")
                            import tempfile
                            with tempfile.TemporaryDirectory() as tmpdir:
                                await self.client.download_media(message, file_name=os.path.join(tmpdir, "wup_voice.ogg"))
                            await self.sleep(listen_time + random.uniform(1.0, 3.0))
                            self.log("Голосовое сообщение успешно прослушано.", "success")
                        except Exception as voe:
                            self.log(f"Не удалось прослушать голосовое: {voe}", "warning")

                    # Просмотр набора стикеров
                    if is_enabled("view_stickers") and message.sticker and message.sticker.set_name:
                        self.log(f"Просмотр набора стикеров '{message.sticker.set_name}'...", "info")
                        try:
                            await self.client.invoke(
                                raw.functions.messages.GetStickerSet(
                                    stickerset=raw.types.InputStickerSetShortName(
                                        short_name=message.sticker.set_name
                                    ),
                                    hash=0
                                )
                            )
                            await self.sleep(random.uniform(3.0, 6.0))
                            self.log("Стикер-пак просмотрен.", "success")
                        except Exception as ste:
                            self.log(f"Не удалось открыть стикер-пак: {ste}", "warning")

                    # Предпросмотр внешней ссылки
                    if is_enabled("preview_links") and message.text:
                        links_found = re.findall(r'(https?://\S+)', message.text)
                        if links_found:
                            target_link = links_found[0]
                            self.log(f"Имитация предпросмотра внешней ссылки {target_link}...", "info")
                            try:
                                await self.client.invoke(
                                    raw.functions.messages.GetWebPagePreview(
                                        message=target_link
                                    )
                                )
                                await self.sleep(random.uniform(4.0, 7.0))
                                self.log("Ссылка открыта во встроенном браузере.", "success")
                            except Exception as pre:
                                self.log(f"Не удалось загрузить превью ссылки: {pre}", "warning")

                    # Голосование в опросах
                    if is_enabled("vote_polls") and message.poll and not message.poll.is_closed:
                        try:
                            chosen_option = [random.choice(range(len(message.poll.options)))]
                            await self.client.vote_poll(chat.id, message.id, chosen_option)
                            self.log(f"Участие в опросе: '{message.poll.question}'", "success")
                            await self.sleep(random.uniform(3.0, 6.0))
                        except Exception as pe:
                            self.log(f"Не удалось проголосовать: {pe}", "warning")

                    # Расстановка реакций
                    if random.random() < r_chance:
                        try:
                            reaction = random.choice(self.COMMON_REACTIONS)
                            await self.client.send_reaction(chat.id, message.id, reaction)
                            self.log(f"Поставил реакцию {reaction} на сообщение {message.id}", "success")
                            await self.sleep(random.uniform(2.0, 4.0))
                        except: pass 

                    # Пересылка сообщений в избранное (Saved Messages)
                    if (is_enabled("forward_messages") or is_enabled("notes_saved")) and random.random() < 0.08:
                        try:
                            await message.forward("me")
                            self.log("Пост переслан и сохранен в Избранное", "success")
                            await self.sleep(random.uniform(2.5, 5.0))
                        except: pass

            # Пишем сообщение в чат с шансом w_chance
            if w_chance > 0 and api_key and random.random() < w_chance:
                try:
                    self.log(f"Генерирую AI-сообщение для чата...", "info")
                    context_msgs.reverse()
                    sys_prompt = self.acc.get("ai_prompt") or "Ты обычный пользователь Telegram. Участвуешь в беседе. Твой стиль общения повседневный и расслабленный."
                    
                    reply_text = await self._generate_message(context_msgs, sys_prompt, api_key, api_base_url, model_name)
                    if reply_text:
                        # Симуляция печати
                        if is_enabled("simulate_typing"):
                            self.log("Имитация набора сообщения (печатает...)...", "info")
                            await self.client.send_chat_action(chat.id, "typing")
                            typing_time = min(len(reply_text) / 10, 8.0)
                            await self.sleep(max(2.0, typing_time) + random.uniform(1.0, 3.0))
                        
                        await self.client.send_message(chat.id, reply_text)
                        self.log(f"💬 Отправлено в чат: '{reply_text}'", "success")
                        await self.sleep(random.uniform(4.0, 9.0))
                except RPCError as e:
                    self.log(f"Не удалось написать в чат: {e}", "warning")
                except Exception as e:
                    self.log(f"Ошибка отправки сообщения: {e}", "error")

            # Создание черновика сообщения
            if is_enabled("drafts") and random.random() < 0.35:
                self.log("Сохранение черновика сообщения в диалоге...", "info")
                try:
                    draft_texts = ["Интересный канал, подписываюсь!", "Позже отвечу", "Ок, договорились!", "Привет, как дела?"]
                    await self.client.save_draft(chat.id, random.choice(draft_texts))
                    self.log("Черновик успешно сохранен в чате.", "success")
                    await self.sleep(random.uniform(2.0, 4.0))
                except Exception as de:
                    self.log(f"Не удалось сохранить черновик: {de}", "warning")

        except FloodWait as e:
            self.log(f"⚠️ Слишком много запросов (FloodWait). Жду {e.value} сек...", "warning")
            await self.sleep(e.value)
        except RPCError as e:
            if "USER_ALREADY_PARTICIPANT" in str(e):
                self.log(f"ℹ️ Аккаунт уже состоит в этом чате: {link}", "info")
            elif "INVITE_HASH_EXPIRED" in str(e) or "INVITE_HASH_INVALID" in str(e):
                self.log(f"❌ Приватная ссылка недействительна или истекла: {link}", "error")
            elif "USERNAME_INVALID" in str(e) or "USERNAME_NOT_OCCUPIED" in str(e):
                self.log(f"❌ Неверный юзернейм или канал не существует: {link}", "error")
            elif "INVITE_REQUEST_SENT" in str(e):
                self.log(f"✅ Заявка на вступление успешно отправлена (ожидает одобрения): {link}", "success")
            else:
                self.log(f"⚠️ Ошибка Telegram API при вступлении в {link}: {e}", "warning")
        except Exception as e:
            self.log(f"❌ Ошибка при обработке {link}: {e}", "error")

    def _is_our_account(self, user) -> bool:
        if not user:
            return False
            
        if hasattr(self, "worker") and self.worker:
            for inst in getattr(self, "worker", None).instances:
                if inst.client and inst.client.is_connected and inst.client.me:
                    if inst.client.me.id == user.id:
                        return True
                        
        if user.username:
            for acc in getattr(self, "selected_accounts", []):
                if acc.get("username") and acc.get("username").strip().lower().replace("@", "") == user.username.lower():
                    return True
                    
        if user.first_name:
            for acc in getattr(self, "selected_accounts", []):
                name = acc.get("name", "").lower()
                first = user.first_name.lower()
                last = (user.last_name or "").lower()
                if first in name or name in first or (last and (last in name or name in last)):
                    return True
                    
        return False

    async def _task_neuro_dialogue(self, mode, target_chat, prompt_context, min_msgs, max_msgs, api_key, api_url, model_name):
        self.log(f"Запуск модуля Нейро-Диалогов (Режим: {mode})...", "info")
        if mode == "Группа / Чат":
            await self._task_neuro_dialogue_group(target_chat, prompt_context, min_msgs, max_msgs, api_key, api_url, model_name)
        else:
            await self._task_neuro_dialogue_pm(prompt_context, min_msgs, max_msgs, api_key, api_url, model_name)

    async def _task_neuro_dialogue_group(self, target_chat, prompt_context, min_msgs, max_msgs, api_key, api_url, model_name):
        clean_chat = self._clean_link(target_chat)
        if not clean_chat:
            self.log("Нейро-Диалоги: Неверная ссылка на чат.", "warning")
            return

        try:
            self.log(f"Нейро-Диалоги: Вход в чат {target_chat}...", "info")
            chat = await self.client.join_chat(clean_chat)
            await self._human_delay(0.5)

            self.log("Нейро-Диалоги: Чтение истории сообщений...", "info")
            messages = []
            async for msg in self.client.get_chat_history(chat.id, limit=15):
                messages.append(msg)
            messages.reverse()

            dialogue_chain = []
            for msg in reversed(messages):
                if msg.from_user and self._is_our_account(msg.from_user):
                    dialogue_chain.append(msg)
                else:
                    break
            dialogue_chain.reverse()
            
            if len(dialogue_chain) >= max_msgs:
                self.log(f"Нейро-Диалоги: Достигнут лимит диалога ({len(dialogue_chain)} сообщений). Пропускаем ход.", "info")
                return

            should_reply = False
            last_msg = messages[-1] if messages else None
            
            if last_msg and last_msg.from_user:
                is_ours = self._is_our_account(last_msg.from_user)
                is_me = (last_msg.from_user.id == self.client.me.id) if (self.client and self.client.me) else False
                if is_ours and not is_me:
                    should_reply = True
                    self.log(f"Нейро-Диалоги: Обнаружено последнее сообщение от нашего аккаунта {last_msg.from_user.first_name}. Будем отвечать.", "success")
            
            if not should_reply:
                if random.random() < 0.25:
                    self.log("Нейро-Диалоги: В чате нет активной нашей беседы. Начинаем новую тему...", "info")
                    reply_text = await self._generate_dialogue_starter(prompt_context, api_key, api_url, model_name)
                    if reply_text:
                        self.log("Нейро-Диалоги: Печатаю стартовое сообщение...", "info")
                        await self.client.send_chat_action(chat.id, "typing")
                        await self.sleep(random.uniform(3.0, 6.0))
                        await self.client.send_message(chat.id, reply_text)
                        self.log(f"💬 Отправлен старт диалога: '{reply_text}'", "success")
                else:
                    self.log("Нейро-Диалоги: Новая беседа не начата (шанс 25% не выпал).", "info")
                return

            reply_text = await self._generate_dialogue_reply(messages, prompt_context, api_key, api_url, model_name)
            if reply_text:
                self.log("Нейро-Диалоги: Имитация набора ответа...", "info")
                await self.client.send_chat_action(chat.id, "typing")
                await self.sleep(random.uniform(4.0, 8.0))
                await self.client.send_message(chat.id, reply_text)
                self.log(f"💬 Отправлена реплика в диалог: '{reply_text}'", "success")

        except Exception as e:
            self.log(f"Ошибка в модуле Нейро-Диалогов (Группа): {e}", "error")

    async def _task_neuro_dialogue_pm(self, prompt_context, min_msgs, max_msgs, api_key, api_url, model_name):
        if not getattr(self, "selected_accounts", None) or len(self.selected_accounts) < 2:
            self.log("Нейро-Диалоги (ЛС): Для личных сообщений необходимо выбрать как минимум 2 аккаунта!", "warning")
            return
            
        other_accounts = []
        for acc in self.selected_accounts:
            if acc.get("name") != self.acc.get("name"):
                other_accounts.append(acc)
                
        if not other_accounts:
            return
            
        partner_acc = random.choice(other_accounts)
        partner_name = partner_acc.get("name")
        
        partner_peer = None
        if hasattr(self, "worker") and self.worker:
            for inst in self.worker.instances:
                if inst.acc.get("name") == partner_name and inst.client and inst.client.is_connected and inst.client.me:
                    partner_peer = inst.client.me.username or inst.client.me.id
                    break
                    
        if not partner_peer:
            partner_peer = partner_acc.get("username")
            
        if not partner_peer:
            self.log(f"Нейро-Диалоги (ЛС): Не удалось определить юзернейм/ID для собеседника {partner_name}.", "warning")
            return

        try:
            self.log(f"Нейро-Диалоги (ЛС): Проверка истории сообщений с {partner_name}...", "info")
            messages = []
            async for msg in self.client.get_chat_history(partner_peer, limit=15):
                messages.append(msg)
            messages.reverse()
            
            dialogue_chain = []
            for msg in reversed(messages):
                if msg.from_user and self._is_our_account(msg.from_user):
                    dialogue_chain.append(msg)
                else:
                    break
            dialogue_chain.reverse()
            
            if len(dialogue_chain) >= max_msgs:
                self.log(f"Нейро-Диалоги (ЛС): Достигнут лимит ЛС диалога ({len(dialogue_chain)} сообщений). Пропускаем.", "info")
                return

            should_reply = False
            last_msg = messages[-1] if messages else None
            
            if last_msg:
                if last_msg.from_user and last_msg.from_user.id != self.client.me.id:
                    should_reply = True
                    self.log(f"Нейро-Диалоги (ЛС): Новое сообщение от {partner_name}: '{last_msg.text}'", "info")
            
            if not should_reply:
                if random.random() < 0.25:
                    self.log(f"Нейро-Диалоги (ЛС): Начинаем новый диалог с {partner_name}...", "info")
                    reply_text = await self._generate_dialogue_starter(prompt_context, api_key, api_url, model_name)
                    if reply_text:
                        await self.client.send_chat_action(partner_peer, "typing")
                        await self.sleep(random.uniform(3.0, 5.0))
                        await self.client.send_message(partner_peer, reply_text)
                        self.log(f"💬 Отправлено ЛС к {partner_name}: '{reply_text}'", "success")
                return

            reply_text = await self._generate_dialogue_reply(messages, prompt_context, api_key, api_url, model_name)
            if reply_text:
                await self.client.send_chat_action(partner_peer, "typing")
                await self.sleep(random.uniform(4.0, 7.0))
                await self.client.send_message(partner_peer, reply_text)
                self.log(f"💬 Отправлен ответ ЛС для {partner_name}: '{reply_text}'", "success")

        except Exception as e:
            self.log(f"Ошибка в модуле Нейро-Диалогов (ЛС): {e}", "error")

    async def _generate_dialogue_starter(self, prompt_context: str, api_key: str, api_url: str, model_name: str) -> str:
        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        system_prompt = (
            "Ты обычный пользователь Telegram. Твоя задача — начать непринужденный разговор с собеседником.\n"
            f"Тематика разговора: {prompt_context}\n"
            "Пиши коротко (1-2 предложения), простым языком, как живой человек. Без вежливости, без хештегов, без длинных вступлений."
        )
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Напиши интересную стартовую фразу или вопрос, чтобы завязать беседу."}
            ],
            "max_tokens": 80,
            "temperature": 0.9
        }
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(f"{api_url}/chat/completions", headers=headers, json=payload, timeout=12)
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip(' "\'')
        except Exception as e:
            self.log(f"Ошибка генерации старта диалога: {e}", "error")
        return ""

    async def _generate_dialogue_reply(self, history: list, prompt_context: str, api_key: str, api_url: str, model_name: str) -> str:
        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        context_lines = []
        for m in history:
            if m.text:
                sender_name = m.from_user.first_name if m.from_user else "Собеседник"
                context_lines.append(f"{sender_name}: {m.text}")
        context_str = "\n".join(context_lines[-8:])
        system_prompt = (
            "Ты обычный участник чата Telegram. Твоя задача — продолжить текущую переписку.\n"
            f"Тематика и контекст общения: {prompt_context}\n"
            "Пиши естественно, коротко (1-2 предложения), как живой человек в мессенджере. "
            "Ты можешь не соглашаться, шутить, высказывать свое мнение или задавать встречные вопросы. "
            "Не используй смайлики в каждом предложении, пиши без хэштегов."
        )
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Вот контекст диалога:\n{context_str}\n\nНапиши короткий и органичный ответ от своего лица."}
            ],
            "max_tokens": 100,
            "temperature": 0.8
        }
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(f"{api_url}/chat/completions", headers=headers, json=payload, timeout=12)
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip(' "\'')
        except Exception as e:
            self.log(f"Ошибка генерации ответа в диалог: {e}", "error")
        return ""

    async def run(self, **kwargs):
        # Чтение сохраненных индивидуальных настроек прогрева для этого аккаунта
        warmup_settings = self.acc.get("warmup_settings", {})
        
        # Вспомогательная функция для получения настроек с дефолтом True
        def is_enabled(key):
            return warmup_settings.get(key, True)

        links_raw = self.acc.get("warmup_chat_links", "") or kwargs.get("chat_links", "")
        links = [l.strip() for l in links_raw.split("\n") if l.strip()]
        
        use_bots = kwargs.get("use_bots", False) or is_enabled("inline_bots")
        
        try:
            r_chance = float(kwargs.get("reactions_chance", 15)) / 100
        except: r_chance = 0.15
        
        try:
            w_chance = float(kwargs.get("write_chance", 0)) / 100
        except: w_chance = 0.0

        try:
            self.d_min = int(kwargs.get("min_delay", 5))
            self.d_max = int(kwargs.get("max_delay", 15))
        except:
            self.d_min, self.d_max = 5, 15

        try:
            duration_mins = float(kwargs.get("warmup_duration", 30))
        except:
            duration_mins = 30.0

        api_key = kwargs.get("api_key", "").strip()
        api_base_url = kwargs.get("api_base_url", "").strip().rstrip("/")
        model_name = kwargs.get("model_name", "").strip()

        if not await self.init_client():
            return

        try:
            # Собираем список доступных типов задач
            task_pool = []
            if is_enabled("check_settings"): task_pool.append("check_privacy")
            if is_enabled("sync_contacts"): task_pool.append("sync_contacts")
            if is_enabled("configure_notifications"): task_pool.append("update_notify")
            if is_enabled("emoji_status"): task_pool.append("emoji_status")
            if is_enabled("gradual_update"): task_pool.append("update_bio")
            if is_enabled("mark_as_read"): task_pool.append("read_unread")
            if is_enabled("search_messages"): task_pool.append("global_search")
            if is_enabled("scheduled_messages"): task_pool.append("schedule_msg")
            if use_bots and is_enabled("inline_bots"): task_pool.append("bot_interact")
            if links: task_pool.append("chat_interact")
            if kwargs.get("enable_neuro_dialogues", False):
                task_pool.append("neuro_dialogues")

            if not task_pool:
                self.log("Нет активных настроек задач для прогрева аккаунта. Завершаю.", "warning")
                return

            end_time = time.time() + duration_mins * 60
            self.log(f"Запуск циклического прогрева. Длительность: {duration_mins:.1f} мин. Будет работать до {time.strftime('%H:%M:%S', time.localtime(end_time))}", "info")
            
            chat_links_pool = list(links)
            
            while time.time() < end_time:
                if getattr(self, "is_stopped", False):
                    raise asyncio.CancelledError("Модуль остановлен пользователем")
                # Выбор случайного типа задачи
                current_task = random.choice(task_pool)
                
                if current_task == "check_privacy":
                    await self._task_check_privacy()
                elif current_task == "sync_contacts":
                    if random.random() < 0.4:
                        await self._task_sync_contacts()
                elif current_task == "update_notify":
                    if random.random() < 0.3:
                        await self._task_update_notify()
                elif current_task == "emoji_status":
                    if random.random() < 0.25:
                        await self._task_emoji_status()
                elif current_task == "update_bio":
                    if random.random() < 0.15:
                        await self._task_update_bio()
                elif current_task == "read_unread":
                    await self._task_read_unread()
                elif current_task == "global_search":
                    if random.random() < 0.4:
                        await self._task_global_search()
                elif current_task == "schedule_msg":
                    if random.random() < 0.4:
                        await self._task_schedule_msg()
                elif current_task == "bot_interact":
                    await self._task_bot_interact()
                elif current_task == "chat_interact":
                    if chat_links_pool:
                        link = random.choice(chat_links_pool)
                        chat_links_pool.remove(link)
                        await self._task_chat_interact(
                            link=link,
                            is_enabled=is_enabled,
                            r_chance=r_chance,
                            w_chance=w_chance,
                            api_key=api_key,
                            api_base_url=api_base_url,
                            model_name=model_name
                        )
                    else:
                        # Сброс пула чатов при прохождении всех
                        chat_links_pool = list(links)
                        continue
                elif current_task == "neuro_dialogues":
                    await self._task_neuro_dialogue(
                        mode=kwargs.get("neuro_dialogue_mode", "Группа / Чат"),
                        target_chat=kwargs.get("neuro_dialogue_chat", ""),
                        prompt_context=kwargs.get("neuro_dialogue_prompt", ""),
                        min_msgs=int(kwargs.get("neuro_dialogue_min_msgs", "3")),
                        max_msgs=int(kwargs.get("neuro_dialogue_max_msgs", "7")),
                        api_key=api_key,
                        api_url=api_base_url,
                        model_name=model_name
                    )

                # Равномерная случайная задержка между крупными задачами
                time_left = end_time - time.time()
                if time_left <= 0:
                    break
                    
                delay = random.uniform(self.d_min, self.d_max)
                delay = min(delay, time_left)
                
                self.log(f"⏳ Ожидание {delay:.1f} сек. перед следующей задачей... (Осталось {time_left/60:.1f} мин. прогрева)", "info")
                await self.sleep(delay)

            self.log("Сессия умного прогрева успешно завершена!", "success")
            
        finally:
            await self.cleanup()

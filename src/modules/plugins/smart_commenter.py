import asyncio
import random
import os
import time
import json
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional
from src.core.base_module import BaseModule
from hydrogram.errors import FloodWait, RPCError

class SmartCommenterPlugin(BaseModule):
    MODULE_NAME = "💬 Нейрокомментинг (Стероиды)"
    MODULE_DESC = "Автоматическое комментирование постов в Telegram-каналах в реальном времени с ИИ и защитой от обнаружения."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_file: Optional[Path] = None
        if self.workdir:
            self.state_file = Path(self.workdir) / "commenter_state.json"
        self.last_post_ids: Dict[str, int] = {}
        self.load_state()

    def load_state(self) -> None:
        """Загрузка состояния последних обработанных постов из файла"""
        if self.state_file and self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_post_ids = data.get("last_post_ids", {})
            except Exception as e:
                self.log(f"Предупреждение: Не удалось загрузить commenter_state.json: {e}", "warning")

    def save_state(self) -> None:
        """Сохранение состояния последних обработанных постов на диск"""
        if self.state_file:
            try:
                state_data = {"last_post_ids": self.last_post_ids}
                # Атомарная запись для предотвращения повреждения файла
                import tempfile
                dir_path = self.state_file.parent
                with tempfile.NamedTemporaryFile("w", dir=dir_path, delete=False, encoding="utf-8") as tf:
                    json.dump(state_data, tf, indent=4, ensure_ascii=False)
                    temp_name = tf.name
                os.replace(temp_name, self.state_file)
            except Exception as e:
                self.log(f"Предупреждение: Не удалось сохранить commenter_state.json: {e}", "warning")

    async def _generate_comment(self, post_text: str, system_prompt: str, api_key: str, api_url: str, model_name: str, auto_language: bool = False) -> str:
        """Обращение к OpenAI-совместимому API для генерации текста комментария с повторными попытками при 429/503"""
        import requests
        
        short_post = post_text[:1000] if post_text else "[Изображение/Медиафайл без текста]"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Добавляем в промпт жесткие системные инструкции против типичного бот-поведения
        bot_prevention_instructions = (
            "\n\nКРИТИЧЕСКИЕ ПРАВИЛА КОММЕНТАРИЯ:\n"
            "1. Пиши как реальный человек в соцсетях: просто, живо, без пафоса.\n"
            "2. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать шаблонные бот-фразы вроде 'Отличный пост!', 'Спасибо за информацию!', 'Полезно!', 'Согласен', 'Круто!'.\n"
            "3. Пиши со строчной (маленькой) буквы, можно не ставить точку в конце предложения.\n"
            "4. Вырази конкретную мысль или легкую иронию/вопрос по сути поста, чтобы это выглядело естественно.\n"
            "5. НЕ используй смайлики (emoji) и хэштеги вообще.\n"
            "6. Длина ответа строго от 3 до 10 слов."
        )
        
        user_content = f"Напиши один короткий комментарий на этот пост:\n\n{short_post}"
        if auto_language:
            user_content += "\n\nВАЖНО: Пиши комментарий СТРОГО на том же языке, на котором написан пост (например, если пост на английском - отвечай на английском, если на русском - на русском)."
            
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt + bot_prevention_instructions},
                {"role": "user", "content": user_content}
            ],
            "max_tokens": 80,
            "temperature": 0.8
        }
        
        for attempt in range(3):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: requests.post(f"{api_url}/chat/completions", headers=headers, json=payload, timeout=20)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    comment = data['choices'][0]['message']['content'].strip()
                    # Убираем кавычки, если модель их вернула
                    return comment.strip('"\'')
                elif response.status_code in [429, 503]:
                    wait_time = 5 * (attempt + 1)
                    self.log(f"⚠️ Превышен лимит запросов AI (код {response.status_code}). Повтор через {wait_time} сек... (Попытка {attempt+1}/3)", "warning")
                    await self.sleep(wait_time)
                else:
                    self.log(f"Ошибка API (код {response.status_code}): {response.text}", "error")
                    return ""
            except Exception as e:
                self.log(f"Сбой сети при запросе к AI: {e}", "error")
                await self.sleep(2)
        return ""

    async def _generate_filter_decision(self, post_text: str, filter_prompt: str, api_key: str, api_url: str, model_name: str) -> str:
        """Анализ поста ИИ для принятия решения о комментировании (отсекание рекламы, спама, оффтопа)"""
        import requests
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": filter_prompt}
            ],
            "max_tokens": 10,
            "temperature": 0.0
        }
        
        for attempt in range(3):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: requests.post(f"{api_url}/chat/completions", headers=headers, json=payload, timeout=15)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    decision = data['choices'][0]['message']['content'].strip().upper()
                    return "PASS" if "PASS" in decision else "REJECT"
                elif response.status_code in [429, 503]:
                    wait_time = 3 * (attempt + 1)
                    self.log(f"⚠️ Превышен лимит запросов AI при анализе поста (код {response.status_code}). Повтор через {wait_time} сек...", "warning")
                    await self.sleep(wait_time)
                else:
                    self.log(f"Ошибка API при фильтрации (код {response.status_code}): {response.text}", "warning")
                    return "PASS"
            except Exception as e:
                self.log(f"Сбой сети при ИИ-фильтрации поста: {e}", "warning")
                await self.sleep(1)
        return "PASS"

    async def _safe_join_chat(self, channel_input: str) -> Optional[Any]:
        """Безопасная подписка на канал или получение информации без повторных спам-запросов join_chat"""
        cleaned = channel_input.replace("https://t.me/", "").replace("@", "").strip()
        chat = None
        
        # Сначала пробуем просто получить чат (если уже подписаны)
        try:
            chat = await self.client.get_chat(cleaned)
            return chat
        except Exception:
            pass

        # Если не подписаны, пробуем подписаться
        try:
            self.log(f"Вступаю в канал {channel_input}...", "info")
            chat = await self.client.join_chat(channel_input)
            self.log(f"Успешно вступили в канал: {chat.title or channel_input}", "success")
            await self.sleep(random.uniform(3.0, 7.0)) # Пауза после вступления
            return chat
        except Exception as e:
            self.log(f"Не удалось вступить в канал {channel_input}: {e}", "error")
            return None

    async def run(self, **kwargs: Any) -> Any:
        # 1. Загрузим настройки аккаунта
        settings = self.acc.get("commenting_settings", {})
        pending_followups = []
        
        # Загрузим дефолтные глобальные настройки AI
        from src.core.constants import CONFIG_FILE
        from src.core.managers.config_manager import _read_config
        
        global_defaults = {}
        try:
            global_defaults = _read_config(CONFIG_FILE).get("settings", {})
        except Exception:
            pass

        api_key = settings.get("api_key", "").strip() or global_defaults.get("default_ai_api_key", "").strip()
        api_base_url = settings.get("api_base_url", "").strip().rstrip("/") or global_defaults.get("default_ai_base_url", "").strip().rstrip("/")
        model_name = settings.get("model_name", "").strip() or global_defaults.get("default_ai_model_name", "").strip()
        system_prompt = settings.get("prompt", "").strip()
        ai_style = settings.get("ai_style", "Обычный пользователь (Естественный)")
        
        # Стили написания
        if ai_style == "Крипто-эксперт (Сленг)":
            system_prompt = (
                "Ты — опытный админ крипто-канала, общающийся со своей аудиторией на равных. "
                "Пиши короткие, живые комменты (от 3 до 10 слов), используя крипто-сленг (гем, ворк, лайфчейндж, скипаем, заносим, смарт-мув, бритва). "
                "Будь уверенным, дерзким, но дружелюбным. Без приветствий, без хэштегов."
            )
        elif ai_style == "Интеллектуал (Умный)":
            system_prompt = (
                "Ты — эксперт с высоким уровнем IQ. Оставляй короткие (до 10 слов), содержательные, хорошо структурированные и "
                "умные комментарии к посту. Используй точные формулировки. Без приветствий, без смайликов."
            )
        elif ai_style == "Юморист (Сарказм/Ирония)":
            system_prompt = (
                "Оставляй короткие, ироничные или саркастические комментарии к постам. Пошути или мягко подстебни тему поста. "
                "Пиши как обычный пользователь соцсетей, очень живо и весело. Не пиши банальностей."
            )
        elif ai_style == "Краткий критик (Хейтер)":
            system_prompt = (
                "Оставляй короткие (2-6 слов), скептические или критические комментарии. Сомневайся в полезности поста, "
                "но делай это смешно и естественно. Будь краток."
            )
        elif ai_style == "Обычный пользователь (Естественный)" or not system_prompt:
            system_prompt = "Напиши короткий, естественный комментарий к посту. Пиши как обычный пользователь соцсетей, просто и живо. Без смайликов, без хештегов."
            
        channels_raw = settings.get("channels", "").strip()
        
        # Режимы комментирования
        ai_protection = settings.get("ai_protection", False)
        protection_preset = settings.get("protection_preset", "balanced")
        mode = settings.get("mode", "Случайный")
        chance = int(settings.get("chance", 50))
        limit_mode = settings.get("limit_mode", "По количеству")
        max_comments = int(settings.get("max_comments", 500))
        keywords_str = settings.get("keywords", "").strip()
        auto_language = settings.get("auto_language", False)
        
        followup_enabled = settings.get("followup_enabled", False)
        followup_hours = int(settings.get("followup_hours", 3))
        followup_chance = int(settings.get("followup_chance", 30))
        
        rotate_prompts = settings.get("rotate_prompts", False)
        prompt_pool = []
        if rotate_prompts:
            SYSTEM_PROMPTS = [
                "Напиши короткий, позитивный и дружелюбный комментарий к публикации. Поддержи автора, вырази одобрение или согласие в простой разговорной манере без использования хэштегов.",
                "Напиши кокетливый, интригующий и слегка загадочный комментарий к посту. Пиши легко, непринужденно, проявляя дружеский или романтический интерес, но оставаясь в рамках приличия.",
                "Напиши эмоциональный и живой комментарий. Вырази яркие эмоции (восторг, удивление или искреннее сочувствие в зависимости от темы поста), пиши естественно.",
                "Напиши вовлекающий комментарий в виде вопроса автору. Задай один интересный или уточняющий вопрос по теме поста, чтобы завязать беседу.",
                "Напиши очень краткий, емкий отзыв на пост. Буквально 3-5 слов, выражающих суть твоего мнения в разговорном стиле.",
                "Напиши вдумчивый, конструктивный и серьезный комментарий к посту. Поделись кратким аргументом или аналитическим выводом по теме."
            ]
            custom_prompts_raw = global_defaults.get("commenting_custom_prompts", [])
            custom_prompts = [cp["text"] for cp in custom_prompts_raw if isinstance(cp, dict) and "text" in cp]
            
            prompt_pool = list(SYSTEM_PROMPTS)
            for cp in custom_prompts:
                if cp not in prompt_pool:
                    prompt_pool.append(cp)
            if system_prompt and system_prompt not in prompt_pool:
                prompt_pool.append(system_prompt)
        
        if not api_key:
            self.log("Ошибка: API ключ не указан в настройках аккаунта!", "error")
            return
        if not api_base_url:
            self.log("Ошибка: Base URL API не указан в настройках аккаунта!", "error")
            return
        if not model_name:
            self.log("Ошибка: Имя модели не указано в настройках аккаунта!", "error")
            return
        if not channels_raw:
            self.log("Ошибка: Список целевых каналов пуст!", "error")
            return
            
        # Разбор каналов
        raw_channel_inputs = [c.strip() for c in channels_raw.split("\n") if c.strip()]
        if not raw_channel_inputs:
            self.log("Ошибка: Не найдено валидных ссылок на каналы!", "error")
            return

        active_channels_list = list(raw_channel_inputs)
        keywords = [k.strip().lower() for k in keywords_str.split(",") if k.strip()]

        # Инициализация клиента Telegram
        if not await self.init_client():
            self.log("Не удалось подключить аккаунт Telegram!", "error")
            return

        self.log(f"Успешный вход! Начинаю мониторинг {len(active_channels_list)} каналов в реальном времени (режим: '{mode}').", "success")
        
        # Лимиты
        comments_sent = 0
        start_time = time.time()

        # Инициализируем последние ID постов для новых каналов, чтобы не комментировать старую историю при первом запуске
        channels_map: Dict[str, Any] = {}
        for channel_input in active_channels_list:
            if getattr(self, "is_stopped", False):
                break
            chat = await self._safe_join_chat(channel_input)
            if chat:
                channels_map[channel_input] = chat
                # Если для этого канала нет сохраненного состояния, инициализируем его последним постом
                if str(chat.id) not in self.last_post_ids and chat.username not in self.last_post_ids:
                    try:
                        async for last_msg in self.client.get_chat_history(chat.id, limit=1):
                            key = chat.username if chat.username else str(chat.id)
                            self.last_post_ids[key] = last_msg.id
                            self.log(f"Канал {chat.title}: инициализирован последним постом ID {last_msg.id}", "info")
                    except Exception as e:
                        self.log(f"Не удалось получить историю {chat.title}: {e}", "warning")
        
        self.save_state()

        # Запуск фонового цикла мониторинга
        while not getattr(self, "is_stopped", False):
            # Проверка глобальных лимитов
            if limit_mode == "По количеству" and comments_sent >= max_comments:
                self.log(f"Достигнут лимит комментариев: {comments_sent}/{max_comments}. Завершение работы.", "success")
                break
            if limit_mode == "По времени":
                elapsed_minutes = (time.time() - start_time) / 60.0
                if elapsed_minutes >= max_comments:
                    self.log(f"Достигнут лимит времени: {elapsed_minutes:.1f}/{max_comments} мин. Завершение работы.", "success")
                    break

            for channel_input, chat in list(channels_map.items()):
                if getattr(self, "is_stopped", False):
                    break
                
                channel_name = chat.title or channel_input
                key = chat.username if chat.username else str(chat.id)
                last_processed_id = self.last_post_ids.get(key, 0)

                try:
                    # Читаем последние 3 поста для поиска новых
                    messages = []
                    async for msg in self.client.get_chat_history(chat.id, limit=3):
                        messages.append(msg)
                    
                    if not messages:
                        continue
                    
                    # Проверяем, появились ли новые посты
                    new_posts = [m for m in messages if m.id > last_processed_id]
                    if not new_posts:
                        continue

                    # Сортируем от старых к новым
                    new_posts.sort(key=lambda x: x.id)

                    for msg in new_posts:
                        if getattr(self, "is_stopped", False):
                            break
                        if getattr(msg, "service", False) or getattr(msg, "empty", False):
                            self.last_post_ids[key] = msg.id
                            self.save_state()
                            continue

                        text_content = (msg.text or msg.caption or "").strip()
                        self.log(f"🔔 Обнаружен новый пост в {channel_name} (ID: {msg.id})", "info")

                        # Проверка режима
                        should_comment = False
                        if mode == "Все посты":
                            should_comment = True
                        elif mode == "Случайный":
                            should_comment = (random.randint(1, 100) <= chance)
                        elif mode == "По ключевым словам":
                            if keywords:
                                should_comment = any(k in text_content.lower() for k in keywords)
                            else:
                                should_comment = True
                        elif mode == "ИИ-Фильтр постов":
                            if not text_content:
                                should_comment = False
                            else:
                                self.log(f"Запуск ИИ-фильтрации поста ID {msg.id}...", "info")
                                filter_prompt = (
                                    "Ты — экспертный фильтр спама и рекламы для Telegram. Твоя задача — проанализировать пост и решить, "
                                    "стоит ли оставлять под ним комментарий.\n"
                                    "Правила:\n"
                                    "1. Если пост является откровенной рекламой стороннего канала/продукта, спамом, розыгрышем (гивэвеем) без пользы, или "
                                    "содержит только реферальные ссылки без полезной информации — ответь REJECT.\n"
                                    "2. Если пост содержит полезную новость, интересную информацию, аналитику или полезную инструкцию — ответь PASS.\n"
                                    "Ответь строго одним словом: PASS или REJECT.\n\n"
                                    f"Текст поста:\n{text_content}"
                                )
                                decision = await self._generate_filter_decision(text_content, filter_prompt, api_key, api_base_url, model_name)
                                should_comment = (decision == "PASS")
                                
                        if not should_comment:
                            self.log(f"Пост ID {msg.id} пропущен по условиям режима '{mode}'.", "info")
                            self.last_post_ids[key] = msg.id
                            self.save_state()
                            continue

                        # Получение связанного чата обсуждений
                        try:
                            # Получаем свежийlinked_chat_id
                            full_chat = await self.client.get_chat(chat.id)
                            discussion_chat_id = getattr(full_chat, "linked_chat_id", None)
                            if not discussion_chat_id and getattr(full_chat, "linked_chat", None):
                                discussion_chat_id = full_chat.linked_chat.id

                            if not discussion_chat_id:
                                self.log(f"У канала {channel_name} отсутствует привязанный чат комментариев. Пропускаю.", "warning")
                                self.last_post_ids[key] = msg.id
                                self.save_state()
                                continue

                            discussion_msg = await self.client.get_discussion_message(chat.id, msg.id)
                        except Exception as de:
                            self.log(f"Комментарии закрыты или недоступны для поста ID {msg.id}: {de}", "info")
                            self.last_post_ids[key] = msg.id
                            self.save_state()
                            continue

                        # Эмуляция человека (Чтение поста на основе длины текста)
                        if ai_protection:
                            chars_count = len(text_content) if text_content else 50
                            # Примерно 15 символов в секунду + случайный шум
                            reading_delay = (chars_count / 15.0) * random.uniform(0.8, 1.3)
                            
                            if protection_preset == "conservative":
                                reading_delay *= 1.5
                            elif protection_preset == "aggressive":
                                reading_delay *= 0.5
                                
                            reading_delay = max(4.0, min(reading_delay, 45.0)) # Ограничение задержки в разумных пределах
                            self.log(f"Имитация чтения поста: жду {reading_delay:.1f} сек...", "info")
                            await self.sleep(reading_delay)

                        # Генерация AI-комментария
                        active_prompt = system_prompt
                        if rotate_prompts and prompt_pool:
                            if len(prompt_pool) > 1:
                                candidates = [p for p in prompt_pool if p != getattr(self, "_last_rotated_prompt", None)]
                                active_prompt = random.choice(candidates) if candidates else random.choice(prompt_pool)
                            else:
                                active_prompt = prompt_pool[0]
                            self._last_rotated_prompt = active_prompt
                            self.log("🔄 Ротация промптов: выбран новый промпт из склада", "info")

                        self.log(f"Генерация ИИ-комментария...", "info")
                        comment_text = await self._generate_comment(text_content, active_prompt, api_key, api_base_url, model_name, auto_language)
                        
                        if not comment_text:
                            self.log("Не удалось получить текст комментария от AI.", "warning")
                            self.last_post_ids[key] = msg.id
                            self.save_state()
                            continue

                        # Имитация человеческого набора текста (скорость печати)
                        if ai_protection:
                            words_count = len(comment_text.split())
                            # Примерно 0.6 сек на слово + случайный шум
                            typing_delay = (words_count * 0.6) * random.uniform(0.7, 1.4)
                            
                            if protection_preset == "conservative":
                                typing_delay *= 1.5
                            elif protection_preset == "aggressive":
                                typing_delay *= 0.5

                            typing_delay = max(3.0, min(typing_delay, 20.0))
                            self.log(f"Симуляция набора текста: жду {typing_delay:.1f} сек...", "info")
                            await self.sleep(typing_delay)

                        # Отправка
                        try:
                            try:
                                await discussion_msg.reply(comment_text)
                            except RPCError as e:
                                if "CHAT_GUEST_SEND_FORBIDDEN" in str(e):
                                    self.log(f"Необходимо вступить в чат комментариев {discussion_chat_id}. Вступаю...", "warning")
                                    await self.client.join_chat(discussion_chat_id)
                                    await self.sleep(random.uniform(4.0, 8.0))
                                    await discussion_msg.reply(comment_text)
                                else:
                                    raise e

                            comments_sent += 1
                            self.log(f"💬 [Успех] Комментарий оставлен: '{comment_text}' (Всего: {comments_sent})", "success")
                            
                            if followup_enabled:
                                duration = random.uniform(1.0, max(1.1, followup_hours)) * 3600
                                end_time = time.time() + duration
                                next_check = time.time() + random.uniform(300, 600)
                                
                                pending_followups.append({
                                    "channel_name": channel_name,
                                    "post_id": msg.id,
                                    "discussion_chat_id": discussion_msg.chat.id,
                                    "discussion_msg_id": discussion_msg.id,
                                    "primary_comment_text": comment_text,
                                    "used_prompt": active_prompt,
                                    "end_time": end_time,
                                    "next_check_time": next_check,
                                    "replied_count": 0
                                })
                                self.log(f"Пост ID {msg.id} добавлен во 2-й круг автоответов.", "info")

                        except FloodWait as fe:
                            self.log(f"FloodWait: ожидание {fe.value} сек...", "warning")
                            await self.sleep(fe.value)
                        except RPCError as e:
                            if "USER_BANNED_IN_CHANNEL" in str(e):
                                self.log(f"❌ [БАН] Отправка не удалась: Аккаунт заблокирован в канале/чате {channel_name} или имеет ограничение от @SpamBot.", "error")
                            elif "CHAT_WRITE_FORBIDDEN" in str(e):
                                self.log(f"⚠️ [Ограничение] Писать в чате {channel_name} запрещено (нет прав или чат только для чтения).", "warning")
                            elif "SLOWMODE_WAIT" in str(e):
                                self.log(f"⚠️ [Slowmode] В чате {channel_name} включен медленный режим. Пропускаю.", "warning")
                            else:
                                self.log(f"Не удалось отправить комментарий (ошибка Telegram): {e}", "error")
                        except Exception as e:
                            self.log(f"Не удалось отправить комментарий: {e}", "error")

                        # Запоминаем последний обработанный ID
                        self.last_post_ids[key] = msg.id
                        self.save_state()

                        # Случайная пауза между комментариями
                        post_delay = random.uniform(15.0, 45.0)
                        if ai_protection:
                            if protection_preset == "conservative":
                                post_delay = random.uniform(45.0, 150.0)
                            elif protection_preset == "aggressive":
                                post_delay = random.uniform(5.0, 15.0)
                        await self.sleep(post_delay)

                except Exception as ce:
                    self.log(f"Ошибка проверки канала {channel_name}: {ce}", "warning")

            # ----------------------------------------------------
            # Обработка ВТОРОГО КРУГА (Ответы в тредах)
            # ----------------------------------------------------
            if followup_enabled and pending_followups:
                current_time = time.time()
                
                # Фильтруем истекшие
                expired = [p for p in pending_followups if current_time > p["end_time"]]
                for exp in expired:
                    self.log(f"Слежение за комментариями к посту ID {exp['post_id']} завершено.", "info")
                pending_followups = [p for p in pending_followups if current_time <= p["end_time"]]

                for p in pending_followups:
                    if getattr(self, "is_stopped", False):
                        break
                    if current_time >= p["next_check_time"] and p["replied_count"] < 1:
                        # Проверяем раз в 10-15 минут
                        p["next_check_time"] = current_time + random.uniform(600, 900)
                        
                        try:
                            eligible_comments = []
                            our_replied_ids = set()
                            
                            async for reply in self.client.get_chat_history(p["discussion_chat_id"], limit=30):
                                if reply.from_user and reply.from_user.is_self:
                                    if reply.reply_to_message_id:
                                        our_replied_ids.add(reply.reply_to_message_id)
                                    if reply.reply_to_message:
                                        our_replied_ids.add(reply.reply_to_message.message_id)
                                else:
                                    if not reply.service and not reply.empty and reply.from_user:
                                        eligible_comments.append(reply)

                            candidates = []
                            for comment in eligible_comments:
                                if comment.id in our_replied_ids or comment.id == p["discussion_msg_id"]:
                                    continue
                                is_in_thread = (
                                    comment.reply_to_message_id == p["discussion_msg_id"] or
                                    (comment.reply_to_message and (
                                        comment.reply_to_message.message_id == p["discussion_msg_id"] or
                                        comment.reply_to_message.reply_to_top_message_id == p["discussion_msg_id"]
                                    ))
                                )
                                if is_in_thread:
                                    candidates.append(comment)

                            if candidates and random.randint(1, 100) <= followup_chance:
                                target_comment = random.choice(candidates)
                                target_text = (target_comment.text or target_comment.caption or "").strip()
                                username_disp = f"@{target_comment.from_user.username}" if target_comment.from_user.username else f"ID {target_comment.from_user.id}"
                                
                                self.log(f"Второй круг: Генерация ответа для {username_disp} под постом ID {p['post_id']}...", "info")
                                
                                base_prompt = p.get("used_prompt", system_prompt)
                                reply_prompt = (
                                    f"{base_prompt}\n"
                                    f"Контекст: Ты оставил комментарий '{p['primary_comment_text']}' к публикации.\n"
                                    f"Пользователь {username_disp} написал в этой ветке комментарий: '{target_text}'.\n"
                                    f"Напиши короткий (до 10 слов), живой, разговорный и естественный ответ на его комментарий в этой же ветке обсуждения. Будь дружелюбен или ироничен в зависимости от твоего характера. Без хэштегов, без официального тона."
                                )
                                
                                reply_text = await self._generate_comment(
                                    post_text=f"Пост: [публикация]. Комментарий: {target_text}",
                                    system_prompt=reply_prompt,
                                    api_key=api_key,
                                    api_url=api_base_url,
                                    model_name=model_name,
                                    auto_language=auto_language
                                )
                                
                                if reply_text:
                                    typing_delay = random.uniform(3.0, 7.0)
                                    await self.sleep(typing_delay)
                                    await target_comment.reply(reply_text)
                                    p["replied_count"] += 1
                                    self.log(f"💬 [Успех Второй Круг] Отправлен ответ для {username_disp}: '{reply_text}'", "success")
                                    await self.sleep(random.uniform(5.0, 15.0))
                        except Exception as fe:
                            self.log(f"Ошибка отслеживания второго круга: {fe}", "warning")

            # Пауза общего цикла опроса каналов (рандомизировано от 45 до 90 секунд)
            poll_sleep = random.uniform(45.0, 90.0)
            await self.sleep(poll_sleep)

        self.log(f"Работа модуля комментирования завершена. Всего отправлено: {comments_sent} комментариев.", "success")
        await self.cleanup()

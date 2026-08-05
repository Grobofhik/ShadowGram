import os
import time
import random

async def bot_start(executor, params):
    bot_username = executor.resolve_string(params.get("bot_username", "")).strip()
    payload = executor.resolve_string(params.get("payload", "")).strip()
    if not bot_username:
        executor.log("Пропуск: не заполнен юзернейм бота.", "warning")
        return "next"
    
    command = "/start"
    if payload:
        command += f" {payload}"
        
    try:
        from hydrogram.enums import ChatAction
        try:
            await executor.client.send_chat_action(bot_username, ChatAction.TYPING)
        except Exception:
            pass
        await executor.sleep(random.randint(1, 2))
        
        await executor.client.send_message(bot_username, command)
        executor.log(f"Бот {bot_username} успешно запущен с командой '{command}'", "success")
    except Exception as e:
        executor.log(f"Ошибка запуска бота {bot_username}: {e}", "error")
    return "next"

async def bot_send_command(executor, params):
    bot_username = executor.resolve_string(params.get("bot_username", "")).strip()
    command = executor.resolve_string(params.get("command", "")).strip()
    if not bot_username or not command:
        executor.log("Пропуск: юзернейм бота или команда пустые.", "warning")
        return "next"
    
    if not command.startswith("/"):
        command = "/" + command
        
    try:
        from hydrogram.enums import ChatAction
        try:
            await executor.client.send_chat_action(bot_username, ChatAction.TYPING)
        except Exception:
            pass
        await executor.sleep(random.randint(1, 2))
        
        await executor.client.send_message(bot_username, command)
        executor.log(f"В бот {bot_username} отправлена команда '{command}'", "success")
    except Exception as e:
        executor.log(f"Ошибка отправки команды в бот {bot_username}: {e}", "error")
    return "next"

async def bot_click_inline(executor, params):
    post_url_or_chat = executor.resolve_string(params.get("post_url", params.get("bot_username", ""))).strip()
    btn_target = executor.resolve_string(params.get("button_target", params.get("button_text", ""))).strip()
    
    if not post_url_or_chat or not btn_target:
        executor.log("Пропуск: Ссылка/Чат или номер/текст кнопки не заполнены.", "warning")
        return "next"
    
    try:
        chat_id = None
        message_id = None

        # 1. Распарсим прямую ссылку на пост вида https://t.me/c/12345/678 или https://t.me/username/678
        import re
        link_match = re.match(r"https?://t\.me/(?:c/(\d+)|([a-zA-Z0-9_]+))/(\d+)", post_url_or_chat)
        if link_match:
            channel_id_num, channel_username, msg_id_str = link_match.groups()
            chat_id = int(f"-100{channel_id_num}") if channel_id_num else f"@{channel_username}"
            message_id = int(msg_id_str)
        else:
            chat_id = post_url_or_chat

        # Единичная попытка получить конкретное сообщение по ID из ссылки
        target_message = None
        if message_id:
            try:
                target_message = await executor.client.get_messages(chat_id, message_id)
            except Exception as msg_err:
                executor.log(f"Не удалось получить сообщение по ID {message_id}: {msg_err}", "warning")
        
        # Если это бот или ссылка без message_id, запускаем динамический опрос (polling) до timeout секунд
        timeout_sec = int(params.get("timeout", 15))
        start_time = time.time()
        
        while not target_message or not (target_message.reply_markup and target_message.reply_markup.inline_keyboard):
            async for msg in executor.client.get_chat_history(chat_id, limit=10):
                if msg.reply_markup and msg.reply_markup.inline_keyboard:
                    target_message = msg
                    break

            if target_message and target_message.reply_markup and target_message.reply_markup.inline_keyboard:
                break

            if (time.time() - start_time) > timeout_sec:
                break
                
            await executor.sleep(1.5)

        if not target_message or not (target_message.reply_markup and target_message.reply_markup.inline_keyboard):
            executor.log(f"Таймаут ({timeout_sec} сек): Не найдено сообщений с inline-кнопками в {chat_id}", "warning")
            return "next"

        keyboard = target_message.reply_markup.inline_keyboard
        flattened_buttons = []
        for row_idx, row in enumerate(keyboard):
            for col_idx, button in enumerate(row):
                flattened_buttons.append((row_idx, col_idx, button))

        selected_row = None
        selected_col = None
        selected_button = None

        # Проверка: указан ли порядок по номеру (например 1, 2, 3...)
        if btn_target.isdigit():
            idx = int(btn_target) - 1 # 1-based index
            if 0 <= idx < len(flattened_buttons):
                selected_row, selected_col, selected_button = flattened_buttons[idx]
        else:
            # Поиск по тексту кнопки (без учета регистра)
            for row_idx, col_idx, button in flattened_buttons:
                if btn_target.lower() in button.text.lower():
                    selected_row = row_idx
                    selected_col = col_idx
                    selected_button = button
                    break

        if selected_button and selected_row is not None and selected_col is not None:
            # Если кнопка является URL-кнопкой (содержит ссылку на канал/чат), сохраняем ссылку в контекст
            btn_url = getattr(selected_button, "url", None)
            if btn_url:
                executor.last_channel_url = btn_url
                executor.last_chat_link = btn_url
                executor.variables["channel_link"] = btn_url
                executor.variables["chat_link"] = btn_url
                executor.log(f"[Контекст]: Нажата URL-кнопка, извлечена ссылка для подписки: {btn_url}", "info")
                return "next"

            await executor.sleep(random.randint(1, 3))
            feedback = ""
            click_success = False

            # 1. Запрос через raw Telegram MTProto GetBotCallbackAnswer
            try:
                from hydrogram.raw.functions.messages import GetBotCallbackAnswer
                peer = await executor.client.resolve_peer(chat_id)
                data_bytes = selected_button.callback_data
                if isinstance(data_bytes, str):
                    data_bytes = data_bytes.encode("utf-8")

                res = await executor.client.invoke(
                    GetBotCallbackAnswer(
                        peer=peer,
                        msg_id=target_message.id,
                        data=data_bytes
                    )
                )
                cb_msg = getattr(res, 'message', None) or getattr(res, 'text', None) or ""
                cb_url = getattr(res, 'url', None) or ""
                if cb_msg:
                    feedback = f" (Ответ: {cb_msg})"
                if cb_url:
                    feedback += f" (URL: {cb_url})"
                    executor.last_channel_url = cb_url
                    executor.last_chat_link = cb_url
                    executor.variables["channel_link"] = cb_url
                    executor.variables["chat_link"] = cb_url

                # Если в тексте ответа есть ссылка (например, t.me/Imiss009 или https://t.me/...), вытаскиваем её
                import re
                urls = re.findall(r'(?:https?://)?t\.me/[a-zA-Z0-9_\+\-]+', cb_msg)
                if urls:
                    target_url = urls[0]
                    if not target_url.startswith("http"):
                        target_url = "https://" + target_url
                    executor.last_channel_url = target_url
                    executor.last_chat_link = target_url
                    executor.variables["channel_link"] = target_url
                    executor.variables["chat_link"] = target_url
                    executor.log(f"[Контекст]: Из всплывающего ответа извлечена ссылка для подписки: {target_url}", "info")

                click_success = True
            except Exception as raw_err:
                executor.log(f"MTProto GetBotCallbackAnswer exception: {raw_err}", "info")

            # 2. Фолбэк через client.request_callback_answer
            if not click_success:
                try:
                    res = await executor.client.request_callback_answer(
                        chat_id=chat_id,
                        message_id=target_message.id,
                        callback_data=selected_button.callback_data
                    )
                    cb_msg = getattr(res, 'text', None) or getattr(res, 'message', None) or ""
                    cb_url = getattr(res, 'url', None) or ""
                    if cb_msg:
                        feedback = f" (Ответ: {cb_msg})"
                    if cb_url:
                        feedback += f" (URL: {cb_url})"
                        executor.last_channel_url = cb_url
                        executor.last_chat_link = cb_url
                        executor.variables["channel_link"] = cb_url
                        executor.variables["chat_link"] = cb_url

                    import re
                    urls = re.findall(r'(?:https?://)?t\.me/[a-zA-Z0-9_\+\-]+', cb_msg)
                    if urls:
                        target_url = urls[0]
                        if not target_url.startswith("http"):
                            target_url = "https://" + target_url
                        executor.last_channel_url = target_url
                        executor.last_chat_link = target_url
                        executor.variables["channel_link"] = target_url
                        executor.variables["chat_link"] = target_url
                        executor.log(f"[Контекст]: Из всплывающего ответа извлечена ссылка для подписки: {target_url}", "info")

                    click_success = True
                except Exception as cb_err:
                    executor.log(f"Callback answer warning: {cb_err}", "info")

            if click_success:
                executor.log(f"Успешно нажата inline-кнопка '{selected_button.text}' в {chat_id}{feedback}", "success")
        else:
            executor.log(f"Кнопка '{btn_target}' не найдена среди {len(flattened_buttons)} доступных кнопок.", "warning")

    except Exception as e:
        executor.log(f"Ошибка при клике по inline-кнопке: {e}", "error")
    return "next"

async def bot_click_keyboard(executor, params):
    bot_username = executor.resolve_string(params.get("bot_username", "")).strip()
    btn_match = executor.resolve_string(params.get("button_text", "")).strip()
    if not bot_username or not btn_match:
        executor.log("Пропуск: юзернейм бота или текст кнопки пустые.", "warning")
        return "next"
    
    try:
        found_text = None
        async for message in executor.client.get_chat_history(bot_username, limit=10):
            if message.reply_markup and message.reply_markup.keyboard:
                for row in message.reply_markup.keyboard:
                    for button in row:
                        if btn_match.lower() in button.text.lower():
                            found_text = button.text
                            break
                    if found_text:
                        break
            if found_text:
                break
                
        text_to_send = found_text or btn_match
        
        from hydrogram.enums import ChatAction
        try:
            await executor.client.send_chat_action(bot_username, ChatAction.TYPING)
        except Exception:
            pass
        await executor.sleep(random.randint(1, 2))
        
        await executor.client.send_message(bot_username, text_to_send)
        if found_text:
            executor.log(f"Нажата кнопка меню '{found_text}' у бота {bot_username}", "success")
        else:
            executor.log(f"Отправлен текст '{text_to_send}' в качестве кнопки у бота {bot_username}", "info")
    except Exception as e:
        executor.log(f"Ошибка нажатия кнопки меню у {bot_username}: {e}", "error")
    return "next"

async def bot_open_web_app(executor, params):
    bot_username = executor.resolve_string(params.get("bot_username", "")).strip()
    short_name = executor.resolve_string(params.get("short_name", "")).strip()
    if not bot_username or not short_name:
        executor.log("Пропуск: юзернейм бота или short_name приложения пустые.", "warning")
        return "next"
        
    try:
        res = await executor.client.request_app_web_view(
            bot_username,
            short_name
        )
        executor.variables["web_app_url"] = res.url
        executor.log(f"Успешно получен URL Mini App для бота {bot_username}: {res.url[:60]}...", "success")
    except Exception as e:
        executor.log(f"Ошибка открытия Mini App: {e}", "error")
    return "next"

async def bot_inline_query(executor, params):
    bot_username = executor.resolve_string(params.get("bot_username", "")).strip()
    query = executor.resolve_string(params.get("query", "")).strip()
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not bot_username or not chat_id:
        executor.log("Пропуск: юзернейм инлайн-бота или chat_id пустые.", "warning")
        return "next"
        
    try:
        results = await executor.client.get_inline_bot_results(bot_username, query)
        if results and results.results:
            first_result = results.results[0]
            await executor.client.send_inline_bot_result(
                chat_id=chat_id,
                query_id=results.query_id,
                result_id=first_result.id
            )
            executor.log(f"Инлайн-запрос в {bot_username} выполнен. Результат отправлен в {chat_id}.", "success")
        else:
            executor.log(f"Инлайн-бот {bot_username} не вернул результатов по запросу '{query}'.", "warning")
    except Exception as e:
        executor.log(f"Ошибка выполнения инлайн-запроса: {e}", "error")
    return "next"

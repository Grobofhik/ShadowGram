import os
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
    bot_username = executor.resolve_string(params.get("bot_username", "")).strip()
    btn_match = executor.resolve_string(params.get("button_text", "")).strip()
    if not bot_username or not btn_match:
        executor.log("Пропуск: юзернейм бота или текст кнопки пустые.", "warning")
        return "next"
    
    try:
        found = False
        async for message in executor.client.get_chat_history(bot_username, limit=10):
            if message.reply_markup and message.reply_markup.inline_keyboard:
                for row_idx, row in enumerate(message.reply_markup.inline_keyboard):
                    for col_idx, button in enumerate(row):
                        match_idx_str_1 = str(row_idx * len(row) + col_idx)
                        match_idx_str_2 = f"{row_idx},{col_idx}"
                        
                        if (btn_match.lower() in button.text.lower()) or (btn_match == match_idx_str_1) or (btn_match == match_idx_str_2):
                            await message.click(row_idx, col_idx)
                            executor.log(f"Успешно нажата inline-кнопка '{button.text}' у бота {bot_username}", "success")
                            found = True
                            break
                    if found:
                        break
            if found:
                break
        if not found:
            executor.log(f"Не удалось найти inline-кнопку по запросу '{btn_match}' у последних сообщений {bot_username}", "warning")
    except Exception as e:
        executor.log(f"Ошибка при нажатии inline-кнопки у {bot_username}: {e}", "error")
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

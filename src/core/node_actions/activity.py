import random

async def join_chat(executor, params):
    chat_link = executor.resolve_string(params.get("chat_link", "")).strip()
    if not chat_link:
        executor.log("Пропуск: ссылка на чат пустая.", "warning")
    else:
        await executor.sleep(random.randint(1, 4))
        chat = await executor.client.join_chat(chat_link)
        executor.log(f"Успешное вступление в чат: {chat.title}", "success")
    return "next"

async def leave_chat(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: ID чата пустое.", "warning")
    else:
        await executor.client.leave_chat(chat_id)
        executor.log(f"Вышли из чата/канала {chat_id}", "success")
    return "next"

async def auto_react(executor, params):
    channel_url = executor.resolve_string(params.get("channel_url", "")).strip()
    posts_count = int(params.get("posts_count", 5))
    reaction_chance = int(params.get("reaction_chance", 100))
    
    if not channel_url:
        executor.log("Пропуск: ссылка на канал пустая.", "warning")
    else:
        executor.log(f"Читаем последние {posts_count} постов канала {channel_url}...", "info")
        reactions_pool = ["👍", "🔥", "❤️", "👏", "🎉", "🤩"]
        
        async for message in executor.client.get_chat_history(channel_url, limit=posts_count):
            if random.randint(1, 100) <= reaction_chance:
                react = random.choice(reactions_pool)
                try:
                    await executor.client.send_reaction(channel_url, message.id, react)
                    executor.log(f"Реакция {react} поставлена на post_id: {message.id}", "success")
                except Exception as react_err:
                    executor.log(f"Не удалось поставить реакцию на пост {message.id}: {react_err}", "warning")
                await executor.sleep(random.randint(2, 4))
    return "next"

async def ai_reply(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    prompt = executor.resolve_string(params.get("prompt", "")).strip()
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        last_msg = ""
        async for message in executor.client.get_chat_history(chat_id, limit=1):
            last_msg = message.text or "[Вложение без текста]"
        
        executor.log(f"Запрос ИИ для ответа на сообщение: '{last_msg[:30]}...'", "info")
        response_text = await executor.generate_ai_text(
            prompt=f"Сгенерируй краткий ответ на сообщение: '{last_msg}'",
            system_prompt=prompt
        )
        if response_text:
            from hydrogram.enums import ChatAction
            try:
                await executor.client.send_chat_action(chat_id, ChatAction.TYPING)
            except Exception:
                pass
            typing_duration = min(7, max(2, len(response_text) // 40))
            executor.log(f"Имитация ввода ИИ-ответа в {chat_id} ({typing_duration} сек)...", "info")
            await executor.sleep(typing_duration)
            
            await executor.client.send_message(chat_id, response_text)
            executor.log(f"Отправлен ИИ-ответ: {response_text}", "success")
        else:
            executor.log("Не удалось получить ответ от ИИ-модели.", "warning")
    return "next"

async def read_chat_history(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        await executor.client.read_chat_history(chat_id)
        executor.log(f"Диалог {chat_id} отмечен прочитанным.", "success")
    return "next"

async def archive_chats(executor, params):
    chat_ids_raw = executor.resolve_string(params.get("chat_ids", "")).strip()
    if not chat_ids_raw:
        executor.log("Пропуск: ID чатов пустые.", "warning")
    else:
        chat_ids = [executor.resolve_string(c.strip()) for c in chat_ids_raw.split(",") if c.strip()]
        await executor.client.archive_chats(chat_ids)
        executor.log(f"Архивировано чатов: {len(chat_ids)}", "success")
    return "next"

async def unarchive_chats(executor, params):
    chat_ids_raw = executor.resolve_string(params.get("chat_ids", "")).strip()
    if not chat_ids_raw:
        executor.log("Пропуск: ID чатов пустые.", "warning")
    else:
        chat_ids = [executor.resolve_string(c.strip()) for c in chat_ids_raw.split(",") if c.strip()]
        await executor.client.unarchive_chats(chat_ids)
        executor.log(f"Разархивировано чатов: {len(chat_ids)}", "success")
    return "next"

async def scrape_chat_members(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    output_file = executor.resolve_string(params.get("output_file", "scraped_users.txt")).strip()
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        executor.log(f"Сбор участников чата {chat_id}...", "info")
        usernames = []
        # Get chat members
        async for member in executor.client.get_chat_members(chat_id):
            if member.user and member.user.username:
                usernames.append(f"@{member.user.username}")
                
        if usernames:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(usernames))
            executor.log(f"Успешно собрано {len(usernames)} участников чата {chat_id}. Список сохранен в '{output_file}'", "success")
        else:
            executor.log(f"В чате {chat_id} не найдено публичных участников с юзернеймами.", "warning")
    return "next"

async def pin_chat(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        await executor.client.pin_chat(chat_id)
        executor.log(f"Чат {chat_id} успешно закреплен.", "success")
    return "next"

async def unpin_chat(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        await executor.client.unpin_chat(chat_id)
        executor.log(f"Чат {chat_id} успешно откреплен.", "success")
    return "next"

async def download_media(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id_raw = params.get("message_id", 0)
    download_dir = executor.resolve_string(params.get("download_dir", "downloads")).strip()
    
    if isinstance(message_id_raw, str):
        message_id_str = executor.resolve_string(message_id_raw).strip()
        message_id = int(message_id_str) if message_id_str.isdigit() else 0
    else:
        message_id = int(message_id_raw)
        
    if not chat_id:
        executor.log("Пропуск: не указан chat_id для скачивания медиа.", "warning")
        return "next"
        
    try:
        msg = None
        if message_id == 0:
            async for m in executor.client.get_chat_history(chat_id, limit=1):
                msg = m
        else:
            msg = await executor.client.get_messages(chat_id, message_id)
            
        if msg and (msg.photo or msg.video or msg.document or msg.voice or msg.audio or msg.animation):
            os.makedirs(download_dir, exist_ok=True)
            # download_media returns the path where the file was saved
            file_path = await executor.client.download_media(msg, file_name=os.path.join(download_dir, ""))
            executor.variables["downloaded_file_path"] = file_path
            executor.log(f"Медиафайл успешно скачан: {file_path}", "success")
        else:
            executor.log("В сообщении нет медиафайлов для скачивания.", "warning")
    except Exception as e:
        executor.log(f"Ошибка скачивания медиафайла: {e}", "error")
    return "next"

async def comment_channel_post(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id_raw = params.get("message_id", 0)
    text = executor.resolve_string(params.get("text", "")).strip()
    
    if isinstance(message_id_raw, str):
        message_id_str = executor.resolve_string(message_id_raw).strip()
        message_id = int(message_id_str) if message_id_str.isdigit() else 0
    else:
        message_id = int(message_id_raw)
        
    if not chat_id or not message_id or not text:
        executor.log("Пропуск: не заполнены параметры для комментария.", "warning")
        return "next"
        
    try:
        disc_msg = await executor.client.get_discussion_message(chat_id, message_id)
        await disc_msg.reply(text)
        executor.log(f"Успешно оставлен комментарий под постом {message_id} в {chat_id}.", "success")
    except Exception as e:
        executor.log(f"Ошибка комментирования поста {message_id} в {chat_id}: {e}", "error")
    return "next"

async def forward_channel_post(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id_raw = params.get("message_id", 0)
    to_chat_id = executor.resolve_string(params.get("to_chat_id", "")).strip()
    
    if isinstance(message_id_raw, str):
        message_id_str = executor.resolve_string(message_id_raw).strip()
        message_id = int(message_id_str) if message_id_str.isdigit() else 0
    else:
        message_id = int(message_id_raw)
        
    if not chat_id or not message_id or not to_chat_id:
        executor.log("Пропуск: не заполнены параметры для пересылки поста.", "warning")
        return "next"
        
    try:
        await executor.client.forward_messages(to_chat_id, chat_id, message_id)
        executor.log(f"Пост {message_id} из канала {chat_id} успешно переслан в {to_chat_id}.", "success")
    except Exception as e:
        executor.log(f"Ошибка пересылки поста {message_id}: {e}", "error")
    return "next"

async def react_to_post(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id_raw = params.get("message_id", 0)
    emoji = executor.resolve_string(params.get("emoji", "👍")).strip()
    
    if isinstance(message_id_raw, str):
        message_id_str = executor.resolve_string(message_id_raw).strip()
        message_id = int(message_id_str) if message_id_str.isdigit() else 0
    else:
        message_id = int(message_id_raw)
        
    if not chat_id or not message_id:
        executor.log("Пропуск: не заполнены параметры для реакции.", "warning")
        return "next"
        
    try:
        await executor.client.send_reaction(chat_id, message_id, emoji)
        executor.log(f"Успешно поставлена реакция '{emoji}' на post {message_id} в {chat_id}.", "success")
    except Exception as e:
        executor.log(f"Ошибка отправки реакции на пост {message_id}: {e}", "error")
    return "next"

async def share_post_link(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id_raw = params.get("message_id", 0)
    
    if isinstance(message_id_raw, str):
        message_id_str = executor.resolve_string(message_id_raw).strip()
        message_id = int(message_id_str) if message_id_str.isdigit() else 0
    else:
        message_id = int(message_id_raw)
        
    if not chat_id or not message_id:
        executor.log("Пропуск: не заполнены параметры для получения ссылки.", "warning")
        return "next"
        
    try:
        chat = await executor.client.get_chat(chat_id)
        if chat.username:
            link = f"https://t.me/{chat.username}/{message_id}"
        else:
            clean_id = str(chat.id).replace("-100", "")
            link = f"https://t.me/c/{clean_id}/{message_id}"
            
        executor.variables["post_link"] = link
        executor.log(f"Получена ссылка на пост {message_id}: {link}", "success")
    except Exception as e:
        executor.log(f"Ошибка получения ссылки на пост {message_id}: {e}", "error")
    return "next"

async def view_user_stories(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: не указан chat_id для просмотра историй.", "warning")
        return "next"
        
    try:
        # In Pyrogram/Hydrogram, active stories can be fetched using get_chat_history_stories
        # and marked read using read_stories
        stories = []
        async for story in executor.client.get_chat_history_stories(chat_id):
            stories.append(story.id)
            
        if stories:
            await executor.client.read_stories(chat_id, stories)
            executor.log(f"Успешно просмотрено {len(stories)} историй пользователя {chat_id}.", "success")
        else:
            executor.log(f"У пользователя {chat_id} нет активных историй для просмотра.", "info")
    except Exception as e:
        executor.log(f"Ошибка просмотра историй {chat_id}: {e}", "error")
    return "next"

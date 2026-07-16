import os
import datetime
from hydrogram.types import ChatPermissions

async def create_group(executor, params):
    title = executor.resolve_string(params.get("title", "Новая группа")).strip()
    users_raw = executor.resolve_string(params.get("users", "")).strip()
    users = [u.strip() for u in users_raw.split(",") if u.strip()]
    
    group = await executor.client.create_group(title, users)
    executor.log(f"Группа '{title}' успешно создана (ID: {group.id})", "success")
    return "next"

async def create_channel(executor, params):
    title = executor.resolve_string(params.get("title", "Новый канал")).strip()
    description = executor.resolve_string(params.get("description", "")).strip()
    
    channel = await executor.client.create_channel(title, description)
    executor.log(f"Канал '{title}' успешно создан (ID: {channel.id})", "success")
    return "next"

async def set_chat_title(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    title = executor.resolve_string(params.get("title", "")).strip()
    if not chat_id or not title:
        executor.log("Пропуск: ID чата или имя пустое.", "warning")
    else:
        await executor.client.set_chat_title(chat_id, title)
        executor.log(f"Название чата {chat_id} успешно изменено на '{title}'", "success")
    return "next"

async def set_chat_description(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    description = executor.resolve_string(params.get("description", "")).strip()
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        await executor.client.set_chat_description(chat_id, description)
        executor.log(f"Описание чата {chat_id} успешно изменено.", "success")
    return "next"

async def set_chat_photo(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    photo_path = executor.resolve_string(params.get("photo_path", "")).strip()
    if not chat_id or not os.path.exists(photo_path):
        executor.log(f"Пропуск: чат {chat_id} не указан или фото '{photo_path}' не существует.", "warning")
    else:
        await executor.client.set_chat_photo(chat_id, photo=photo_path)
        executor.log(f"Аватар чата {chat_id} изменен.", "success")
    return "next"

async def delete_chat_photo(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        await executor.client.delete_chat_photo(chat_id)
        executor.log(f"Аватар чата {chat_id} удален.", "success")
    return "next"

async def pin_chat_message(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id = int(params.get("message_id", 0))
    silent = bool(int(params.get("silent", 1)))
    if not chat_id or message_id == 0:
        executor.log("Пропуск: неверные параметры закрепления.", "warning")
    else:
        await executor.client.pin_chat_message(chat_id, message_id, disable_notification=silent)
        executor.log(f"Сообщение {message_id} закреплено в {chat_id}", "success")
    return "next"

async def unpin_chat_message(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id = int(params.get("message_id", 0))
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        if message_id == 0:
            await executor.client.unpin_all_chat_messages(chat_id)
            executor.log(f"Откреплены все сообщения в {chat_id}", "success")
        else:
            await executor.client.unpin_chat_message(chat_id, message_id)
            executor.log(f"Сообщение {message_id} откреплено в {chat_id}", "success")
    return "next"

async def restrict_chat_member(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    user_id = executor.resolve_string(params.get("user_id", "")).strip()
    until_date_sec = int(params.get("until_date_sec", 0))
    if not chat_id or not user_id:
        executor.log("Пропуск: ID чата или юзера пустые.", "warning")
    else:
        until = datetime.datetime.now() + datetime.timedelta(seconds=until_date_sec) if until_date_sec > 0 else None
        await executor.client.restrict_chat_member(chat_id, user_id, ChatPermissions(), until_date=until)
        executor.log(f"Пользователь {user_id} ограничен в чате {chat_id} (срок: {until_date_sec} сек)", "success")
    return "next"

async def promote_chat_member(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    user_id = executor.resolve_string(params.get("user_id", "")).strip()
    if not chat_id or not user_id:
        executor.log("Пропуск: ID чата или юзера пустые.", "warning")
    else:
        await executor.client.promote_chat_member(chat_id, user_id, is_anonymous=False)
        executor.log(f"Пользователь {user_id} назначен администратором чата {chat_id}", "success")
    return "next"

async def ban_chat_member(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    user_id = executor.resolve_string(params.get("user_id", "")).strip()
    if not chat_id or not user_id:
        executor.log("Пропуск: ID чата или юзера пустые.", "warning")
    else:
        await executor.client.ban_chat_member(chat_id, user_id)
        executor.log(f"Пользователь {user_id} забанен в чате {chat_id}", "success")
    return "next"

async def unban_chat_member(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    user_id = executor.resolve_string(params.get("user_id", "")).strip()
    if not chat_id or not user_id:
        executor.log("Пропуск: ID чата или юзера пустые.", "warning")
    else:
        await executor.client.unban_chat_member(chat_id, user_id)
        executor.log(f"Пользователь {user_id} разбанен в чате {chat_id}", "success")
    return "next"

async def export_chat_invite_link(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        link = await executor.client.export_chat_invite_link(chat_id)
        executor.variables["invite_link"] = link
        executor.log(f"Ссылка-приглашение экспортирована в {{invite_link}}: {link}", "success")
    return "next"

async def set_chat_slow_mode(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    seconds = int(params.get("seconds", 10))
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        # slow_mode is set using set_chat_slow_mode in hydrogram/pyrogram
        await executor.client.set_chat_slow_mode(chat_id, seconds)
        executor.log(f"Для чата {chat_id} установлен медленный режим: {seconds} сек.", "success")
    return "next"

async def set_chat_permissions(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    send_messages = bool(int(params.get("send_messages", 1)))
    send_media = bool(int(params.get("send_media", 1)))
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        permissions = ChatPermissions(
            can_send_messages=send_messages,
            can_send_media_messages=send_media
        )
        await executor.client.set_chat_permissions(chat_id, permissions)
        executor.log(f"Для чата {chat_id} обновлены права (отправка сообщений: {send_messages}, медиа: {send_media})", "success")
    return "next"

async def set_chat_username(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    username = executor.resolve_string(params.get("username", "")).strip().replace("@", "")
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        try:
            await executor.client.set_chat_username(chat_id, username if username else None)
            executor.log(f"Для чата {chat_id} успешно установлен юзернейм: @{username}" if username else f"Для чата {chat_id} юзернейм удален.", "success")
        except Exception as e:
            executor.log(f"Ошибка изменения юзернейма чата {chat_id}: {e}", "error")
    return "next"

async def get_channel_posts(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    limit = int(params.get("limit", 5))
    if not chat_id:
        executor.log("Пропуск: не указан chat_id для получения постов.", "warning")
        return "next"
    try:
        posts = []
        async for msg in executor.client.get_chat_history(chat_id, limit=limit):
            if msg.text or msg.caption:
                content = msg.text or msg.caption
                posts.append(f"Пост {msg.id}: {content}")
        if posts:
            executor.variables["channel_posts_text"] = "\n\n".join(posts)
            first_content = (posts[0].split(": ", 1)[1]) if ": " in posts[0] else posts[0]
            executor.variables["channel_last_post_text"] = first_content
            executor.log(f"Успешно выгружено {len(posts)} постов из канала {chat_id}.", "success")
        else:
            executor.variables["channel_posts_text"] = ""
            executor.variables["channel_last_post_text"] = ""
            executor.log("Посты в канале не найдены.", "info")
    except Exception as e:
        executor.log(f"Ошибка выгрузки постов из канала: {e}", "error")
    return "next"

async def approve_join_requests(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    user_id_str = executor.resolve_string(params.get("user_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: не указан chat_id для одобрения заявок.", "warning")
        return "next"
    try:
        if user_id_str:
            await executor.client.approve_chat_join_request(chat_id, user_id_str)
            executor.log(f"Одобрена заявка на вступление пользователя {user_id_str} в чат {chat_id}.", "success")
        else:
            count = 0
            async for request in executor.client.get_chat_join_requests(chat_id):
                await executor.client.approve_chat_join_request(chat_id, request.user.id)
                count += 1
            executor.log(f"Одобрено {count} заявок на вступление в чат {chat_id}.", "success")
    except Exception as e:
        executor.log(f"Ошибка одобрения заявок в чате {chat_id}: {e}", "error")
    return "next"

async def edit_channel_post(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id_raw = params.get("message_id", 0)
    new_text = executor.resolve_string(params.get("new_text", "")).strip()
    
    if isinstance(message_id_raw, str):
        message_id_str = executor.resolve_string(message_id_raw).strip()
        message_id = int(message_id_str) if message_id_str.isdigit() else 0
    else:
        message_id = int(message_id_raw)
        
    if not chat_id or not message_id or not new_text:
        executor.log("Пропуск: не заполнены обязательные параметры для редактирования поста.", "warning")
        return "next"
        
    try:
        await executor.client.edit_message_text(chat_id, message_id, new_text)
        executor.log(f"Пост {message_id} в канале {chat_id} успешно отредактирован.", "success")
    except Exception as e:
        executor.log(f"Ошибка редактирования поста {message_id}: {e}", "error")
    return "next"

async def delete_channel_post(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id_raw = params.get("message_id", 0)
    
    if isinstance(message_id_raw, str):
        message_id_str = executor.resolve_string(message_id_raw).strip()
        message_id = int(message_id_str) if message_id_str.isdigit() else 0
    else:
        message_id = int(message_id_raw)
        
    if not chat_id or not message_id:
        executor.log("Пропуск: не заполнены обязательные параметры для удаления поста.", "warning")
        return "next"
        
    try:
        await executor.client.delete_messages(chat_id, message_id)
        executor.log(f"Пост {message_id} в канале {chat_id} успешно удален.", "success")
    except Exception as e:
        executor.log(f"Ошибка удаления поста {message_id}: {e}", "error")
    return "next"

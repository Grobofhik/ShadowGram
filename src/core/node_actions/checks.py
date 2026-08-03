from hydrogram.errors import UsernameNotOccupied, UsernameInvalid
from hydrogram.enums import UserStatus, ChatMemberStatus

async def check_avatar(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        chat_id = "me"
    try:
        chat = await executor.client.get_chat(chat_id)
        if chat.photo:
            executor.log(f"Проверка аватара для {chat_id}: Аватар присутствует.", "success")
            return "has_avatar"
        else:
            executor.log(f"Проверка аватара для {chat_id}: Аватар отсутствует.", "info")
            return "no_avatar"
    except Exception as e:
        executor.log(f"Ошибка проверки аватара {chat_id}: {e}", "error")
        return "no_avatar"

async def check_username(executor, params):
    username = executor.resolve_string(params.get("username", "")).strip()
    if username.startswith("@"):
        username = username[1:]
    if not username:
        executor.log("Пропуск: пустой юзернейм для проверки.", "warning")
        return "taken"
        
    try:
        try:
            await executor.client.get_chat(username)
            executor.log(f"Юзернейм @{username} ЗАНЯТ.", "info")
            return "taken"
        except UsernameNotOccupied:
            executor.log(f"Юзернейм @{username} СВОБОДЕН.", "success")
            return "available"
        except UsernameInvalid:
            executor.log(f"Юзернейм @{username} НЕКОРРЕКТЕН.", "warning")
            return "taken"
    except Exception as e:
        executor.log(f"Ошибка проверки юзернейма @{username}: {e}", "error")
        return "taken"

async def check_user_status(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: не указан пользователь для проверки статуса.", "warning")
        return "offline"
        
    try:
        user = await executor.client.get_users(chat_id)
        if user.status in [UserStatus.ONLINE]:
            executor.log(f"Пользователь {chat_id} в сети (ONLINE).", "success")
            return "online"
        else:
            executor.log(f"Пользователь {chat_id} не в сети (OFFLINE/скрыт).", "info")
            return "offline"
    except Exception as e:
        executor.log(f"Ошибка проверки статуса {chat_id}: {e}", "error")
        return "offline"

async def check_is_member(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    user_id_str = executor.resolve_string(params.get("user_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: не указан чат для проверки участия.", "warning")
        return "not_member"
        
    if not user_id_str:
        user_id_str = "me"
        
    try:
        member = await executor.client.get_chat_member(chat_id, user_id_str)
        if member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
            executor.log(f"Пользователь {user_id_str} НЕ состоит в {chat_id}.", "info")
            return "not_member"
        else:
            executor.log(f"Пользователь {user_id_str} СОСТОИТ в {chat_id} (статус: {member.status}).", "success")
            return "member"
    except Exception:
        executor.log(f"Пользователь {user_id_str} НЕ состоит в {chat_id} (ошибка или не найден).", "info")
        return "not_member"

async def check_is_premium(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        chat_id = "me"
        
    try:
        user = await executor.client.get_users(chat_id)
        if user.is_premium:
            executor.log(f"Пользователь {chat_id} имеет Telegram Premium! ✨", "success")
            return "premium"
        else:
            executor.log(f"Пользователь {chat_id} НЕ имеет Telegram Premium.", "info")
            return "not_premium"
    except Exception as e:
        executor.log(f"Ошибка проверки Премиума для {chat_id}: {e}", "error")
        return "not_premium"

async def check_bio_link(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        chat_id = "me"
        
    try:
        chat = await executor.client.get_chat(chat_id)
        bio = chat.bio or chat.description or ""
        if "@" in bio or "t.me" in bio or "http" in bio:
            executor.log(f"Проверка био для {chat_id}: найдена ссылка/юзернейм.", "success")
            return "has_link"
        else:
            executor.log(f"Проверка био для {chat_id}: ссылка/юзернейм отсутствует.", "info")
            return "no_link"
    except Exception as e:
        executor.log(f"Ошибка проверки ссылки в био {chat_id}: {e}", "error")
        return "no_link"

async def check_is_admin(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    user_id_str = executor.resolve_string(params.get("user_id", "")).strip()
    
    if not chat_id:
        executor.log("Пропуск: не указан чат для проверки админа.", "warning")
        return "not_admin"
        
    if not user_id_str:
        user_id_str = "me"
        
    try:
        member = await executor.client.get_chat_member(chat_id, user_id_str)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            executor.log(f"Пользователь {user_id_str} ЯВЛЯЕТСЯ админом в {chat_id}.", "success")
            return "admin"
        else:
            executor.log(f"Пользователь {user_id_str} НЕ является админом в {chat_id} (статус: {member.status}).", "info")
            return "not_admin"
    except Exception as e:
        executor.log(f"Ошибка проверки админа в {chat_id}: {e}", "error")
        return "not_admin"

async def check_chat_type(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: не указан чат для проверки типа.", "warning")
        return "private"
        
    try:
        chat = await executor.client.get_chat(chat_id)
        from hydrogram.enums import ChatType
        if chat.type in [ChatType.PRIVATE, ChatType.BOT]:
            executor.log(f"Тип чата {chat_id}: личный чат/бот.", "info")
            return "private"
        elif chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            executor.log(f"Тип чата {chat_id}: группа/супергруппа.", "info")
            return "group"
        elif chat.type in [ChatType.CHANNEL]:
            executor.log(f"Тип чата {chat_id}: канал.", "info")
            return "channel"
        else:
            return "private"
    except Exception as e:
        executor.log(f"Ошибка проверки типа чата {chat_id}: {e}", "error")
        return "private"

async def check_is_restricted(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    user_id_str = executor.resolve_string(params.get("user_id", "")).strip()
    
    if not chat_id:
        executor.log("Пропуск: не указан чат для проверки ограничений.", "warning")
        return "normal"
        
    if not user_id_str:
        user_id_str = "me"
        
    try:
        member = await executor.client.get_chat_member(chat_id, user_id_str)
        if member.status in [ChatMemberStatus.RESTRICTED, ChatMemberStatus.BANNED]:
            executor.log(f"Пользователь {user_id_str} ОГРАНИЧЕН/ЗАБАНЕН в {chat_id}.", "warning")
            return "restricted"
        else:
            executor.log(f"Пользователь {user_id_str} в {chat_id} имеет статус: {member.status} (без ограничений).", "success")
            return "normal"
    except Exception as e:
        executor.log(f"Ошибка проверки ограничений в {chat_id}: {e}", "error")
        return "normal"

async def check_is_contact(executor, params):
    user_id = executor.resolve_string(params.get("user_id", "")).strip()
    if not user_id:
        executor.log("Пропуск: пустой ID для проверки в контактах.", "warning")
        return "not_contact"
        
    try:
        contacts = await executor.client.get_contacts()
        found = False
        for c in contacts:
            if str(c.id) == user_id or (c.username and c.username.lower() == user_id.lower().replace("@", "")):
                found = True
                break
        if found:
            executor.log(f"Пользователь {user_id} НАЙДЕН в контактах.", "success")
            return "contact"
        else:
            executor.log(f"Пользователь {user_id} НЕ найден в контактах.", "info")
            return "not_contact"
    except Exception as e:
        executor.log(f"Ошибка проверки контактов: {e}", "error")
        return "not_contact"

async def check_is_bot(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: не указан пользователь для проверки на бота.", "warning")
        return "user"
    try:
        user = await executor.client.get_users(chat_id)
        if user.is_bot:
            executor.log(f"Пользователь {chat_id} является ботом (BOT).", "success")
            return "bot"
        else:
            executor.log(f"Пользователь {chat_id} является обычным аккаунтом (USER).", "info")
            return "user"
    except Exception as e:
        executor.log(f"Ошибка проверки бота {chat_id}: {e}", "error")
        return "user"

async def check_message_contains(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id_raw = params.get("message_id", 0)
    keyword = executor.resolve_string(params.get("keyword", "")).strip()
    
    if isinstance(message_id_raw, str):
        message_id_str = executor.resolve_string(message_id_raw).strip()
        message_id = int(message_id_str) if message_id_str.isdigit() else 0
    else:
        message_id = int(message_id_raw)
        
    if not chat_id or not keyword:
        executor.log("Пропуск: не указан chat_id или искомая фраза.", "warning")
        return "false"
        
    try:
        msg = None
        if message_id == 0:
            async for m in executor.client.get_chat_history(chat_id, limit=1):
                msg = m
        else:
            msg = await executor.client.get_messages(chat_id, message_id)
            
        if msg and msg.text and keyword.lower() in msg.text.lower():
            executor.log(f"В сообщении {msg.id} в {chat_id} найдена фраза '{keyword}'.", "success")
            return "true"
        else:
            executor.log(f"В сообщении в {chat_id} фраза '{keyword}' НЕ найдена.", "info")
            return "false"
    except Exception as e:
        executor.log(f"Ошибка проверки содержимого сообщения в {chat_id}: {e}", "error")
        return "false"

async def check_unread_count(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: не указан chat_id.", "warning")
        return "no_unread"
    try:
        chat = await executor.client.get_chat(chat_id)
        if chat.unread_messages_count and chat.unread_messages_count > 0:
            executor.log(f"В чате {chat_id} есть непрочитанные сообщения ({chat.unread_messages_count} шт).", "success")
            return "has_unread"
        else:
            executor.log(f"В чате {chat_id} нет непрочитанных сообщений.", "info")
            return "no_unread"
    except Exception as e:
        executor.log(f"Ошибка проверки непрочитанных сообщений в {chat_id}: {e}", "error")
        return "no_unread"

async def check_chat_members_count(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    threshold = int(params.get("threshold", 100))
    if not chat_id:
        executor.log("Пропуск: не указан чат.", "warning")
        return "less"
    try:
        chat = await executor.client.get_chat(chat_id)
        count = chat.members_count or 0
        if count >= threshold:
            executor.log(f"Число участников в {chat_id} ({count}) больше или равно порогу {threshold}.", "success")
            return "more"
        else:
            executor.log(f"Число участников в {chat_id} ({count}) меньше порога {threshold}.", "info")
            return "less"
    except Exception as e:
        executor.log(f"Ошибка проверки числа участников {chat_id}: {e}", "error")
        return "less"

async def check_is_pinned(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id_raw = params.get("message_id", 0)
    
    if isinstance(message_id_raw, str):
        message_id_str = executor.resolve_string(message_id_raw).strip()
        message_id = int(message_id_str) if message_id_str.isdigit() else 0
    else:
        message_id = int(message_id_raw)
        
    if not chat_id:
        executor.log("Пропуск: не указан chat_id.", "warning")
        return "not_pinned"
        
    try:
        chat = await executor.client.get_chat(chat_id)
        pinned_id = chat.pinned_message.id if chat.pinned_message else None
        
        if message_id == 0:
            if pinned_id:
                executor.log(f"В чате {chat_id} есть закрепленное сообщение (ID: {pinned_id}).", "success")
                return "pinned"
            else:
                executor.log(f"В чате {chat_id} нет закрепленных сообщений.", "info")
                return "not_pinned"
        else:
            if pinned_id == message_id:
                executor.log(f"Сообщение {message_id} закреплено в чате {chat_id}.", "success")
                return "pinned"
            else:
                executor.log(f"Сообщение {message_id} НЕ закреплено в чате {chat_id} (текущий закреп: {pinned_id}).", "info")
                return "not_pinned"
    except Exception as e:
        executor.log(f"Ошибка проверки закрепа в {chat_id}: {e}", "error")
        return "not_pinned"

async def check_profile_has_username(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        chat_id = "me"
    try:
        user = await executor.client.get_users(chat_id)
        if user.username:
            executor.log(f"У пользователя {chat_id} установлен юзернейм: @{user.username}", "success")
            return "has_username"
        else:
            executor.log(f"У пользователя {chat_id} юзернейм отсутствует.", "info")
            return "no_username"
    except Exception as e:
        executor.log(f"Ошибка проверки юзернейма профиля {chat_id}: {e}", "error")
        return "no_username"

async def check_profile_phone_visible(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        chat_id = "me"
    try:
        user = await executor.client.get_users(chat_id)
        if user.phone:
            executor.log(f"Номер телефона пользователя {chat_id} видим: {user.phone}", "success")
            return "visible"
        else:
            executor.log(f"Номер телефона пользователя {chat_id} скрыт.", "info")
            return "hidden"
    except Exception as e:
        executor.log(f"Ошибка проверки видимости телефона {chat_id}: {e}", "error")
        return "hidden"

async def check_profile_is_scam(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        chat_id = "me"
    try:
        user = await executor.client.get_users(chat_id)
        is_scam = getattr(user, "is_scam", False)
        is_fake = getattr(user, "is_fake", False)
        if is_scam or is_fake:
            executor.log(f"ВНИМАНИЕ: Пользователь {chat_id} помечен как Scam: {is_scam}, Fake: {is_fake}!", "warning")
            return "scam_or_fake"
        else:
            executor.log(f"Пользователь {chat_id} чист (без меток Scam/Fake).", "success")
            return "clean"
    except Exception as e:
        executor.log(f"Ошибка проверки меток Scam/Fake для {chat_id}: {e}", "error")
        return "clean"

async def check_profile_stories_enabled(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        chat_id = "me"
    try:
        user = await executor.client.get_users(chat_id)
        chat = await executor.client.get_chat(chat_id)
        has_stories = getattr(chat, "has_visible_stories", False) or getattr(user, "has_visible_stories", False)
        if has_stories:
            executor.log(f"У пользователя {chat_id} есть активные истории.", "success")
            return "has_stories"
        else:
            executor.log(f"У пользователя {chat_id} активные истории не найдены.", "info")
            return "no_stories"
    except Exception as e:
        executor.log(f"Ошибка проверки историй {chat_id}: {e}", "error")
        return "no_stories"

async def check_profile_is_mutual(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: не указан пользователь для проверки взаимности.", "warning")
        return "not_mutual"
    try:
        user = await executor.client.get_users(chat_id)
        is_mutual = getattr(user, "is_mutual_contact", False)
        if is_mutual:
            executor.log(f"Пользователь {chat_id} является ВЗАИМНЫМ контактом.", "success")
            return "mutual"
        else:
            executor.log(f"Пользователь {chat_id} НЕ является взаимным контактом.", "info")
            return "not_mutual"
    except Exception as e:
        executor.log(f"Ошибка проверки взаимности контакта {chat_id}: {e}", "error")
        return "not_mutual"

async def check_channel_subscription(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    user_id_str = executor.resolve_string(params.get("user_id", "")).strip()
    
    if not chat_id:
        executor.log("Пропуск: не указан чат/канал для проверки подписки.", "warning")
        return "not_subscribed"
        
    if not user_id_str or user_id_str == "me":
        me = await executor.client.get_me()
        user_id_str = me.id

    # Нормализация ссылки на канал (например: https://t.me/Imiss009 -> Imiss009)
    clean_target = chat_id
    if "t.me/" in clean_target:
        clean_target = clean_target.split("t.me/")[-1].replace("+", "").replace("joinchat/", "").strip("/")
        
    try:
        member = await executor.client.get_chat_member(clean_target, user_id_str)
        status_name = getattr(member.status, "value", str(member.status)).lower()
        if "banned" in status_name or "left" in status_name:
            executor.log(f"Пользователь НЕ подписан на канал {chat_id}.", "info")
            return "not_subscribed"
        else:
            executor.log(f"Пользователь подписан на канал {chat_id} (статус: {member.status}).", "success")
            return "subscribed"
    except Exception as e:
        # Вторая попытка по объекту чата напрямую
        try:
            chat = await executor.client.get_chat(clean_target)
            member = await executor.client.get_chat_member(chat.id, user_id_str)
            status_name = getattr(member.status, "value", str(member.status)).lower()
            if "banned" in status_name or "left" in status_name:
                executor.log(f"Пользователь НЕ подписан на канал {chat_id}.", "info")
                return "not_subscribed"
            else:
                executor.log(f"Пользователь подписан на канал {chat_id} (статус: {member.status}).", "success")
                return "subscribed"
        except Exception as err2:
            executor.log(f"Пользователь НЕ подписан на канал {chat_id} ({err2}).", "info")
            return "not_subscribed"

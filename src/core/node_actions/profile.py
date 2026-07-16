import os
import random
from hydrogram.raw.functions.account import UpdateStatus

async def get_me(executor, params):
    me = await executor.client.get_me()
    executor.variables["me_id"] = str(me.id)
    executor.variables["me_username"] = me.username or ""
    executor.variables["me_first_name"] = me.first_name or ""
    executor.log(f"Записаны переменные: me_id={me.id}, me_username=@{me.username or ''}", "success")
    return "next"

async def set_bio(executor, params):
    file_path = executor.resolve_string(params.get("file_path", "")).strip()
    if file_path:
        bio_text = await executor.get_next_line_from_file(file_path)
    else:
        bio_text = executor.resolve_string(params.get("bio_text", "")).strip()
        
    if not bio_text:
        executor.log("Пропуск: текст БИО пустой.", "warning")
        return "next"
        
    try:
        await executor.client.update_profile(bio=bio_text)
        executor.log(f"Описание профиля обновлено на: '{bio_text}'", "success")
    except Exception as e:
        executor.log(f"Ошибка обновления БИО: {e}", "error")
    return "next"

async def set_avatar(executor, params):
    avatars_dir = executor.resolve_string(params.get("avatars_dir", "")).strip()
    if not avatars_dir or not os.path.exists(avatars_dir):
        executor.log(f"Папка аватаров '{avatars_dir}' не существует!", "error")
    else:
        photos = [
            os.path.join(avatars_dir, f) 
            for f in os.listdir(avatars_dir) 
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        if not photos:
            executor.log(f"В папке '{avatars_dir}' не найдено картинок для аватара!", "warning")
        else:
            chosen_pic = random.choice(photos)
            await executor.client.set_profile_photo(photo=chosen_pic)
            executor.log(f"Установлен аватар: {os.path.basename(chosen_pic)}", "success")
    return "next"


async def add_contact(executor, params):
    phone = executor.resolve_string(params.get("phone", "")).strip()
    first_name = executor.resolve_string(params.get("first_name", "")).strip()
    if not phone or not first_name:
        executor.log("Пропуск: номер или имя пустое.", "warning")
    else:
        await executor.client.add_contact(phone_number=phone, first_name=first_name)
        executor.log(f"Контакт '{first_name}' ({phone}) добавлен.", "success")
    return "next"

async def delete_contacts(executor, params):
    user_ids_raw = executor.resolve_string(params.get("user_ids", "")).strip()
    if not user_ids_raw:
        executor.log("Пропуск: ID контактов пустые.", "warning")
    else:
        user_ids = [int(u.strip()) for u in user_ids_raw.split(",") if u.strip().isdigit()]
        await executor.client.delete_contacts(user_ids)
        executor.log(f"Успешно удалено контактов: {len(user_ids)}", "success")
    return "next"

async def block_user(executor, params):
    user_id = executor.resolve_string(params.get("user_id", "")).strip()
    if not user_id:
        executor.log("Пропуск: ID пользователя пустое.", "warning")
    else:
        await executor.client.block_user(user_id)
        executor.log(f"Пользователь {user_id} заблокирован.", "success")
    return "next"

async def unblock_user(executor, params):
    user_id = executor.resolve_string(params.get("user_id", "")).strip()
    if not user_id:
        executor.log("Пропуск: ID пользователя пустое.", "warning")
    else:
        await executor.client.unblock_user(user_id)
        executor.log(f"Пользователь {user_id} разблокирован.", "success")
    return "next"

async def get_chat(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        chat = await executor.client.get_chat(chat_id)
        executor.variables["chat_title"] = chat.title or ""
        executor.variables["chat_members_count"] = str(chat.members_count or 0)
        executor.log(f"Успешно получена информация о чате: '{chat.title}' (участников: {chat.members_count})", "success")
    return "next"

async def set_name(executor, params):
    file_path = executor.resolve_string(params.get("file_path", "")).strip()
    
    first_name = ""
    last_name = ""
    
    if file_path:
        line = await executor.get_next_line_from_file(file_path)
        if line:
            parts = line.split(",", 1)
            first_name = parts[0].strip()
            if len(parts) > 1:
                last_name = parts[1].strip()
    else:
        first_name = executor.resolve_string(params.get("first_name", "")).strip()
        last_name = executor.resolve_string(params.get("last_name", "")).strip()
        
    if not first_name:
        executor.log("Пропуск: имя не может быть пустым.", "warning")
        return "next"
        
    try:
        await executor.client.update_profile(first_name=first_name, last_name=last_name)
        executor.log(f"Имя профиля успешно обновлено на: {first_name} {last_name}", "success")
    except Exception as e:
        executor.log(f"Ошибка изменения имени: {e}", "error")
    return "next"

async def set_username(executor, params):
    file_path = executor.resolve_string(params.get("file_path", "")).strip()
    if file_path:
        username = await executor.get_next_line_from_file(file_path)
    else:
        username = executor.resolve_string(params.get("username", "")).strip()
        
    username = username.replace("@", "").strip()
    
    try:
        await executor.client.set_username(username if username else None)
        executor.log(f"Юзернейм успешно изменен на: @{username}" if username else "Юзернейм профиля удален.", "success")
    except Exception as e:
        executor.log(f"Ошибка установки юзернейма @{username}: {e}", "error")
    return "next"

async def set_privacy(executor, params):
    phone_choice = int(params.get("phone_number", 3))
    invite_choice = int(params.get("chat_invite", 2))
    status_choice = int(params.get("status_timestamp", 3))
    call_choice = int(params.get("phone_call", 2))
    
    from hydrogram import raw
    
    def map_rule(val):
        if val == 1:
            return [raw.types.InputPrivacyValueAllowAll()]
        elif val == 2:
            return [raw.types.InputPrivacyValueAllowContacts()]
        else:
            return [raw.types.InputPrivacyValueDisallowAll()]

    try:
        await executor.client.invoke(
            raw.functions.account.SetPrivacy(
                key=raw.types.InputPrivacyKeyPhoneNumber(),
                rules=map_rule(phone_choice)
            )
        )
        await executor.client.invoke(
            raw.functions.account.SetPrivacy(
                key=raw.types.InputPrivacyKeyChatInvite(),
                rules=map_rule(invite_choice)
            )
        )
        await executor.client.invoke(
            raw.functions.account.SetPrivacy(
                key=raw.types.InputPrivacyKeyStatusTimestamp(),
                rules=map_rule(status_choice)
            )
        )
        await executor.client.invoke(
            raw.functions.account.SetPrivacy(
                key=raw.types.InputPrivacyKeyPhoneCall(),
                rules=map_rule(call_choice)
            )
        )
        executor.log("Настройки конфиденциальности успешно применены.", "success")
    except Exception as e:
        executor.log(f"Ошибка настройки конфиденциальности: {e}", "error")
    return "next"

async def enable_2fa(executor, params):
    password = executor.resolve_string(params.get("password", "")).strip()
    if not password:
        executor.log("Пропуск: пароль для 2FA не указан.", "warning")
    else:
        try:
            await executor.client.enable_cloud_password(password=password)
            executor.log("Двухфакторная аутентификация (2FA) успешно включена для аккаунта.", "success")
        except Exception as e:
            executor.log(f"Ошибка установки 2FA (возможно, уже включен?): {e}", "warning")
    return "next"

async def search_contacts(executor, params):
    query = executor.resolve_string(params.get("query", "")).strip()
    limit = int(params.get("limit", 5))
    if not query:
        executor.log("Пропуск: пустой поисковый запрос.", "warning")
    else:
        try:
            results = await executor.client.search_contacts(query, limit=limit)
            if results:
                first_user = results[0]
                executor.variables["found_user_id"] = str(first_user.id)
                executor.variables["found_user_username"] = first_user.username or ""
                executor.variables["found_user_first_name"] = first_user.first_name or ""
                executor.log(f"Поиск контактов: найдено {len(results)} пользователей. Первый: {first_user.first_name} (@{first_user.username or ''})", "success")
            else:
                executor.log(f"Поиск контактов: по запросу '{query}' ничего не найдено.", "info")
        except Exception as e:
            executor.log(f"Ошибка поиска контактов: {e}", "error")
    return "next"

async def import_contacts(executor, params):
    contacts_raw = executor.resolve_string(params.get("contacts_list", "")).strip()
    if not contacts_raw:
        executor.log("Пропуск: список импорта пустой.", "warning")
    else:
        from hydrogram.types import InputPhoneContact
        contacts = []
        for line in contacts_raw.split(";"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            phone = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else "Unknown"
            contacts.append(InputPhoneContact(phone_number=phone, first_name=first_name))
            
        if contacts:
            try:
                res = await executor.client.import_contacts(contacts)
                executor.log(f"Импорт контактов: отправлено {len(contacts)}, успешно импортировано {len(res.users)} пользователей.", "success")
            except Exception as e:
                executor.log(f"Ошибка импорта контактов: {e}", "error")
        else:
            executor.log("Импорт контактов: не найдено валидных строк для импорта.", "warning")
    return "next"

async def get_common_chats(executor, params):
    user_id = executor.resolve_string(params.get("user_id", "")).strip()
    if not user_id:
        executor.log("Пропуск: ID пользователя пустой.", "warning")
    else:
        try:
            chats = await executor.client.get_common_chats(user_id)
            executor.variables["common_chats_count"] = str(len(chats))
            executor.log(f"Успешно получено общих чатов с {user_id}: {len(chats)}", "success")
        except Exception as e:
            executor.log(f"Ошибка получения общих чатов: {e}", "error")
    return "next"

async def download_profile_photos(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    download_dir = executor.resolve_string(params.get("download_dir", "downloads/avatars")).strip()
    
    if not chat_id:
        chat_id = "me"
        
    try:
        import os
        photos = []
        async for photo in executor.client.get_chat_photos(chat_id, limit=1):
            photos.append(photo)
            
        if photos:
            os.makedirs(download_dir, exist_ok=True)
            file_path = await executor.client.download_media(photos[0].file_id, file_name=os.path.join(download_dir, ""))
            executor.variables["downloaded_avatar_path"] = file_path
            executor.log(f"Аватарка пользователя {chat_id} успешно скачана: {file_path}", "success")
        else:
            executor.variables["downloaded_avatar_path"] = ""
            executor.log(f"У пользователя {chat_id} нет аватарок для скачивания.", "info")
    except Exception as e:
        executor.variables["downloaded_avatar_path"] = ""
        executor.log(f"Ошибка скачивания аватарки {chat_id}: {e}", "error")
    return "next"

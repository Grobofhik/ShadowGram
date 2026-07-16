import os
import random

async def send_message(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    file_path = executor.resolve_string(params.get("file_path", "")).strip()
    
    if file_path:
        text = await executor.get_next_line_from_file(file_path)
    else:
        text = executor.resolve_string(params.get("text", "")).strip()
        
    if not chat_id or not text:
        executor.log("Пропуск: chat_id или text не заполнены.", "warning")
    else:
        from hydrogram.enums import ChatAction
        try:
            await executor.client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass
        typing_duration = min(7, max(2, len(text) // 40))
        executor.log(f"Имитация ввода сообщения в {chat_id} ({typing_duration} сек)...", "info")
        await executor.sleep(typing_duration)
        
        res = await executor.client.send_message(chat_id, text)
        executor.log(f"Сообщение успешно отправлено в {chat_id} (msg_id: {res.id})", "success")
    return "next"

async def send_photo(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    photo_path = executor.resolve_string(params.get("photo_path", "")).strip()
    caption = executor.resolve_string(params.get("caption", "")).strip()
    if not chat_id or not photo_path or not os.path.exists(photo_path):
        executor.log(f"Пропуск: chat_id пустой или файл изображения '{photo_path}' не найден.", "warning")
    else:
        from hydrogram.enums import ChatAction
        try:
            await executor.client.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
        except Exception:
            pass
        await executor.sleep(random.randint(2, 4))
        
        await executor.client.send_photo(chat_id, photo_path, caption=caption)
        executor.log(f"Фото отправлено в {chat_id}", "success")
    return "next"

async def send_video(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    video_path = executor.resolve_string(params.get("video_path", "")).strip()
    caption = executor.resolve_string(params.get("caption", "")).strip()
    if not chat_id or not video_path or not os.path.exists(video_path):
        executor.log(f"Пропуск: chat_id пустой или видеофайл '{video_path}' не найден.", "warning")
    else:
        from hydrogram.enums import ChatAction
        try:
            await executor.client.send_chat_action(chat_id, ChatAction.UPLOAD_VIDEO)
        except Exception:
            pass
        await executor.sleep(random.randint(3, 5))
        
        await executor.client.send_video(chat_id, video_path, caption=caption)
        executor.log(f"Видео отправлено в {chat_id}", "success")
    return "next"

async def send_document(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    file_path = executor.resolve_string(params.get("file_path", "")).strip()
    caption = executor.resolve_string(params.get("caption", "")).strip()
    if not chat_id or not file_path or not os.path.exists(file_path):
        executor.log(f"Пропуск: chat_id пустой или файл '{file_path}' не найден.", "warning")
    else:
        from hydrogram.enums import ChatAction
        try:
            await executor.client.send_chat_action(chat_id, ChatAction.UPLOAD_DOCUMENT)
        except Exception:
            pass
        await executor.sleep(random.randint(2, 4))
        
        await executor.client.send_document(chat_id, file_path, caption=caption)
        executor.log(f"Документ отправлен в {chat_id}", "success")
    return "next"

async def forward_messages(executor, params):
    from_chat_id = executor.resolve_string(params.get("from_chat_id", "")).strip()
    to_chat_id = executor.resolve_string(params.get("to_chat_id", "")).strip()
    msg_ids_raw = executor.resolve_string(params.get("message_ids", "")).strip()
    if not from_chat_id or not to_chat_id or not msg_ids_raw:
        executor.log("Пропуск: не заполнены параметры пересылки.", "warning")
    else:
        message_ids = [int(m.strip()) for m in msg_ids_raw.split(",") if m.strip().isdigit()]
        await executor.client.forward_messages(to_chat_id, from_chat_id, message_ids)
        executor.log(f"Переслано сообщений: {len(message_ids)} в {to_chat_id}", "success")
    return "next"

async def edit_message_text(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id = int(params.get("message_id", 0))
    new_text = executor.resolve_string(params.get("new_text", "")).strip()
    if not chat_id or message_id == 0 or not new_text:
        executor.log("Пропуск: не заполнены параметры редактирования.", "warning")
    else:
        await executor.client.edit_message_text(chat_id, message_id, new_text)
        executor.log(f"Сообщение {message_id} в {chat_id} отредактировано.", "success")
    return "next"

async def delete_messages(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    msg_ids_raw = executor.resolve_string(params.get("message_ids", "")).strip()
    if not chat_id or not msg_ids_raw:
        executor.log("Пропуск: не заполнены параметры удаления.", "warning")
    else:
        message_ids = [int(m.strip()) for m in msg_ids_raw.split(",") if m.strip().isdigit()]
        await executor.client.delete_messages(chat_id, message_ids)
        executor.log(f"Удалено сообщений: {len(message_ids)} в {chat_id}", "success")
    return "next"

async def send_sticker(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    sticker = executor.resolve_string(params.get("sticker", "")).strip()
    if not chat_id or not sticker:
        executor.log("Пропуск: chat_id или стикер не указаны.", "warning")
    else:
        await executor.client.send_sticker(chat_id, sticker)
        executor.log(f"Стикер {sticker} успешно отправлен в {chat_id}", "success")
    return "next"

async def send_reaction(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id = int(params.get("message_id", 0))
    reaction = executor.resolve_string(params.get("reaction", "👍")).strip()
    if not chat_id or message_id == 0:
        executor.log("Пропуск: неверные параметры реакции.", "warning")
    else:
        await executor.client.send_reaction(chat_id, message_id, reaction)
        executor.log(f"Поставлена реакция {reaction} на сообщение {message_id} в {chat_id}", "success")
    return "next"

async def send_story(executor, params):
    media_path = executor.resolve_string(params.get("media_path", "")).strip()
    caption = executor.resolve_string(params.get("caption", "")).strip()
    if not media_path or not os.path.exists(media_path):
        executor.log(f"Пропуск: файл истории '{media_path}' не найден.", "warning")
    else:
        # In Pyrogram/Hydrogram, sending stories is done via client.send_story:
        await executor.client.send_story(chat_id="me", media=media_path, caption=caption)
        executor.log(f"История '{os.path.basename(media_path)}' успешно опубликована", "success")
    return "next"

async def send_voice(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    voice_path = executor.resolve_string(params.get("voice_path", "")).strip()
    if not chat_id or not voice_path or not os.path.exists(voice_path):
        executor.log(f"Пропуск: chat_id пустой или голосовой файл '{voice_path}' не найден.", "warning")
    else:
        from hydrogram.enums import ChatAction
        try:
            # Имитируем запись голосового
            await executor.client.send_chat_action(chat_id, ChatAction.RECORD_AUDIO)
        except Exception:
            pass
        await executor.sleep(random.randint(3, 6))
        
        await executor.client.send_voice(chat_id, voice_path)
        executor.log(f"Голосовое сообщение отправлено в {chat_id}", "success")
    return "next"

async def send_audio(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    audio_path = executor.resolve_string(params.get("audio_path", "")).strip()
    caption = executor.resolve_string(params.get("caption", "")).strip()
    if not chat_id or not audio_path or not os.path.exists(audio_path):
        executor.log(f"Пропуск: chat_id пустой или аудиофайл '{audio_path}' не найден.", "warning")
    else:
        from hydrogram.enums import ChatAction
        try:
            await executor.client.send_chat_action(chat_id, ChatAction.UPLOAD_AUDIO)
        except Exception:
            pass
        await executor.sleep(random.randint(3, 5))
        
        await executor.client.send_audio(chat_id, audio_path, caption=caption)
        executor.log(f"Аудиофайл отправлен в {chat_id}", "success")
    return "next"

async def send_gif(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    gif_path = executor.resolve_string(params.get("gif_path", "")).strip()
    caption = executor.resolve_string(params.get("caption", "")).strip()
    if not chat_id or not gif_path or not os.path.exists(gif_path):
        executor.log(f"Пропуск: chat_id пустой или GIF-файл '{gif_path}' не найден.", "warning")
    else:
        from hydrogram.enums import ChatAction
        try:
            await executor.client.send_chat_action(chat_id, ChatAction.UPLOAD_VIDEO)
        except Exception:
            pass
        await executor.sleep(random.randint(2, 4))
        
        await executor.client.send_animation(chat_id, gif_path, caption=caption)
        executor.log(f"GIF-анимация отправлена в {chat_id}", "success")
    return "next"

async def send_location(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    lat_str = executor.resolve_string(params.get("latitude", "55.7558")).strip()
    lon_str = executor.resolve_string(params.get("longitude", "37.6173")).strip()
    if not chat_id or not lat_str or not lon_str:
        executor.log("Пропуск: не заполнены параметры локации.", "warning")
    else:
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            
            from hydrogram.enums import ChatAction
            try:
                await executor.client.send_chat_action(chat_id, ChatAction.FIND_LOCATION)
            except Exception:
                pass
            await executor.sleep(random.randint(1, 3))
            
            await executor.client.send_location(chat_id, lat, lon)
            executor.log(f"Геопозиция ({lat}, {lon}) успешно отправлена в {chat_id}", "success")
        except ValueError:
            executor.log(f"Ошибка: Неверный формат координат ({lat_str}, {lon_str})", "error")
    return "next"

async def search_messages(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    query = executor.resolve_string(params.get("query", "")).strip()
    limit = int(params.get("limit", 5))
    if not chat_id or not query:
        executor.log("Пропуск: chat_id или поисковый запрос пустые.", "warning")
    else:
        try:
            results = []
            async for msg in executor.client.search_messages(chat_id, query=query, limit=limit):
                if msg.text:
                    results.append(msg.text)
            if results:
                executor.variables["found_message_text"] = results[0]
                executor.log(f"Поиск сообщений: найдено {len(results)} сообщений по запросу '{query}' в {chat_id}.", "success")
            else:
                executor.log(f"Поиск сообщений: по запросу '{query}' в чате {chat_id} ничего не найдено.", "info")
        except Exception as e:
            executor.log(f"Ошибка поиска сообщений: {e}", "error")
    return "next"

async def send_dice(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    emoji = executor.resolve_string(params.get("emoji", "🎲")).strip()
    if not chat_id:
        executor.log("Пропуск: ID чата пустой.", "warning")
    else:
        try:
            res = await executor.client.send_dice(chat_id, emoji=emoji)
            executor.variables["dice_value"] = str(res.dice.value)
            executor.log(f"Игра '{emoji}' отправлена в {chat_id}. Выпало значение: {res.dice.value}", "success")
        except Exception as e:
            executor.log(f"Ошибка отправки игры '{emoji}': {e}", "error")
    return "next"

async def send_poll(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    question = executor.resolve_string(params.get("question", "")).strip()
    options_raw = executor.resolve_string(params.get("options", "")).strip()
    is_anonymous = params.get("is_anonymous", "true").lower() == "true"
    
    options = [opt.strip() for opt in options_raw.split(",") if opt.strip()]
    if not chat_id or not question or len(options) < 2:
        executor.log("Пропуск: не заполнены обязательные параметры опроса.", "warning")
        return "next"
        
    try:
        await executor.client.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            is_anonymous=is_anonymous
        )
        executor.log(f"Опрос '{question}' успешно отправлен в {chat_id}.", "success")
    except Exception as e:
        executor.log(f"Ошибка отправки опроса: {e}", "error")
    return "next"

async def save_draft(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    text = executor.resolve_string(params.get("text", "")).strip()
    
    if not chat_id or not text:
        executor.log("Пропуск: пустой ID чата или текст черновика.", "warning")
        return "next"
        
    try:
        # In Pyrogram/Hydrogram, you can set a draft by calling client.set_draft
        await executor.client.set_draft(chat_id, text)
        executor.log(f"Черновик успешно сохранен в чате {chat_id}.", "success")
    except Exception as e:
        executor.log(f"Ошибка сохранения черновика в {chat_id}: {e}", "error")
    return "next"

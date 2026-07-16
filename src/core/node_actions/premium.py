import re
import random
from hydrogram.types import MessageEntity
from hydrogram.enums import MessageEntityType, ChatAction
from hydrogram import raw

async def send_premium_message(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    text = executor.resolve_string(params.get("text", "")).strip()
    if not chat_id or not text:
        executor.log("Пропуск: chat_id или текст пустые.", "warning")
        return "next"
        
    try:
        await executor.client.send_chat_action(chat_id, ChatAction.TYPING)
    except Exception:
        pass
    await executor.sleep(max(1, len(text) * 0.05 + random.uniform(0.5, 1.5)))
    
    try:
        pattern = re.compile(r":(\d+):")
        entities = []
        new_text = ""
        last_idx = 0
        
        for m in pattern.finditer(text):
            new_text += text[last_idx:m.start()]
            offset = len(new_text)
            new_text += "⭐"
            entities.append(MessageEntity(
                type=MessageEntityType.CUSTOM_EMOJI,
                offset=offset,
                length=1,
                custom_emoji_id=int(m.group(1))
            ))
            last_idx = m.end()
            
        new_text += text[last_idx:]
        
        await executor.client.send_message(
            chat_id=chat_id,
            text=new_text,
            entities=entities if entities else None
        )
        executor.log(f"Премиум сообщение успешно отправлено в {chat_id}.", "success")
    except Exception as e:
        executor.log(f"Ошибка отправки премиум сообщения: {e}", "error")
    return "next"

async def send_premium_reaction(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id_str = executor.resolve_string(str(params.get("message_id", "0"))).strip()
    reactions_raw = executor.resolve_string(params.get("reactions", "")).strip()
    if not chat_id or not message_id_str or not reactions_raw:
        executor.log("Пропуск: не заполнены обязательные параметры реакции.", "warning")
        return "next"
        
    try:
        message_id = int(message_id_str)
        from hydrogram.types import ReactionTypeEmoji, ReactionTypeCustomEmoji
        
        reactions_list = []
        for r in reactions_raw.split(","):
            r = r.strip()
            if not r:
                continue
            if r.isdigit():
                reactions_list.append(ReactionTypeCustomEmoji(custom_emoji_id=int(r)))
            else:
                reactions_list.append(ReactionTypeEmoji(emoji=r))
                
        if reactions_list:
            await executor.client.send_reaction(
                chat_id=chat_id,
                message_id=message_id,
                emoji=reactions_list
            )
            executor.log(f"Успешно установлены премиум-реакции на сообщение {message_id} в {chat_id}.", "success")
        else:
            executor.log("Премиум-реакция: не найдено валидных эмодзи/ID.", "warning")
    except Exception as e:
        executor.log(f"Ошибка отправки премиум-реакции: {e}", "error")
    return "next"

async def set_emoji_status(executor, params):
    custom_emoji_id_str = executor.resolve_string(params.get("custom_emoji_id", "")).strip()
    
    try:
        if custom_emoji_id_str:
            emoji_id = int(custom_emoji_id_str)
            await executor.client.invoke(
                raw.functions.account.UpdateEmojiStatus(
                    emoji_status=raw.types.EmojiStatus(document_id=emoji_id)
                )
            )
            executor.log(f"Эмодзи-статус успешно изменен на ID: {emoji_id}", "success")
        else:
            await executor.client.invoke(
                raw.functions.account.UpdateEmojiStatus(
                    emoji_status=raw.types.EmojiStatusEmpty()
                )
            )
            executor.log("Эмодзи-статус успешно удален.", "success")
    except Exception as e:
        executor.log(f"Ошибка изменения эмодзи-статуса: {e}", "error")
    return "next"

import asyncio
from hydrogram import Client
from src.core.logger import logger


async def run(client: Client, params: dict, context: dict) -> bool:
    """
    Воркер: Пишет осмысленный комментарий под последним постом канала.
    """
    try:
        me = await client.get_me()
        channel_link = params.get("channel")
        prompt = params.get("prompt", "Прокомментируй этот пост коротко и по теме")
        
        if not channel_link:
            logger.warning(f"[{me.first_name}] Воркеру task_comment не передали параметр channel")
            return False

        target = channel_link.strip().replace(" ", "")
        if target.startswith("@"):
            target = target[1:]
        elif "t.me/" in target:
            target = target.split("t.me/")[-1].strip("/")
            
        logger.info(f"[{me.first_name}] Воркер task_comment запущен для канала @{target}.")

        # 1. Получаем инфо о канале
        try:
            chat = await client.get_chat(target)
            if not chat.linked_chat:
                logger.warning(f"[{me.first_name}] ❌ Канал @{target} не имеет привязанного чата для комментариев.")
                return False
                
            discussion_group_id = chat.linked_chat.id
        except Exception as e:
            logger.error(f"[{me.first_name}] Не удалось получить чат @{target}: {e}")
            return False

        # 2. Получаем последний пост
        posts = []
        async for msg in client.get_chat_history(chat.id, limit=1):
            posts.append(msg)
            
        if not posts:
            logger.warning(f"[{me.first_name}] В канале @{target} нет постов.")
            return False
            
        last_post = posts[0]
        post_text = last_post.text or last_post.caption or "(Пост с медиа без текста)"

        # 3. Генерируем комментарий через LLM (используем context.api_key)
        logger.info(f"[{me.first_name}] Генерируем комментарий через LLM...")
        
        import requests
        api_key = context.get("api_key")
        api_base_url = context.get("api_base_url", "https://api.groq.com/openai/v1").rstrip("/")
        model = context.get("model_name", "llama-3.1-8b-instant")
        
        if not api_key:
            logger.error(f"[{me.first_name}] Нет API ключа для генерации комментария.")
            return False

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": f"Ты живой пользователь Telegram. {prompt}. Не используй хештеги. Максимум 2 предложения."},
                {"role": "user", "content": f"Пост:\n{post_text}"}
            ],
            "temperature": 0.7
        }
        
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: requests.post(f"{api_base_url}/chat/completions", headers=headers, json=payload, timeout=15)
        )
        
        if response.status_code == 200:
            data = response.json()
            comment_text = data['choices'][0]['message']['content'].strip()
            
            # 4. Получаем message_id в группе обсуждения, к которому нужно сделать reply
            discussion_msg = await client.get_discussion_message(chat.id, last_post.id)
            
            # 5. Имитируем набор текста
            await client.send_chat_action(discussion_group_id, "typing")
            await asyncio.sleep(len(comment_text) * 0.1) # Чем длиннее, тем дольше печатаем
            
            # 6. Отправляем комментарий
            await client.send_message(
                chat_id=discussion_group_id,
                text=comment_text,
                reply_to_message_id=discussion_msg.id
            )
            logger.info(f"[{me.first_name}] ✅ Оставлен комментарий: {comment_text}")
            return True
        else:
            logger.error(f"[{me.first_name}] Ошибка API при генерации комментария: {response.text}")
            return False

    except Exception as e:
        logger.error(f"Ошибка в task_comment: {e}")
        return False

from hydrogram import Client
from src.core.logger import logger
from src.ai_agents.brain.specialists.channel_agent import NamingAgent

async def run(client: Client, params: dict, context: dict) -> bool:
    """
    Микро-воркер: Создает личный канал для аккаунта.
    Генерирует название и описание через NamingAgent.
    """
    channel_name = params.get("channel_name")
    channel_desc = params.get("channel_desc", "")
    
    if not channel_name:
        # Обращаемся к ИИ-Креативщику
        generated = NamingAgent.generate(
            api_key=context.get("api_key"),
            api_base_url=context.get("api_base_url"),
            model_name=context.get("model_name")
        )
        channel_name = generated.get("channel_name", "My Crypto Journal")
        channel_desc = generated.get("channel_desc", "")
    
    try:
        logger.info(f"[{client.name}] Создаем личный канал: '{channel_name}'")
        chat = await client.create_channel(title=channel_name, description=channel_desc)
        logger.info(f"[{client.name}] Канал успешно создан! ID: {chat.id}")
        return True
    except Exception as e:
        logger.error(f"[{client.name}] Ошибка создания канала: {e}")
        return False

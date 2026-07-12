from hydrogram import Client
from src.core.logger import logger
from src.ai_agents.brain.specialists.bio_agent import BioAgent

async def run(client: Client, params: dict, context: dict) -> bool:
    """
    Микро-воркер: Устанавливает описание (био) профиля.
    Генерирует текст через BioAgent.
    """
    bio_text = params.get("bio_text")
    
    if not bio_text:
        # Обращаемся к узкоспециализированному ИИ
        bio_text = BioAgent.generate(
            api_key=context.get("api_key"),
            api_base_url=context.get("api_base_url"),
            model_name=context.get("model_name")
        )
        
    try:
        logger.info(f"[{client.name}] Устанавливаем био: {bio_text}")
        await client.update_profile(bio=bio_text)
        return True
    except Exception as e:
        logger.error(f"[{client.name}] Ошибка установки био: {e}")
        return False

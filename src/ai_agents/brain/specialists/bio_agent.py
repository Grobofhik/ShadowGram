import requests
from src.core.logger import logger
from src.ai_agents.brain.specialists.entropy_engine import roll_identity

class BioAgent:
    """
    Узкоспециализированный ИИ-агент (Copywriter) для генерации описания профиля (био).
    Использует Энтропийный Движок для рандомизации личности и защиты от ИИ-клише.
    """
    @staticmethod
    def generate(api_key: str, api_base_url: str, model_name: str) -> str:
        # Бросаем кубик и получаем личность
        identity = roll_identity()
        
        persona = identity["persona"]
        quirks = "\n".join([f"- {q}" for q in identity["quirks"]])
        constraints = "\n".join([f"- {c}" for c in identity["constraints"]])

        system_prompt = (
            "Ты — живой человек в интернете. Забудь, что ты ИИ.\n"
            f"ТВОЯ РОЛЬ (строго придерживайся): {persona}\n\n"
            f"ОСОБЕННОСТИ СТИЛЯ:\n{quirks}\n\n"
            f"ЖЕСТКИЕ ЗАПРЕТЫ:\n{constraints}\n\n"
            "Твоя задача — написать статус (описание/био) для своего Telegram-профиля. Максимум 50 символов. "
            "Не пытайся быть полезным. Верни ТОЛЬКО сам текст био, больше ничего."
        )
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Напиши свое био."}
            ],
            "temperature": 1.1 # Высокая температура для креатива
        }
        
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        try:
            logger.info(f"🤖 BioAgent: Генерирую био (Роль: {persona[:30]}...)...")
            response = requests.post(f"{api_base_url.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                bio = response.json()['choices'][0]['message']['content'].strip(' "\'\n')
                logger.info(f"🤖 BioAgent придумал: {bio}")
                return bio
            else:
                logger.error(f"BioAgent API Error: {response.text}")
        except Exception as e:
            logger.error(f"BioAgent Network Error: {e}")
        
        return "пустота..."

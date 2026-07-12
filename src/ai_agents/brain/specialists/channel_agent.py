import json
import requests
from src.core.logger import logger
from src.ai_agents.brain.specialists.entropy_engine import roll_identity

class NamingAgent:
    """
    Узкоспециализированный ИИ-агент для придумывания названия и описания личных каналов.
    С защитой от "ИИ-шаблонов" и использованием Энтропийного Движка.
    """
    @staticmethod
    def generate(api_key: str, api_base_url: str, model_name: str) -> dict:
        identity = roll_identity()
        
        persona = identity["persona"]
        quirks = "\n".join([f"- {q}" for q in identity["quirks"]])
        constraints = "\n".join([f"- {c}" for c in identity["constraints"]])

        system_prompt = (
            "Ты — живой человек в интернете. Забудь, что ты ИИ.\n"
            f"ТВОЯ РОЛЬ (строго придерживайся): {persona}\n\n"
            f"ОСОБЕННОСТИ СТИЛЯ:\n{quirks}\n\n"
            f"ЖЕСТКИЕ ЗАПРЕТЫ:\n{constraints}\n\n"
            "Твоя задача — придумать название и описание для твоего личного Telegram-канала.\n"
            "Не будь банальным. Сделай название и описание живыми, странными, кринжовыми или забавными.\n"
            "ВЫВЕДИ СТРОГО JSON-ОБЪЕКТ и больше ничего. Пример формата:\n"
            "{\n"
            '  "channel_name": "текст",\n'
            '  "channel_desc": "текст"\n'
            "}"
        )
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Создай канал."}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 1.1 # Высокая креативность
        }
        
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        default_result = {"channel_name": "dump", "channel_desc": "..."}
        
        try:
            logger.info(f"🤖 NamingAgent: Придумываю канал (Роль: {persona[:30]}...)...")
            response = requests.post(f"{api_base_url.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content'].strip()
                if content.startswith("```json"): content = content[7:]
                if content.startswith("```"): content = content[3:]
                if content.endswith("```"): content = content[:-3]
                
                result = json.loads(content.strip())
                logger.info(f"🤖 NamingAgent придумал: {result.get('channel_name', 'Без названия')}")
                return result
            else:
                logger.error(f"NamingAgent API Error: {response.text}")
        except Exception as e:
            logger.error(f"NamingAgent Network Error: {e}")
        
        return default_result

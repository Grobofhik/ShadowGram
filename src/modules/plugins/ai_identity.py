import json
import asyncio
from typing import Any
import requests
from src.core.base_module import BaseModule

class AIIdentityPlugin(BaseModule):
    MODULE_NAME: str = "🧠 AI Identity (Генератор личностей)"
    MODULE_DESC: str = "Генерирует и устанавливает уникальное имя, фамилию и био для аккаунта с помощью нейросети по заданной тематике."
    SINGLE_ACCOUNT: bool = False
    
    PARAMS = [
        {"name": "persona_prompt", "type": "textarea", "label": "Тематика аккаунта (например: '25-летний криптоинвестор из Москвы, любит машины')"},
        {"name": "api_key", "type": "text", "label": "API Ключ (Groq/OpenRouter/OpenAI)"},
        {"name": "api_base_url", "type": "text", "label": "Base URL API"},
        {"name": "model_name", "type": "text", "label": "Название модели"}
    ]

    async def run(self, **kwargs: Any) -> None:
        prompt = kwargs.get("persona_prompt", "Обычный парень из СНГ, 25 лет")
        api_key = kwargs.get("api_key", "")
        api_url = kwargs.get("api_base_url", "https://api.groq.com/openai/v1")
        model = kwargs.get("model_name", "llama-3.1-8b-instant")
        
        if not api_key:
            self.log("Не указан API ключ для ИИ!", "error")
            return

        if not await self.init_client():
            return

        self.log(f"🧠 Генерируем личность под тематику: '{prompt}'...", "info")
        
        system_prompt = """Ты генератор реалистичных личностей для Telegram.
Пользователь передаст тебе тематику.
Тебе нужно придумать имя, фамилию (на языке, соответствующем тематике, по умолчанию русский) и короткое био (максимум 70 символов).
ВЕРНИ ТОЛЬКО JSON В СТРОГОМ ФОРМАТЕ, БЕЗ МАРКДАУНА, БЕЗ ПОЯСНЕНИЙ:
{"first_name": "Имя", "last_name": "Фамилия", "bio": "Текст био"}"""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Тематика: {prompt}"}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.9
        }
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(f"{api_url}/chat/completions", headers=headers, json=payload, timeout=15)
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                # Попробуем вытащить JSON если ИИ все же добавил маркдаун
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].strip()
                    
                identity = json.loads(content)
                first_name = identity.get("first_name", "User")
                last_name = identity.get("last_name", "")
                bio = identity.get("bio", "")
                
                self.log(f"Сгенерировано: Имя: {first_name} {last_name}, Био: {bio}", "success")
                
                self.log("Применяем к профилю Telegram...", "info")
                await self.client.update_profile(first_name=first_name, last_name=last_name, bio=bio)
                self.log("Личность успешно обновлена!", "success")
                
            else:
                self.log(f"Ошибка API: {response.status_code} - {response.text}", "error")
                
        except json.JSONDecodeError:
            self.log("ИИ вернул невалидный JSON.", "error")
        except Exception as e:
            self.log(f"Ошибка генерации личности: {e}", "error")
        finally:
            await self.cleanup()

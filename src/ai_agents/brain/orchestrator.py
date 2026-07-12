import os
import sys
import json
import requests
import asyncio
import time
from pathlib import Path

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.core.managers import config_manager
from src.core.constants import CONFIG_FILE
from src.core.logger import logger
from src.ai_agents.brain.schemas import get_assistant_prompt

class AIOrchestrator:
    """
    Интерактивный Мозг фермы (Фаза 2). 
    Принимает команды пользователя и состояние фермы, общается через чат и генерирует план.
    """
    def __init__(self, api_key: str, api_base_url: str = None, model_name: str = None):
        self.api_key = api_key
        # По умолчанию используем Gemini (через совместимый endpoint) или Groq
        # Если передан Gemini ключ, настроим URL
        if not api_base_url and self.api_key.startswith("AIza"):
            self.api_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            self.model_name = "gemini-2.5-flash"
        else:
            self.api_base_url = (api_base_url or "https://api.groq.com/openai/v1").rstrip("/")
            self.model_name = model_name or "llama-3.1-8b-instant"
            
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat_with_agent(self, user_message: str, farm_state: dict) -> tuple[str, list, list]:
        """
        Отправляет запрос в LLM и возвращает (ответ_ассистента, сгенерированный_план, мутации_конфига).
        """
        system_instruction = get_assistant_prompt()
        
        # Фильтруем стейт, чтобы не превысить лимиты токенов
        active_state = {}
        for k, v in farm_state.items():
            if v.get("status") == "active":
                active_state[k] = {
                    "phone": v.get("phone"),
                    "has_proxy": v.get("has_proxy"),
                    "device_info_set": v.get("device_info_set"),
                    "has_avatar": v.get("has_avatar"),
                    "username": v.get("username"),
                    "bio": v.get("bio"),
                    "has_2fa": v.get("has_2fa"),
                    "privacy_setup": v.get("privacy_setup"),
                    "has_personal_channel": v.get("has_personal_channel")
                }
        
        state_json = json.dumps(active_state, ensure_ascii=False)
        
        full_user_content = f"Текущее состояние фермы:\n{state_json}\n\nКоманда пользователя:\n{user_message}"
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": full_user_content}
            ],
            "temperature": 0.4
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    logger.info(f"Отправляем запрос к ИИ-Оркестратору (Модель: {self.model_name})...")
                else:
                    logger.info(f"Повторная попытка запроса к ИИ-Оркестратору ({attempt + 1}/{max_retries})...")
                
                response = requests.post(f"{self.api_base_url}/chat/completions", headers=self.headers, json=payload, timeout=300)
                
                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content'].strip()
                    
                    # Очистка маркдауна JSON
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                        
                    content = content.strip()
                    
                    try:
                        parsed_response = json.loads(content, strict=False)
                        bot_msg = parsed_response.get("message", "План готов.")
                        bot_plan = parsed_response.get("plan", [])
                        bot_mutations = parsed_response.get("config_mutations", [])
                        return bot_msg, bot_plan, bot_mutations
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка парсинга JSON от ИИ: {e}\nСырой ответ: {content}")
                        return "Произошла ошибка при генерации ответа. ИИ вернул неверный формат.", [], []
                        
                elif response.status_code in [429, 503]:
                    logger.warning(f"API перегружено или лимит исчерпан ({response.status_code}). Ждем перед повторной попыткой...")
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))
                        continue
                    else:
                        logger.error(f"Ошибка API ({response.status_code}): {response.text}")
                        return f"Ошибка API: {response.status_code} (Сервер перегружен)", [], []
                else:
                    logger.error(f"Ошибка API ({response.status_code}): {response.text}")
                    return f"Ошибка API: {response.status_code}", [], []
                    
            except Exception as e:
                logger.error(f"Сетевая ошибка при обращении к ИИ: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                return "Ошибка сети при обращении к ИИ.", [], []

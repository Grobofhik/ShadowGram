import os
import json
import random
import string
from pathlib import Path
from hydrogram import Client
from src.core.logger import logger

async def run(client: Client, params: dict, context: dict) -> bool:
    """
    Микро-воркер: Устанавливает Облачный пароль (2FA), если его нет.
    Генерирует случайный пароль и сохраняет его в config.json аккаунта.
    Параметры не требуются.
    """
    try:
        # Генерируем надежный 12-значный пароль
        chars = string.ascii_letters + string.digits
        new_pass = ''.join(random.choices(chars, k=12))
        
        logger.info(f"[{client.name}] Пытаемся установить 2FA пароль...")
        
        # Hydrogram метод для включения пароля
        await client.enable_cloud_password(password=new_pass)
        logger.info(f"[{client.name}] 2FA пароль успешно установлен!")
        
        # Сохраняем пароль в конфиг самого аккаунта
        if hasattr(client, "workdir") and client.workdir:
            cfg_path = Path(client.workdir) / "config.json"
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                data["cloud_password"] = new_pass
                
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                    
        return True
    except Exception as e:
        logger.error(f"[{client.name}] Ошибка установки 2FA (возможно, уже установлен?): {e}")
        return False

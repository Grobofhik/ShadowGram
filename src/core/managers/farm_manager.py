import os
import json
import uuid
import shutil
import urllib.request
import subprocess
import time
import zipfile
import string
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from src.core.constants import *
from src.core.logger import logger

def get_active_farm_name() -> str:
    """Возвращает имя текущей активной фермы"""
    if not ACTIVE_FARM_FILE.exists():
        return "default"
    try:
        return ACTIVE_FARM_FILE.read_text(encoding="utf-8").strip()
    except:
        return "default"


def get_active_farm_dir() -> Path:
    """Возвращает путь к папке текущей активной фермы"""
    farm_name = get_active_farm_name()
    farm_dir = FARMS_DIR / farm_name
    farm_dir.mkdir(parents=True, exist_ok=True)
    (farm_dir / "accounts").mkdir(parents=True, exist_ok=True)
    return farm_dir


def save_active_farm_config():
    """Синхронизирует root config.json с активной фермой"""
    try:
        active_farm = get_active_farm_name()
        farm_dir = FARMS_DIR / active_farm
        farm_dir.mkdir(parents=True, exist_ok=True)
        farm_config = farm_dir / "config.json"
        if CONFIG_FILE.exists():
            shutil.copy2(CONFIG_FILE, farm_config)
    except Exception as e:
        logger.error(f"Ошибка синхронизации конфига фермы: {e}")


def init_farms():
    """Инициализация директорий ферм на старте приложения"""
    try:
        FARMS_DIR.mkdir(parents=True, exist_ok=True)
        AVATARS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Если нет файла активной фермы
        if not ACTIVE_FARM_FILE.exists():
            ACTIVE_FARM_FILE.write_text("default", encoding="utf-8")
            
        active_farm = get_active_farm_name()
        active_farm_dir = FARMS_DIR / active_farm
        active_farm_dir.mkdir(parents=True, exist_ok=True)
        (active_farm_dir / "accounts").mkdir(parents=True, exist_ok=True)
        
        farm_config = active_farm_dir / "config.json"
        
        # Миграция старого конфига
        if active_farm == "default" and not farm_config.exists() and CONFIG_FILE.exists():
            shutil.copy2(CONFIG_FILE, farm_config)
        
        # Если конфига фермы всё еще нет — создаем дефолтный
        if not farm_config.exists():
            default_config = {"settings": {"api_id": 0, "api_hash": ""}, "accounts": []}
            with open(farm_config, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
                
        # На старте всегда копируем конфиг активной фермы в корень
        shutil.copy2(farm_config, CONFIG_FILE)
        
        # Обновляем SQLite зеркало
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        from src.core.managers.db_manager import mirror_to_sqlite
        mirror_to_sqlite(CONFIG_FILE, data)
        
    except Exception as e:
        logger.error(f"Ошибка инициализации ферм: {e}")


def list_available_farms() -> List[str]:
    """Возвращает список имен всех доступных ферм"""
    if not FARMS_DIR.exists():
        return ["default"]
    farms = [d.name for d in FARMS_DIR.iterdir() if d.is_dir()]
    if not farms:
        return ["default"]
    return sorted(farms)


def create_new_farm(name: str) -> bool:
    """Создает новую ферму с текущими общими настройками, но без аккаунтов"""
    name = name.strip()
    if not name or "/" in name or "\\" in name:
        return False
    farm_dir = FARMS_DIR / name
    if farm_dir.exists():
        return False
        
    try:
        farm_dir.mkdir(parents=True, exist_ok=True)
        (farm_dir / "accounts").mkdir(parents=True, exist_ok=True)
        
        # Копируем текущие настройки (без аккаунтов)
        settings = {}
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f).get("settings", {})
            except:
                pass
                
        default_config = {
            "settings": settings,
            "accounts": []
        }
        
        with open(farm_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Ошибка создания фермы: {e}")
        return False


def switch_active_farm(name: str) -> bool:
    """Переключает активную ферму"""
    name = name.strip()
    farm_config = FARMS_DIR / name / "config.json"
    if not farm_config.exists():
        return False
        
    try:
        # 1. Сохраняем текущую активную ферму
        save_active_farm_config()
        
        # 2. Переключаем имя в файле
        ACTIVE_FARM_FILE.write_text(name, encoding="utf-8")
        
        # 3. Копируем новый конфиг в корень
        shutil.copy2(farm_config, CONFIG_FILE)
        
        # 4. Обновляем SQLite зеркало
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        from src.core.managers.db_manager import mirror_to_sqlite
        mirror_to_sqlite(CONFIG_FILE, data)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка переключения фермы: {e}")
        return False



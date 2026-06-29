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
from src.core.managers.config_manager import _read_config, _write_config
from src.core.logger import logger

def parse_vendor_model_from_device_name(device_name: str) -> Tuple[str, str]:
    if not device_name:
        return "PC", "Unknown"
    device_name_lower = device_name.lower()
    mapping = {
        "macbook": ("Apple", device_name.replace("-", " ")),
        "imac": ("Apple", device_name.replace("-", " ")),
        "mac-mini": ("Apple", "Mac mini"),
        "mac-studio": ("Apple", "Mac Studio"),
        "mac-pro": ("Apple", "Mac Pro"),
        "iphone": ("Apple", device_name.replace("-", " ")),
        "ipad": ("Apple", device_name.replace("-", " ")),
        "galaxy": ("Samsung", device_name.replace("-", " ")),
        "pixel": ("Google", device_name.replace("-", " ")),
    }
    for key, (vendor, model) in mapping.items():
        if device_name_lower.startswith(key):
            return vendor, model
            
    brands = [
        "dell", "lenovo", "asus", "hp", "acer", "msi", "razer", "microsoft", 
        "xiaomi", "oneplus", "gigabyte", "apple", "samsung", "google", 
        "honor", "huawei", "sony", "nothing", "realme"
    ]
    
    brand = None
    model = None
    
    parts = device_name.split("-", 1)
    if len(parts) == 2 and parts[0].lower() in brands:
        brand, model = parts
    else:
        parts = device_name.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() in brands:
            brand, model = parts
            
    if brand and model:
        brand_map = {
            "dell": "Dell", "lenovo": "Lenovo", "asus": "ASUS", "hp": "HP", "acer": "Acer",
            "msi": "MSI", "razer": "Razer", "microsoft": "Microsoft", "xiaomi": "Xiaomi",
            "oneplus": "OnePlus", "gigabyte": "GIGABYTE", "apple": "Apple", "samsung": "Samsung", 
            "google": "Google", "honor": "Honor", "huawei": "Huawei", "sony": "Sony", 
            "nothing": "Nothing", "realme": "Realme"
        }
        clean_brand = brand_map.get(brand.lower(), brand)
        clean_model = model.replace("-", " ")
        return clean_brand, clean_model
            
    if "-" in device_name:
        parts = device_name.split("-")
        return parts[0], " ".join(parts[1:])
    return "PC", device_name


def generate_random_device_name() -> str:
    """Генерация случайного имени устройства для спуфинга"""
    import random
    import json
    from src.core.constants import RESOURCE_DIR
    
    models_file = RESOURCE_DIR / "device_models.json"
    if models_file.exists():
        with open(models_file, "r", encoding="utf-8") as f:
            models = json.load(f)
    else:
        models = {"PC": ["Desktop"]}
        
    fake_vendor = random.choice(list(models.keys()))
    fake_model = random.choice(models[fake_vendor])
    
    clean_model = fake_model.replace("-", " ")
    
    if clean_model.lower().startswith(fake_vendor.lower()):
        return clean_model
    else:
        return f"{fake_vendor} {clean_model}"


def get_or_create_fake_hw(account_name: Optional[str]) -> Tuple[str, str, Optional[str]]:
    import random
    from src.core.constants import CONFIG_FILE
    fake_vendor = None
    fake_model = None
    device_name = None
    
    if account_name:
        try:
            data = _read_config(CONFIG_FILE)
            
            accounts = data.get("accounts", [])
            for acc in accounts:
                if acc.get("name") == account_name:
                    device_name = acc.get("device_name")
                    if device_name and device_name != f"PC-{account_name}":
                        fake_vendor, fake_model = parse_vendor_model_from_device_name(device_name)
                    else:
                        fake_vendor = acc.get("fake_vendor")
                        fake_model = acc.get("fake_model")
                        
                    if not fake_vendor or not fake_model:
                        device_name = generate_random_device_name()
                        fake_vendor, fake_model = parse_vendor_model_from_device_name(device_name)
                        
                        acc["device_name"] = device_name
                        acc["fake_vendor"] = fake_vendor
                        acc["fake_model"] = fake_model
                        
                        _write_config(CONFIG_FILE, data)
                    break
        except Exception as e:
            logger.warning(f"Ошибка загрузки/сохранения фейкового железа: {e}")
            
    if not fake_vendor or not fake_model:
        device_name = generate_random_device_name()
        fake_vendor, fake_model = parse_vendor_model_from_device_name(device_name)
        
    return fake_vendor, fake_model, device_name



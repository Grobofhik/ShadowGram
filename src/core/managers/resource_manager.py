import os
import asyncio
import random
from typing import Dict, List, Optional, Any

class ResourceManager:
    """
    Глобальный менеджер ресурсов.
    Обеспечивает потокобезопасный (atomic) доступ к пулам данных 
    для всех одновременно работающих аккаунтов.
    """
    _instance = None
    _lock = asyncio.Lock()
    
    # Структура: { resource_id: {"type": "file", "path": "...", "mode": "delete/random/sequential", "data": [...], "cursor": 0} }
    _resources: Dict[str, Dict[str, Any]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResourceManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def init_file_resource(self, resource_id: str, file_path: str, mode: str = "sequential"):
        """
        Инициализировать ресурс из файла, если он еще не инициализирован.
        mode: 'sequential' (по кругу), 'random' (случайно), 'delete' (взять и удалить)
        """
        async with self._lock:
            if resource_id not in self._resources:
                abs_path = os.path.abspath(file_path)
                data = []
                if os.path.exists(abs_path):
                    try:
                        with open(abs_path, "r", encoding="utf-8") as f:
                            data = [line.strip() for line in f if line.strip()]
                    except Exception as e:
                        print(f"Error reading resource {abs_path}: {e}")
                
                self._resources[resource_id] = {
                    "type": "file",
                    "path": abs_path,
                    "mode": mode,
                    "data": data,
                    "cursor": 0
                }
                
    async def get_value(self, resource_id: str) -> str:
        """
        Получить следующее значение из ресурса с учетом его мода (потокобезопасно).
        Возвращает пустую строку, если ресурс пуст или не найден.
        """
        async with self._lock:
            if resource_id not in self._resources:
                return ""
                
            res = self._resources[resource_id]
            data = res["data"]
            
            if not data:
                return ""
                
            mode = res["mode"]
            
            if mode == "random":
                return random.choice(data)
                
            elif mode == "delete":
                return data.pop(0)  # берем первый и удаляем из пула
                
            elif mode == "sequential":
                idx = res["cursor"]
                if idx >= len(data):
                    idx = 0
                val = data[idx]
                res["cursor"] = idx + 1
                return val
                
        return ""

resource_manager = ResourceManager.get_instance()

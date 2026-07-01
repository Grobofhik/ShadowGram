import asyncio
import random
import os
import sys
import importlib
from typing import List, Dict
from src.core.logger import logger
from src.core.managers import config_manager
from src.core.constants import CONFIG_FILE
from PyQt6.QtCore import pyqtSignal, QObject, QThread

class OrchestratorSignals(QObject):
    log_msg = pyqtSignal(str, str) # workdir, message
    progress = pyqtSignal(str, int, int) # workdir, current_step, total_steps
    finished = pyqtSignal()

class SmartOrchestratorThread(QThread):
    def __init__(self, workdirs: List[str], plugins: List[str], min_delay: int = 10, max_delay: int = 30):
        super().__init__()
        self.workdirs = workdirs
        self.plugins = plugins
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.signals = OrchestratorSignals()
        self._is_running = False
        
        # Load all global settings so we can pass them as kwargs to plugins
        cfg = config_manager._read_config(CONFIG_FILE)
        self.global_settings = cfg.get("settings", {})
        
        # Pre-import all plugin classes to find them by name
        self.plugin_classes = {}
        plugins_dir = os.path.join(os.getcwd(), "src", "modules", "plugins")
        for filename in os.listdir(plugins_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                try:
                    mod = importlib.import_module(f"src.modules.plugins.{module_name}")
                    for attr in dir(mod):
                        cls = getattr(mod, attr)
                        if isinstance(cls, type) and issubclass(cls, object) and attr.endswith("Plugin"):
                            self.plugin_classes[attr] = cls
                except Exception:
                    pass
        
    def stop(self):
        self._is_running = False
        
    async def run_account_sequence(self, workdir: str):
        sequence = list(self.plugins)
        random.shuffle(sequence)
        
        steps = []
        for i, plugin in enumerate(sequence):
            steps.append(plugin)
            if i < len(sequence) - 1:
                steps.append("DELAY")
                
        total_real_steps = len(sequence)
        completed_real_steps = 0
        
        acc_name = os.path.basename(workdir)
        self.signals.log_msg.emit(acc_name, f"🎲 Сгенерирован уникальный путь: {' ➔ '.join([s.replace('Plugin', '') for s in steps])}")
        
        data = config_manager._read_config(CONFIG_FILE)
        acc_data = next((acc for acc in data.get("accounts", []) if acc["workdir"] == workdir), None)
        if not acc_data:
            self.signals.log_msg.emit(acc_name, "❌ Аккаунт не найден!")
            return
            
        for step in steps:
            if not self._is_running:
                self.signals.log_msg.emit(acc_name, "🛑 Сценарий остановлен.")
                break
                
            if step == "DELAY":
                delay = random.randint(self.min_delay, self.max_delay)
                self.signals.log_msg.emit(acc_name, f"⏳ Имитация человека (спим {delay} сек)...")
                await asyncio.sleep(delay)
            else:
                self.signals.log_msg.emit(acc_name, f"⚙️ Выполняем: {step.replace('Plugin', '')}")
                try:
                    plugin_class = self.plugin_classes.get(step)
                    if plugin_class:
                        # Instantiate the plugin
                        plugin_inst = plugin_class(
                            acc_data, 
                            str(acc_data.get("api_id", "")), 
                            acc_data.get("api_hash", ""), 
                            lambda msg: self.signals.log_msg.emit(acc_name, f"  └ {msg}")
                        )
                        
                        # Prepare kwargs from global settings
                        kwargs = {}
                        # Map some common UI keys from global_settings if they exist
                        if "default_ai_api_key" in self.global_settings:
                            kwargs["api_key"] = self.global_settings["default_ai_api_key"]
                        if "default_ai_base_url" in self.global_settings:
                            kwargs["api_base_url"] = self.global_settings["default_ai_base_url"]
                        if "default_ai_model_name" in self.global_settings:
                            kwargs["model_name"] = self.global_settings["default_ai_model_name"]
                        if "default_ai_persona_prompt" in self.global_settings:
                            kwargs["persona_prompt"] = self.global_settings["default_ai_persona_prompt"]
                            
                        # Default avatars dir
                        kwargs["avatars_dir"] = os.path.join(os.getcwd(), "avatars")
                        # Some plugins might need links (like Smart Warmer)
                        if "default_chat_links" in self.global_settings:
                            kwargs["chat_links"] = self.global_settings["default_chat_links"]
                            
                        await plugin_inst.run(**kwargs)
                    else:
                        self.signals.log_msg.emit(acc_name, f"❌ Класс {step} не найден.")
                        
                except Exception as e:
                    self.signals.log_msg.emit(acc_name, f"❌ Ошибка в {step}: {e}")
                    
                completed_real_steps += 1
                self.signals.progress.emit(acc_name, completed_real_steps, total_real_steps)
                
        self.signals.log_msg.emit(acc_name, "✅ Сценарий успешно завершен!")

    async def _run_all(self):
        self._is_running = True
        tasks = []
        for wd in self.workdirs:
            tasks.append(asyncio.create_task(self.run_account_sequence(wd)))
            # Разброс старта каждого потока чтобы не ломиться всем сразу
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
        await asyncio.gather(*tasks)
        self._is_running = False
        self.signals.finished.emit()
        
    def run(self):
        asyncio.run(self._run_all())

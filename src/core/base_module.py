import os
import asyncio
import subprocess
import socket
import time
from typing import Dict, List, Optional, Callable, Any, Tuple, Union

"""
Базовый класс для всех модулей автоматизации ShadowGram.
Функции:

- log: отправка отформатированного сообщения в UI
- _get_free_port: получение свободного порта для прокси
- _find_session_file: поиск .session файла в папке профиля
- init_client: полная подготовка клиента (прокси + сессия + коннект)
- run: абстрактный метод для реализации логики модуля
- cleanup: корректное завершение работы (закрытие клиента и туннелей)
"""


class BaseModule:
    # Метаданные модуля (переопределяются в наследниках)
    MODULE_NAME: str = "Базовый модуль"
    MODULE_DESC: str = "Описание отсутствует"

    # Список необходимых параметров для UI: [{"name": "key", "type": "file/text", "label": "Текст"}]
    PARAMS: List[Dict[str, str]] = []

    # Флаг: разрешить запуск только для ОДНОГО аккаунта одновременно
    SINGLE_ACCOUNT: bool = False

    # (Устаревший флаг, оставлен для обратной совместимости, лучше использовать новые)
    ALLOW_PARALLEL: bool = False

    # --- Новая система жизненного цикла задач ---
    
    # 1. Задержка перед самым первым запуском аккаунта (в секундах).
    # Позволяет "размазать" массовый запуск (по умолчанию от 1 до 15 сек).
    START_DELAY: Tuple[int, int] = (5, 250)

    # 2. Должен ли этот скрипт работать циклично (бесконечно)?
    IS_CYCLIC: bool = False

    # 3. Сколько отдыхать между циклами, если IS_CYCLIC = True (в секундах).
    # По дефолту от 3 до 6 часов.
    CYCLE_DELAY: Tuple[int, int] = (10800, 21600)

    # Глобальная блокировка для синхронизации действий между аккаунтами
    _global_action_lock: Optional[asyncio.Lock] = None
    _last_global_action_time: float = 0.0

    def __init__(
        self,
        account_data: Dict[str, Any],
        api_id: str,
        api_hash: str,
        log_callback: Callable[[str], None],
    ) -> None:
        self.acc = account_data
        self.api_id = api_id
        self.api_hash = api_hash
        self.log_callback = log_callback

        self.workdir: Optional[str] = self.acc.get("workdir")
        self.proxy_url: Optional[str] = self.acc.get("proxy_url")
        self.device_name: str = self.acc.get("device_name", "ShadowGram-PC")

        self.client: Optional[Any] = None
        self.gost_process: Optional[subprocess.Popen] = None
        self.local_port: Optional[int] = None
        
    def record_analytics(self, action: str, details: str = ""):
        """Записывает событие аналитики в базу данных."""
        try:
            from src.core.managers.farm_manager import get_active_farm_name
            from src.core.managers.db_manager import log_analytics_action
            from src.core.constants import FARMS_DIR
            farm_name = get_active_farm_name()
            if farm_name and self.workdir:
                config_file = FARMS_DIR / farm_name / "config.json"
                log_analytics_action(config_file, str(self.workdir), action, details)
        except Exception:
            pass
        
        self.stealth_mode = False
        try:
            from src.core.constants import CONFIG_FILE
            from src.core.managers.config_manager import _read_config
            config = _read_config(CONFIG_FILE)
            self.stealth_mode = config.get("settings", {}).get("stealth_mode", False)
        except Exception:
            pass

        self.is_stopped = False
        self.is_paused = False

    async def sleep(self, seconds: float):
        """Обертка над asyncio.sleep с поддержкой режима невидимки (+50% к задержке)"""
        if self.stealth_mode:
            seconds *= 1.5
        
        if getattr(self, "is_stopped", False):
            raise asyncio.CancelledError("Модуль остановлен пользователем")
            
        step = 0.2
        elapsed = 0.0
        while elapsed < seconds:
            while getattr(self, "is_paused", False):
                if getattr(self, "is_stopped", False):
                    raise asyncio.CancelledError("Модуль остановлен пользователем")
                await asyncio.sleep(0.5)

            if getattr(self, "is_stopped", False):
                raise asyncio.CancelledError("Модуль остановлен пользователем")
            to_sleep = min(step, seconds - elapsed)
            await asyncio.sleep(to_sleep)
            elapsed += to_sleep
            
        if getattr(self, "is_stopped", False):
            raise asyncio.CancelledError("Модуль остановлен пользователем")

    @classmethod
    def _get_global_lock(cls) -> asyncio.Lock:
        if cls._global_action_lock is None:
            cls._global_action_lock = asyncio.Lock()
        return cls._global_action_lock

    async def wait_global_delay(self, min_seconds: int = 40, max_seconds: int = 80) -> None:
        """
        Синхронизирует аккаунты: гарантирует, что между вызовами этой функции 
        с разных аккаунтов пройдет от min_seconds до max_seconds случайного времени.
        Полезно для предотвращения одновременного спама от разных сессий.
        """
        import random
        
        lock = self._get_global_lock()
        
        async with lock:
            now = time.time()
            target_delay = random.uniform(min_seconds, max_seconds)
            elapsed = now - BaseModule._last_global_action_time
            
            if elapsed < target_delay:
                wait_time = target_delay - elapsed
                self.log(f"Глобальная пауза безопасности: {wait_time:.1f} сек...", "warning")
                await self.sleep(wait_time)
            
            BaseModule._last_global_action_time = time.time()

    def log(self, message: str, status: str = "info") -> None:
        """Отправляет отформатированное сообщение в UI"""
        prefix = f"[{self.acc['name']}]"
        color_map = {
            "success": "#00e676",
            "error": "#ff5252",
            "warning": "#fbc02d",
            "info": "white",
        }
        color = color_map.get(status, "white")

        formatted_msg = f"<span style='color: {color};'>{prefix} {message}</span>"
        self.log_callback(formatted_msg)
        
        if "Глобальная пауза" not in message:
            self.record_analytics("log_" + status, message)

    def _get_free_port(self) -> int:
        from src.core.utils import get_free_port
        return get_free_port()

    def _find_session_file(self) -> Optional[str]:
        from src.core.utils import find_session_file
        return find_session_file(self.workdir)

    async def init_client(self) -> bool:
        try:
            self.log("Инициализация клиента...", "info")
            session_path = self._find_session_file()
            if not session_path:
                self.log("Файл сессии (.session) не найден!", "error")
                return False

            proxy_settings = self._setup_proxy()
            if proxy_settings is False:
                return False

            if proxy_settings:
                self.log("Ожидание стабилизации туннеля (2 сек)...", "info")
                await self.sleep(2)

            self.log("Подключение к Telegram...", "info")
            success = await self._create_and_connect_client(session_path, proxy_settings)

            if success:
                self.log("Клиент готов!", "success")
            return success

        except asyncio.CancelledError:
            await self.cleanup()
            raise
        except Exception as e:
            self.log(f"Ошибка инициализации: {e}", "error")
            return False

    async def run(self, **kwargs: Any) -> Any:
        raise NotImplementedError("Модуль должен реализовать метод run()")

    async def cleanup(self) -> None:
        """Полная очистка ресурсов"""
        try:
            if self.client:
                if self.client.is_connected:
                    await self.client.stop()
                self.client = None
        except Exception:
            pass
        finally:
            await self._cleanup_proxy()

    async def _cleanup_proxy(self) -> None:
        if self.gost_process:
            try:
                self.gost_process.terminate()
                for _ in range(10):
                    if self.gost_process.poll() is not None: break
                    await asyncio.sleep(0.2)
                else: self.gost_process.kill()
            except: pass
            finally:
                self.gost_process = None
                self.local_port = None

    def _setup_proxy(self) -> Union[Dict[str, Any], bool, None]:
        if not self.proxy_url: return None
        
        is_socks = self.proxy_url.startswith("socks5://") or self.proxy_url.startswith("socks4://")
        if is_socks:
            from src.core.managers.proxy_manager import parse_proxy_url
            proxy_info = parse_proxy_url(self.proxy_url)
            if proxy_info:
                self.log(f"Использую SOCKS прокси напрямую: {proxy_info['hostname']}:{proxy_info['port']}", "info")
                return proxy_info
            return False

        from src.core.managers.proxy_manager import resolve_gost_binary
        gost_path = resolve_gost_binary()
        if not gost_path:
            self.log("Gost не найден!", "error")
            return False

        self.local_port = self._get_free_port()
        try:
            from src.core.managers.proxy_manager import normalize_proxy_url
            import json
            normalized_url = normalize_proxy_url(self.proxy_url)
            config_path = os.path.join(self.workdir, "gost.json")
            gost_config = {
                "ServeNodes": [f"socks5://127.0.0.1:{self.local_port}"],
                "ChainNodes": [normalized_url]
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(gost_config, f)
                
            log_path = os.path.join(self.workdir, "gost_module.log")
            log_file = open(log_path, "w")
            self.gost_process = subprocess.Popen(
                [gost_path, "-L", f"socks5://127.0.0.1:{self.local_port}", "-F", normalized_url],
                stdout=log_file, stderr=log_file, start_new_session=True
            )
            time.sleep(0.5)
            log_file.close()

            if not self._wait_for_proxy_ready(): return False

            return {"scheme": "socks5", "hostname": "127.0.0.1", "port": self.local_port}
        except Exception as e:
            self.log(f"Ошибка Gost: {e}", "error")
            return False

    def _wait_for_proxy_ready(self) -> bool:
        for i in range(50):
            if self.gost_process.poll() is not None: return False
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.1)
                    if s.connect_ex(("127.0.0.1", self.local_port)) == 0: return True
            except: pass
            time.sleep(0.1)
        return False

    async def _create_and_connect_client(self, session_path: str, proxy_settings: Optional[Dict[str, Any]]) -> bool:
        from hydrogram import Client
        from hydrogram.errors import FloodWait
        
        try:
            # Исправляем возможные проблемы с импортами в Hydrogram
            import hydrogram.types
            import hydrogram.errors
        except: pass
        
        try:
            from pathlib import Path

            from src.core.constants import CONFIG_FILE
            from src.core.managers.account_manager import get_hardware_profile
            from src.core.managers.runtime_hw_manager import apply_runtime_hw_overrides

            hw_profile = apply_runtime_hw_overrides(
                get_hardware_profile(CONFIG_FILE, os.path.dirname(session_path))
            )
            session_stem = Path(session_path).stem
            session_dir = str(Path(session_path).parent)
            
            self.client = Client(
                name=session_stem,
                api_id=int(self.api_id),
                api_hash=self.api_hash,
                workdir=session_dir,
                proxy=proxy_settings,
                device_model=hw_profile.get("device_model", "PC 64bit"),
                system_version=hw_profile.get("system_version", "Windows 10"),
                app_version=hw_profile.get("app_version", "4.8.4 x64"),
                lang_code=hw_profile.get("lang_code", "en"),
                sleep_threshold=60
            )
            # Добавляем таймаут для предотвращения вечного зависания при недоступности прокси/сети
            await asyncio.wait_for(self.client.start(), timeout=20.0)
            return True
        except asyncio.TimeoutError:
            self.log("Ошибка связи: превышено время ожидания подключения (проверьте прокси или сеть)", "error")
            try:
                await self.client.stop()
            except:
                pass
            return False
        except FloodWait as e:
            self.log(f"Флуд-вейт {e.value} сек.", "warning")
            return False
        except Exception as e:
            self.log(f"Ошибка связи: {e}", "error")
            return False

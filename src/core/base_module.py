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
        
        self.stealth_mode = False
        try:
            from src.core.constants import CONFIG_FILE
            from src.core.logic import _read_config
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
            from src.core.logic import parse_proxy_url
            proxy_info = parse_proxy_url(self.proxy_url)
            if proxy_info:
                self.log(f"Использую SOCKS прокси напрямую: {proxy_info['hostname']}:{proxy_info['port']}", "info")
                return proxy_info
            return False

        import shutil
        if not shutil.which("gost"):
            self.log("Gost не найден!", "error")
            return False

        self.local_port = self._get_free_port()
        try:
            log_path = os.path.join(self.workdir, "gost_module.log")
            log_file = open(log_path, "w")
            self.gost_process = subprocess.Popen(
                ["gost", "-L", f"socks5://127.0.0.1:{self.local_port}", "-F", self.proxy_url],
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
            self.client = Client(
                name=os.path.basename(session_path),
                api_id=int(self.api_id),
                api_hash=self.api_hash,
                workdir=os.path.dirname(session_path),
                proxy=proxy_settings,
                device_model=self.device_name,
                system_version="Linux 6.x",
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

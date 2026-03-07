import os
import asyncio
import subprocess
import socket
from typing import Dict, List, Optional, Callable, Any, Tuple
from hydrogram import Client
from hydrogram.errors import FloodWait

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
    START_DELAY: Tuple[int, int] = (1, 15)

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
        """
        :param account_data: Дикт с данными аккаунта (name, workdir, proxy_url, device_name)
        :param api_id: Telegram API ID
        :param api_hash: Telegram API Hash
        :param log_callback: Функция для вывода логов в консоль UI (принимает строку)
        """
        self.acc = account_data
        self.api_id = api_id
        self.api_hash = api_hash
        self.log_callback = log_callback

        self.workdir: Optional[str] = self.acc.get("workdir")
        self.proxy_url: Optional[str] = self.acc.get("proxy_url")
        self.device_name: str = self.acc.get("device_name", "ShadowGram-PC")

        self.client: Optional[Client] = None
        self.gost_process: Optional[subprocess.Popen] = None
        self.local_port: Optional[int] = None

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
        """Получает свободный порт для прокси"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def _find_session_file(self) -> Optional[str]:
        """Ищет .session файл в стандартных путях Telegram Desktop"""
        search_paths = [
            self.workdir,
            os.path.join(self.workdir, "tdata"),
            os.path.join(self.workdir, "tdata", "user_data"),
        ]

        for path in search_paths:
            if path and os.path.exists(path):
                try:
                    for f in os.listdir(path):
                        if f.endswith(".session"):
                            # Возвращаем путь без расширения для Hydrogram
                            return os.path.join(path, f.replace(".session", ""))
                except OSError:
                    continue
        return None

    async def init_client(self) -> bool:
        """Полная подготовка клиента: прокси + сессия + коннект"""
        try:
            self.log("Инициализация клиента...", "info")
            session_path = self._find_session_file()
            if not session_path:
                self.log("Файл сессии (.session) не найден в папке профиля!", "error")
                return False

            # Настройка прокси
            proxy_settings = self._setup_proxy()
            if proxy_settings is False:  # Ошибка при настройке прокси
                return False

            self.log("Подключение к Telegram API...", "info")
            success = await self._create_and_connect_client(
                session_path, proxy_settings
            )

            if success:
                self.log("Клиент успешно подключен!", "success")

            return success

        except asyncio.CancelledError:
            await self.cleanup()
            raise
        except Exception as e:
            self.log(f"Неожиданная ошибка при инициализации клиента: {e}", "error")
            return False

    async def run(self, **kwargs: Any) -> Any:
        """Метод для переопределения в модулях-наследниках"""
        raise NotImplementedError("Модуль должен реализовать метод run()")

    async def cleanup(self) -> None:
        """Корректное завершение работы"""
        await self._cleanup_client()
        await self._cleanup_proxy()

    async def _cleanup_client(self) -> None:
        """Очистка клиента Telegram"""
        if self.client:
            try:
                if self.client.is_connected:
                    await self.client.stop()
                else:
                    await self.client.disconnect()
            except Exception:
                pass
            finally:
                self.client = None

    async def _cleanup_proxy(self) -> None:
        """Очистка прокси-туннеля"""
        if self.gost_process:
            try:
                self.gost_process.terminate()
                # Неблокирующее ожидание завершения
                for _ in range(20):
                    if self.gost_process.poll() is not None:
                        break
                    await asyncio.sleep(0.1)
                else:
                    self.gost_process.kill()
                self.log("Прокси-туннель закрыт.", "info")
            except Exception:
                pass
            finally:
                self.gost_process = None
                self.local_port = None

    def _setup_proxy(self) -> Optional[Dict[str, Any]]:
        """Настройка прокси через Gost"""
        if not self.proxy_url:
            return None

        import shutil

        if not shutil.which("gost"):
            self.log("Ошибка: утилита 'gost' не найдена в системе!", "error")
            return False

        self.local_port = self._get_free_port()
        try:
            log_path = os.path.join(self.workdir, "gost_module.log")
            self.log(f"Запуск Gost на порту {self.local_port}...", "info")
            
            log_file = open(log_path, "w")
            self.gost_process = subprocess.Popen(
                [
                    "gost",
                    "-L",
                    f"socks5://127.0.0.1:{self.local_port}",
                    "-F",
                    self.proxy_url,
                ],
                stdout=log_file,
                stderr=log_file,
                start_new_session=True,
            )
            
            # Даем процессу время занять дескрипторы и инициализироваться
            import time
            time.sleep(0.5)
            log_file.close()

            # Ждем готовности порта
            if not self._wait_for_proxy_ready():
                return False

            self.log("Прокси-туннель готов, ожидание стабилизации...", "info")

            return {
                "scheme": "socks5",
                "hostname": "127.0.0.1",
                "port": self.local_port,
            }
        except Exception as e:
            self.log(f"Ошибка запуска Gost: {e}", "error")
            return False

    def _wait_for_proxy_ready(self) -> bool:
        """Ожидает готовности прокси-порта"""
        for i in range(50):
            if self.gost_process.poll() is not None:
                self.log("Gost внезапно завершился сразу после старта!", "error")
                return False

            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.1)
                    if s.connect_ex(("127.0.0.1", self.local_port)) == 0:
                        return True
            except Exception:
                continue

        self.log(f"Ошибка: gost не открыл порт {self.local_port} за 5 секунд!", "error")
        return False

    async def _create_and_connect_client(
        self, session_path: str, proxy_settings: Optional[Dict[str, Any]]
    ) -> bool:
        """Создание и подключение клиента Telegram"""
        try:
            self.client = Client(
                name=os.path.basename(session_path),
                api_id=int(self.api_id),
                api_hash=self.api_hash,
                workdir=os.path.dirname(session_path),
                proxy=proxy_settings,
                device_model=self.device_name,
                system_version="Arch Linux",
            )

            await self.client.start()
            return True
        except FloodWait as e:
            self.log(f"Флуд-вейт: нужно подождать {e.value} сек.", "warning")
            return False
        except Exception as e:
            self.log(f"Ошибка подключения: {e}", "error")
            return False

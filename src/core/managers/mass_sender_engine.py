import os
import re
import asyncio
import random
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt6.QtCore import QThread, pyqtSignal
from hydrogram import Client
from hydrogram.types import MessageEntity
from hydrogram.enums import MessageEntityType
from hydrogram.errors import FloodWait, RPCError, UserDeactivated, PeerIdInvalid, UserPrivacyRestricted

from src.core.logger import logger
from src.core.managers import config_manager
from src.core.constants import CONFIG_FILE

def parse_premium_emojis_and_entities(text: str) -> tuple[str, list[MessageEntity]]:
    """
    Парсит синтаксис :emoji_id: в сообщении и превращает его в Telegram Custom Emoji Entities.
    Поддерживает совместную работу с обычным Markdown/HTML форматированием.
    """
    if not text:
        return "", []
        
    pattern = re.compile(r":(\d{15,20}):")
    entities = []
    clean_text = ""
    last_idx = 0
    
    for match in pattern.finditer(text):
        clean_text += text[last_idx:match.start()]
        offset = len(clean_text)
        # Вставляем символьный плейсхолдер для эмодзи
        clean_text += "⭐"
        emoji_id = int(match.group(1))
        entities.append(MessageEntity(
            type=MessageEntityType.CUSTOM_EMOJI,
            offset=offset,
            length=1,
            custom_emoji_id=emoji_id
        ))
        last_idx = match.end()
        
    clean_text += text[last_idx:]
    return clean_text, entities

class MassSenderWorker(QThread):
    progress_signal = pyqtSignal(str, str, str)  # status_type, account_name, message
    stat_signal = pyqtSignal(int, int, int)      # sent, failed, flood
    finished_signal = pyqtSignal()

    def __init__(
        self,
        accounts: List[Dict[str, Any]],
        target_usernames: List[str],
        message_text: str,
        delay_min: int = 5,
        delay_max: int = 15,
        limit_per_acc: int = 20,
        parse_mode: str = "markdown"
    ):
        super().__init__()
        self.accounts = accounts
        self.target_usernames = [u.strip() for u in target_usernames if u.strip()]
        self.message_text = message_text
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.limit_per_acc = limit_per_acc
        self.parse_mode = parse_mode
        self.is_running = True
        
        self.total_sent = 0
        self.total_failed = 0
        self.total_flood = 0

    def stop(self):
        self.is_running = False

    def run(self):
        asyncio.run(self._process_mass_sending())

    async def _process_mass_sending(self):
        if not self.target_usernames or not self.accounts:
            self.progress_signal.emit("error", "Система", "Список получателей или аккаунтов пуст.")
            self.finished_signal.emit()
            return

        # Разделяем получателей между аккаунтами
        target_queue = list(self.target_usernames)
        self.progress_signal.emit("info", "Система", f"Запуск рассылки по {len(target_queue)} получателям с {len(self.accounts)} аккаунтов.")

        for acc in self.accounts:
            if not self.is_running or not target_queue:
                break
                
            acc_name = acc.get("name", "Unknown")
            workdir = acc.get("workdir")
            if not workdir or not Path(workdir).exists():
                self.progress_signal.emit("error", acc_name, "Папка аккаунта не найдена, пропуск.")
                continue

            # Ищем сессию
            from src.modules.session_checker import _find_session_file, _setup_proxy
            session_file = _find_session_file(Path(workdir))
            if not session_file:
                self.progress_signal.emit("error", acc_name, "Файл .session не найден.")
                continue

            # Настройка прокси
            proxy_dict = None
            gost_process = None
            proxy_url = acc.get("proxy_url")
            if proxy_url:
                is_socks = proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://")
                if is_socks:
                    from src.core.managers import proxy_manager
                    proxy_dict = proxy_manager.parse_proxy_url(proxy_url)
                else:
                    gost_process, proxy_dict = await _setup_proxy(proxy_url)

            # Создание клиента
            hw = acc.get("hardware_profile", {})
            client = Client(
                name=session_file.stem,
                workdir=str(session_file.parent),
                api_id=acc.get("api_id"),
                api_hash=acc.get("api_hash"),
                proxy=proxy_dict,
                app_version=hw.get("app_version", "4.8.4"),
                device_model=hw.get("device_model", "PC 64bit"),
                system_version=hw.get("system_version", "Windows 10"),
                lang_code=hw.get("lang_code", "en"),
                sleep_threshold=60
            )

            try:
                await client.connect()
                self.progress_signal.emit("info", acc_name, "Успешно подключен к Telegram.")

                sent_by_this_acc = 0
                while self.is_running and target_queue and sent_by_this_acc < self.limit_per_acc:
                    target_user = target_queue.pop(0)
                    
                    try:
                        # Подготовка текста и Премиум-эмодзи
                        clean_text, custom_entities = parse_premium_emojis_and_entities(self.message_text)
                        
                        if custom_entities:
                            # Для премиум-эмодзи отправляем с объектами MessageEntity
                            await client.send_message(
                                chat_id=target_user,
                                text=clean_text,
                                entities=custom_entities
                            )
                        else:
                            # Стандартная отправка с форматированием (markdown/html)
                            await client.send_message(
                                chat_id=target_user,
                                text=self.message_text,
                                parse_mode=self.parse_mode
                            )

                        self.total_sent += 1
                        sent_by_this_acc += 1
                        self.stat_signal.emit(self.total_sent, self.total_failed, self.total_flood)
                        self.progress_signal.emit("success", acc_name, f"Отправлено для {target_user} (Всего с аккаунта: {sent_by_this_acc}/{self.limit_per_acc})")

                        # Случайная задержка
                        if target_queue and sent_by_this_acc < self.limit_per_acc:
                            delay = random.uniform(self.delay_min, self.delay_max)
                            await asyncio.sleep(delay)

                    except FloodWait as flood:
                        self.total_flood += 1
                        self.stat_signal.emit(self.total_sent, self.total_failed, self.total_flood)
                        self.progress_signal.emit("warning", acc_name, f"FloodWait: Блокировка на {flood.value} сек. Переход к следующему аккаунту.")
                        # Возвращаем юзера в очередь
                        target_queue.insert(0, target_user)
                        break

                    except (UserPrivacyRestricted, PeerIdInvalid, UserDeactivated) as user_err:
                        self.total_failed += 1
                        self.stat_signal.emit(self.total_sent, self.total_failed, self.total_flood)
                        self.progress_signal.emit("error", acc_name, f"Не удалось отправить {target_user}: {user_err}")

                    except Exception as send_err:
                        self.total_failed += 1
                        self.stat_signal.emit(self.total_sent, self.total_failed, self.total_flood)
                        self.progress_signal.emit("error", acc_name, f"Ошибка отправки {target_user}: {send_err}")

            except Exception as conn_err:
                self.progress_signal.emit("error", acc_name, f"Ошибка подключения: {conn_err}")

            finally:
                if client.is_connected:
                    await client.disconnect()
                if gost_process:
                    try:
                        gost_process.terminate()
                    except:
                        pass
                self.progress_signal.emit("info", acc_name, "Завершен.")

        self.progress_signal.emit("info", "Система", f"Рассылка завершена. Успешно: {self.total_sent}, Ошибок: {self.total_failed}, FloodWait: {self.total_flood}")
        self.finished_signal.emit()

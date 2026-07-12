import os
import asyncio
import threading
import sqlite3
from typing import Optional, Dict
from PyQt6.QtCore import QObject, pyqtSignal

def _convert_telethon_to_hydrogram(telethon_session_path: str, hydrogram_session_path: str, api_id: int, user_id: int):
    # Read auth_key and dc_id from telethon
    conn_t = sqlite3.connect(telethon_session_path)
    cur_t = conn_t.cursor()
    cur_t.execute("SELECT dc_id, auth_key FROM sessions")
    row = cur_t.fetchone()
    if not row:
        conn_t.close()
        raise Exception("Telethon session not found")
    dc_id, auth_key = row
    conn_t.close()

    # Create hydrogram session
    if os.path.exists(hydrogram_session_path):
        os.remove(hydrogram_session_path)
    
    conn_h = sqlite3.connect(hydrogram_session_path)
    cur_h = conn_h.cursor()
    cur_h.execute("""
        CREATE TABLE sessions (
            dc_id INTEGER PRIMARY KEY,
            api_id INTEGER,
            test_mode INTEGER,
            auth_key BLOB,
            date INTEGER,
            user_id INTEGER,
            is_bot INTEGER
        )
    """)
    cur_h.execute("""
        CREATE TABLE peers (
            id INTEGER PRIMARY KEY,
            access_hash INTEGER,
            type INTEGER,
            username TEXT,
            phone_number TEXT,
            last_update_on INTEGER
        )
    """)
    cur_h.execute("""
        CREATE TABLE version (
            version INTEGER PRIMARY KEY
        )
    """)
    cur_h.execute("INSERT INTO version VALUES (3)")
    
    cur_h.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
        (dc_id, api_id, 0, auth_key, 0, user_id, 0)
    )
    conn_h.commit()
    conn_h.close()

class AuthWorker(QObject):
    signal_status = pyqtSignal(str)
    signal_ask_code = pyqtSignal(str) # phone_code_hash
    signal_ask_password = pyqtSignal()
    signal_success = pyqtSignal(str) # workdir path
    signal_error = pyqtSignal(str)

    def __init__(self, phone: str, api_id: int, api_hash: str, workdir: str, proxy_url: Optional[str] = None, device_name: str = "ShadowGram-PC"):
        super().__init__()
        self.phone = phone
        self.api_id = api_id
        self.api_hash = api_hash
        self.workdir = workdir
        self.proxy_url = proxy_url
        self.device_name = device_name
        
        self.user_input_event = threading.Event()
        self.user_input_value = None
        self._is_running = True

    def provide_input(self, value: str):
        self.user_input_value = value
        self.user_input_event.set()

    def cancel(self):
        self._is_running = False
        self.user_input_event.set()

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_run())
        except Exception as e:
            self.signal_error.emit(f"Критическая ошибка: {e}")
        finally:
            try:
                loop.close()
            except:
                pass

    async def _async_run(self):
        # We now use Telethon for authentication since it is more reliable for receiving SMS.
        try:
            from telethon import TelegramClient
            from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError, FloodWaitError
        except ImportError:
            self.signal_error.emit("Отсутствует библиотека telethon. Пожалуйста, выполните: pip install telethon")
            return

        import socks
        import subprocess

        os.makedirs(self.workdir, exist_ok=True)
        telethon_session_path = os.path.join(self.workdir, "telethon_account")
        hydrogram_session_path = os.path.join(self.workdir, "account.session")
        
        from src.core.constants import CONFIG_FILE
        from src.core.managers.account_manager import get_hardware_profile
        hw_profile = get_hardware_profile(CONFIG_FILE, self.workdir)

        gost_process = None
        telethon_proxy = None

        if self.proxy_url:
            is_socks = self.proxy_url.startswith("socks5://") or self.proxy_url.startswith("socks4://")
            if is_socks:
                # Format: socks5://user:pass@host:port
                # Parse proxy to telethon format
                from src.core.managers.proxy_manager import parse_proxy_url
                p_settings = parse_proxy_url(self.proxy_url)
                if p_settings:
                    proxy_type = socks.SOCKS5 if p_settings["scheme"] == "socks5" else socks.SOCKS4
                    telethon_proxy = (proxy_type, p_settings["hostname"], p_settings["port"], True, p_settings.get("username"), p_settings.get("password"))
            else:
                from src.modules.session_checker import _setup_proxy
                gost_process, p_settings = await _setup_proxy(self.proxy_url)
                if p_settings:
                    # p_settings dict is hydrogram format, e.g. {"scheme": "socks5", "hostname": "127.0.0.1", "port": port}
                    telethon_proxy = (socks.SOCKS5, p_settings["hostname"], p_settings["port"])

        # Игнорируем прокси и кастомные метаданные для чистого запроса (как просил пользователь)
        client = TelegramClient(
            telethon_session_path,
            api_id=self.api_id,
            api_hash=self.api_hash
        )

        try:
            self.signal_status.emit("Подключение к Telegram (Telethon)...")
            await client.connect()
            if not await client.is_user_authorized():
                self.signal_status.emit(f"Отправка кода на {self.phone}...")
                sent_code = await client.send_code_request(self.phone)
                self.signal_ask_code.emit(sent_code.phone_code_hash)
                
                # Wait for user input
                await asyncio.to_thread(self.user_input_event.wait)
                if not self._is_running:
                    await client.disconnect()
                    return
                
                code = self.user_input_value
                self.user_input_event.clear()
                self.user_input_value = None

                self.signal_status.emit("Авторизация...")
                try:
                    await client.sign_in(self.phone, sent_code.phone_code_hash, code)
                except SessionPasswordNeededError:
                    self.signal_ask_password.emit()
                    await asyncio.to_thread(self.user_input_event.wait)
                    if not self._is_running:
                        await client.disconnect()
                        return
                    
                    password = self.user_input_value
                    self.user_input_event.clear()
                    self.user_input_value = None
                    
                    self.signal_status.emit("Проверка пароля 2FA...")
                    await client.sign_in(password=password)
                except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
                    self.signal_error.emit("Неверный или просроченный код!")
                    await client.disconnect()
                    return
            
            # Auth complete, get user ID
            me = await client.get_me()
            user_id = me.id
            await client.disconnect()
            
            self.signal_status.emit("Конвертация в Hydrogram...")
            # Convert session
            telethon_db = telethon_session_path + ".session"
            _convert_telethon_to_hydrogram(telethon_db, hydrogram_session_path, self.api_id, user_id)
            
            # Cleanup telethon db
            if os.path.exists(telethon_db):
                os.remove(telethon_db)

            self.signal_status.emit("Успешная авторизация!")
            self.signal_success.emit(self.workdir)

        except FloodWaitError as e:
            self.signal_error.emit(f"Слишком много попыток. Подождите {e.seconds} секунд.")
        except Exception as e:
            self.signal_error.emit(f"Ошибка авторизации: {e}")
        finally:
            try:
                if client.is_connected():
                    await client.disconnect()
            except:
                pass
            if gost_process:
                gost_process.terminate()
                gost_process.wait()

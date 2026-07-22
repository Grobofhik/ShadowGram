import asyncio
import os
import sqlite3
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Awaitable, Callable

from PyQt6.QtCore import QObject, pyqtSignal
from src.core.constants import CONFIG_FILE
from src.core.managers import account_manager
from src.core.managers.api_manager import get_api_fallback_candidates, is_invalid_api_error


def _convert_telethon_to_hydrogram(
    telethon_session_path: str,
    hydrogram_session_path: str,
    api_id: int,
    user_id: int,
):
    conn_t = sqlite3.connect(telethon_session_path)
    cur_t = conn_t.cursor()
    cur_t.execute("SELECT dc_id, auth_key FROM sessions")
    row = cur_t.fetchone()
    if not row:
        conn_t.close()
        raise Exception("Telethon session not found")
    dc_id, auth_key = row
    conn_t.close()

    if os.path.exists(hydrogram_session_path):
        os.remove(hydrogram_session_path)

    conn_h = sqlite3.connect(hydrogram_session_path)
    cur_h = conn_h.cursor()
    cur_h.execute(
        """
        CREATE TABLE sessions (
            dc_id INTEGER PRIMARY KEY,
            api_id INTEGER,
            test_mode INTEGER,
            auth_key BLOB,
            date INTEGER,
            user_id INTEGER,
            is_bot INTEGER
        )
    """
    )
    cur_h.execute(
        """
        CREATE TABLE peers (
            id INTEGER PRIMARY KEY,
            access_hash INTEGER,
            type INTEGER,
            username TEXT,
            phone_number TEXT,
            last_update_on INTEGER
        )
    """
    )
    cur_h.execute(
        """
        CREATE TABLE version (
            version INTEGER PRIMARY KEY
        )
    """
    )
    cur_h.execute("INSERT INTO version VALUES (3)")
    cur_h.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
        (dc_id, api_id, 0, auth_key, 0, user_id, 0),
    )
    conn_h.commit()
    conn_h.close()


class AuthWorker(QObject):
    signal_status = pyqtSignal(str)
    signal_log = pyqtSignal(str)
    signal_stage = pyqtSignal(str)
    signal_ask_code = pyqtSignal(str)
    signal_ask_password = pyqtSignal()
    signal_success = pyqtSignal(str)
    signal_error = pyqtSignal(str)

    def __init__(
        self,
        phone: str,
        api_id: int,
        api_hash: str,
        workdir: str,
        proxy_url: Optional[str] = None,
        device_name: str = "ShadowGram-PC",
        session_name: str = "account",
        output_dir: Optional[str] = None,
        use_telethon: bool = False,
    ):
        super().__init__()
        self.phone = phone
        self.api_id = api_id
        self.api_hash = api_hash
        self.workdir = workdir
        self.proxy_url = proxy_url
        self.device_name = device_name
        self.session_name = session_name
        self.output_dir = output_dir or workdir
        self.use_telethon = use_telethon

        self.user_input_event = threading.Event()
        self.user_input_value = None
        self._is_running = True
        self._current_stage = "idle"

    def log(self, text: str):
        self.signal_status.emit(text)
        self.signal_log.emit(text)

    def set_stage(self, stage: str, text: str):
        self._current_stage = stage
        self.signal_stage.emit(stage)
        if stage == "code":
            self.signal_ask_code.emit("")
        elif stage == "password":
            self.signal_ask_password.emit()
        self.log(text)

    def provide_input(self, value: str):
        self.user_input_value = value
        self.user_input_event.set()

    def cancel(self):
        self._is_running = False
        self.user_input_event.set()

    def _emit_error(self, text: str):
        if not self._is_running:
            return
        self.signal_error.emit(text)

    def run(self):
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_run())
        except Exception as e:
            self._emit_error(f"Критическая ошибка: {e}")
        finally:
            if loop:
                try:
                    loop.close()
                except Exception:
                    pass

    async def _wait_for_input(self) -> Optional[str]:
        await asyncio.to_thread(self.user_input_event.wait)
        if not self._is_running:
            return None
        value = self.user_input_value
        self.user_input_value = None
        self.user_input_event.clear()
        return value

    def _get_hw_profile(self) -> Dict[str, Any]:
        from src.core.managers.account_manager import get_hardware_profile
        from src.core.managers.runtime_hw_manager import apply_runtime_hw_overrides

        return apply_runtime_hw_overrides(
            get_hardware_profile(CONFIG_FILE, self.workdir)
        )

    def _build_api_attempts(self):
        attempts = [{"api_id": int(self.api_id), "api_hash": self.api_hash, "label": "configured"}]
        attempts.extend(get_api_fallback_candidates(int(self.api_id), self.api_hash))
        return attempts

    def _save_working_api(self, api_id: int, api_hash: str):
        try:
            account_manager.update_api_credentials(CONFIG_FILE, self.workdir, str(api_id), api_hash)
        except Exception as exc:
            self.log(f"Не удалось сохранить рабочую API-пару: {exc}")

    def _is_invalid_2fa_error(self, error: Exception) -> bool:
        error_name = error.__class__.__name__.lower()
        error_text = str(error).lower()
        invalid_markers = (
            "passwordhashinvalid",
            "password_hash_invalid",
            "invalid password",
            "password is invalid",
            "cloud password is invalid",
        )
        return any(marker in error_name or marker in error_text for marker in invalid_markers)

    async def _verify_2fa_password(self, verifier: Callable[[str], Awaitable[Any]]) -> bool:
        while self._is_running:
            self.set_stage("password", "На аккаунте включён 2FA. Введите облачный пароль.")
            password = await self._wait_for_input()
            if password is None:
                return False

            self.set_stage("authorizing", "Проверяем пароль 2FA...")
            try:
                await verifier(password)
                return True
            except Exception as exc:
                if self._is_invalid_2fa_error(exc):
                    self.log("Неверный пароль 2FA. Попробуйте ещё раз или отмените процесс.")
                    continue
                raise
        return False

    async def _build_proxy(self):
        import socks

        gost_process = None
        telethon_proxy = None
        hydrogram_proxy = None

        if not self.proxy_url:
            return gost_process, telethon_proxy, hydrogram_proxy

        is_socks = self.proxy_url.startswith("socks5://") or self.proxy_url.startswith("socks4://")
        if is_socks:
            from src.core.managers.proxy_manager import parse_proxy_url

            p_settings = parse_proxy_url(self.proxy_url)
            if p_settings:
                proxy_type = socks.SOCKS5 if p_settings["scheme"] == "socks5" else socks.SOCKS4
                telethon_proxy = (
                    proxy_type,
                    p_settings["hostname"],
                    p_settings["port"],
                    True,
                    p_settings.get("username"),
                    p_settings.get("password"),
                )
                hydrogram_proxy = p_settings
                self.log(f"Используем SOCKS прокси: {p_settings['hostname']}:{p_settings['port']}")
            return gost_process, telethon_proxy, hydrogram_proxy

        self.log("Подключаемся к gost для HTTP/HTTPS прокси...")
        from src.modules.session_checker import _setup_proxy

        gost_process, p_settings = await _setup_proxy(self.proxy_url)
        if p_settings:
            telethon_proxy = (socks.SOCKS5, p_settings["hostname"], p_settings["port"])
            hydrogram_proxy = p_settings
            self.log(f"Локальный SOCKS туннель готов: {p_settings['hostname']}:{p_settings['port']}")

        return gost_process, telethon_proxy, hydrogram_proxy

    async def _auth_with_telethon(self):
        try:
            from telethon import TelegramClient
            from telethon.errors import (
                FloodWaitError,
                PhoneCodeExpiredError,
                PhoneCodeInvalidError,
                SessionPasswordNeededError,
            )
        except ImportError:
            self._emit_error("Отсутствует библиотека telethon. Установите: pip install telethon")
            return

        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        telethon_session_stem = output_dir / f"{self.session_name}_telethon_tmp"
        final_session_path = output_dir / f"{self.session_name}.session"

        hw = self._get_hw_profile()
        gost_process, telethon_proxy, _ = await self._build_proxy()

        try:
            for index, creds in enumerate(self._build_api_attempts(), start=1):
                client = TelegramClient(
                    str(telethon_session_stem),
                    api_id=int(creds["api_id"]),
                    api_hash=creds["api_hash"],
                    proxy=telethon_proxy,
                    device_model=hw.get("device_model", self.device_name or "PC 64bit"),
                    system_version=hw.get("system_version", "Windows 10"),
                    app_version=hw.get("app_version", "4.8.4 x64"),
                    lang_code=hw.get("lang_code", "en"),
                    system_lang_code=hw.get("lang_code", "en"),
                )
                try:
                    self.set_stage("connecting", f"Подключаемся к Telegram через Telethon (API attempt {index})...")
                    await client.connect()
                    if not await client.is_user_authorized():
                        self.set_stage("sending_code", f"Отправляем код на {self.phone}...")
                        sent_code = await client.send_code_request(self.phone)
                        self.set_stage("code", "Код отправлен. Введите код из Telegram.")

                        code = await self._wait_for_input()
                        if code is None:
                            return

                        self.set_stage("authorizing", "Проверяем код...")
                        try:
                            await client.sign_in(self.phone, sent_code.phone_code_hash, code)
                        except SessionPasswordNeededError:
                            password_ok = await self._verify_2fa_password(
                                lambda password: client.sign_in(password=password)
                            )
                            if not password_ok:
                                return
                        except (PhoneCodeInvalidError, PhoneCodeExpiredError):
                            self._emit_error("Неверный или просроченный код.")
                            return

                    me = await client.get_me()
                    self.log("Создаём файл Telethon session...")
                    telethon_db = str(telethon_session_stem) + ".session"
                    if not os.path.exists(telethon_db):
                        self._emit_error("Telethon не создал файл session.")
                        return
                    if final_session_path.exists():
                        final_session_path.unlink()
                    os.replace(telethon_db, final_session_path)
                    journal_path = Path(f"{telethon_db}-journal")
                    if journal_path.exists():
                        journal_path.unlink()
                    self._save_working_api(int(creds["api_id"]), creds["api_hash"])
                    self.log(f"Сохраняем итоговую сессию: {final_session_path}")
                    self.signal_success.emit(str(final_session_path))
                    self.log(f"Сессия успешно создана для @{getattr(me, 'username', '') or me.id}")
                    return
                except FloodWaitError as e:
                    self._emit_error(f"Слишком много попыток. Подождите {e.seconds} секунд.")
                    return
                except Exception as e:
                    if is_invalid_api_error(str(e)) and index < len(self._build_api_attempts()):
                        self.log(f"API-пара отклонена Telegram: {e}. Пробуем локальный fallback.")
                        continue
                    self._emit_error(f"Ошибка авторизации: {e}")
                    return
                finally:
                    try:
                        if client.is_connected():
                            await client.disconnect()
                    except Exception:
                        pass
        finally:
            if gost_process:
                gost_process.terminate()
                gost_process.wait()

    async def _auth_with_hydrogram(self):
        try:
            from hydrogram import Client
            from hydrogram.errors import FloodWait, PhoneCodeExpired, PhoneCodeInvalid, SessionPasswordNeeded
        except ImportError:
            self._emit_error("Отсутствует библиотека hydrogram. Проверьте requirements.")
            return

        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        final_session_path = output_dir / f"{self.session_name}.session"

        hw = self._get_hw_profile()
        gost_process, _, hydrogram_proxy = await self._build_proxy()

        try:
            for index, creds in enumerate(self._build_api_attempts(), start=1):
                client = Client(
                    name=self.session_name,
                    api_id=int(creds["api_id"]),
                    api_hash=creds["api_hash"],
                    workdir=str(output_dir),
                    proxy=hydrogram_proxy,
                    device_model=hw.get("device_model", self.device_name or "PC 64bit"),
                    system_version=hw.get("system_version", "Windows 10"),
                    app_version=hw.get("app_version", "4.8.4 x64"),
                    lang_code=hw.get("lang_code", "en"),
                )

                try:
                    self.set_stage("connecting", f"Подключаемся к Telegram через Hydrogram (API attempt {index})...")
                    await client.connect()
                    try:
                        me = await client.get_me()
                    except Exception:
                        me = None

                    if not me:
                        self.set_stage("sending_code", f"Отправляем код на {self.phone}...")
                        sent_code = await client.send_code(self.phone)
                        self.set_stage("code", "Код отправлен. Введите код из Telegram.")

                        code = await self._wait_for_input()
                        if code is None:
                            return

                        self.set_stage("authorizing", "Проверяем код...")
                        try:
                            await client.sign_in(self.phone, sent_code.phone_code_hash, code)
                        except SessionPasswordNeeded:
                            password_ok = await self._verify_2fa_password(client.check_password)
                            if not password_ok:
                                return
                        except (PhoneCodeInvalid, PhoneCodeExpired):
                            self._emit_error("Неверный или просроченный код.")
                            return

                    me = await client.get_me()
                    self._save_working_api(int(creds["api_id"]), creds["api_hash"])
                    self.log(f"Сохраняем итоговую сессию: {final_session_path}")
                    self.signal_success.emit(str(final_session_path))
                    self.log(f"Сессия успешно создана для @{getattr(me, 'username', '') or me.id}")
                    return
                except FloodWait as e:
                    wait_seconds = getattr(e, "value", None) or getattr(e, "x", None) or "неизвестно"
                    self._emit_error(f"Слишком много попыток. Подождите {wait_seconds} секунд.")
                    return
                except Exception as e:
                    if is_invalid_api_error(str(e)) and index < len(self._build_api_attempts()):
                        self.log(f"API-пара отклонена Telegram: {e}. Пробуем локальный fallback.")
                        continue
                    self._emit_error(f"Ошибка авторизации: {e}")
                    return
                finally:
                    try:
                        if client.is_connected:
                            await client.disconnect()
                    except Exception:
                        pass
        finally:
            if gost_process:
                gost_process.terminate()
                gost_process.wait()

    async def _async_run(self):
        if self.use_telethon:
            await self._auth_with_telethon()
            return
        await self._auth_with_hydrogram()

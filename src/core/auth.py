import os
import asyncio
import threading
from typing import Optional, Dict
from PyQt6.QtCore import QObject, pyqtSignal

class AuthWorker(QObject):
    signal_status = pyqtSignal(str)
    signal_ask_code = pyqtSignal(str) # phone_code_hash
    signal_ask_password = pyqtSignal()
    signal_success = pyqtSignal(str) # workdir path
    signal_error = pyqtSignal(str)

    def __init__(self, phone: str, api_id: int, api_hash: str, workdir: str, proxy: Optional[Dict] = None, device_name: str = "ShadowGram-PC"):
        super().__init__()
        self.phone = phone
        self.api_id = api_id
        self.api_hash = api_hash
        self.workdir = workdir
        self.proxy = proxy
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
        from hydrogram import Client
        from hydrogram.errors import SessionPasswordNeeded, FloodWait, PhoneCodeInvalid, PhoneCodeExpired

        os.makedirs(self.workdir, exist_ok=True)
        session_name = "account" # default name inside workdir
        
        client = Client(
            name=session_name,
            api_id=self.api_id,
            api_hash=self.api_hash,
            workdir=self.workdir,
            proxy=self.proxy,
            device_model=self.device_name,
            system_version="Arch Linux"
        )

        try:
            self.signal_status.emit("Подключение к Telegram...")
            try:
                await asyncio.wait_for(client.connect(), timeout=20.0)
            except asyncio.TimeoutError:
                raise Exception("Превышено время ожидания подключения (проверьте прокси или сеть)")

            self.signal_status.emit(f"Отправка кода на {self.phone}...")
            sent_code = await client.send_code(self.phone)
            
            self.signal_ask_code.emit(sent_code.phone_code_hash)
            
            # Ждем ввода кода от пользователя
            # Так как мы в асинхронной функции, но event блокирующий, используем asyncio.to_thread
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
            except SessionPasswordNeeded:
                self.signal_ask_password.emit()
                await asyncio.to_thread(self.user_input_event.wait)
                if not self._is_running:
                    await client.disconnect()
                    return
                
                password = self.user_input_value
                self.user_input_event.clear()
                self.user_input_value = None
                
                self.signal_status.emit("Проверка пароля 2FA...")
                await client.check_password(password)
            except (PhoneCodeInvalid, PhoneCodeExpired) as e:
                self.signal_error.emit("Неверный или просроченный код!")
                await client.disconnect()
                return

            self.signal_status.emit("Успешная авторизация!")
            await client.disconnect()
            self.signal_success.emit(self.workdir)

        except FloodWait as e:
            self.signal_error.emit(f"Слишком много попыток. Подождите {e.value} секунд.")
        except Exception as e:
            self.signal_error.emit(f"Ошибка авторизации: {e}")
        finally:
            try:
                if client.is_connected:
                    await client.disconnect()
            except:
                pass

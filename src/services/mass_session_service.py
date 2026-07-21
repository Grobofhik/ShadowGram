import asyncio
import random
import re
import threading
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QPlainTextEdit,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.core.auth import AuthWorker
from src.core.constants import CONFIG_FILE
from src.core.managers.api_manager import get_api_fallback_candidates
from src.core.managers.config_manager import _read_config
from src.core.utils import find_session_file


def resolve_account_api(account_data: dict) -> tuple[int, str]:
    raw_api_id = str(account_data.get("api_id", "")).strip()
    raw_api_hash = str(account_data.get("api_hash", "")).strip()
    if raw_api_id.isdigit() and raw_api_hash:
        return int(raw_api_id), raw_api_hash

    try:
        config = _read_config(CONFIG_FILE)
        settings = config.get("settings", {})
        default_api_id = str(settings.get("default_tg_api_id", "")).strip()
        default_api_hash = str(settings.get("default_tg_api_hash", "")).strip()
        if default_api_id.isdigit() and default_api_hash:
            return int(default_api_id), default_api_hash
    except Exception:
        pass

    return 0, ""


class AuthCodeReader:
    CODE_PATTERN = re.compile(r"\b(\d{5})\b")

    @staticmethod
    async def _build_proxy(proxy_url: Optional[str]):
        import socks

        gost_process = None
        hydrogram_proxy = None

        if not proxy_url:
            return gost_process, hydrogram_proxy

        is_socks = proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://")
        if is_socks:
            from src.core.managers.proxy_manager import parse_proxy_url

            hydrogram_proxy = parse_proxy_url(proxy_url)
            return gost_process, hydrogram_proxy

        from src.modules.session_checker import _setup_proxy

        gost_process, hydrogram_proxy = await _setup_proxy(proxy_url)
        return gost_process, hydrogram_proxy

    @classmethod
    async def _read_latest_message_id(cls, account_data: dict, timeout: int = 25) -> Optional[int]:
        code, message_id = await cls._read_code(account_data, min_message_id=None, timeout=timeout, read_only=True)
        if message_id is not None:
            return message_id
        return None

    @classmethod
    async def _read_code(
        cls,
        account_data: dict,
        min_message_id: Optional[int],
        timeout: int = 90,
        read_only: bool = False,
    ) -> tuple[Optional[str], Optional[int]]:
        try:
            from hydrogram import Client
        except ImportError as exc:
            raise RuntimeError(f"Hydrogram не установлен: {exc}") from exc

        session_path = find_session_file(account_data.get("workdir", ""))
        if not session_path:
            raise RuntimeError("Не найдена исходная Hydrogram session для чтения кода.")
        session_path = Path(session_path)

        api_id, api_hash = resolve_account_api(account_data)
        if not api_id or not api_hash:
            raise RuntimeError("Для чтения кода не настроены API ID / API Hash.")

        attempts = [{"api_id": api_id, "api_hash": api_hash}]
        attempts.extend(get_api_fallback_candidates(api_id, api_hash))

        last_error = None
        for creds in attempts:
            client = None
            gost_process = None
            try:
                gost_process, hydrogram_proxy = await cls._build_proxy(account_data.get("proxy_url"))
                client = Client(
                    name=session_path.stem,
                    workdir=str(session_path.parent),
                    api_id=int(creds["api_id"]),
                    api_hash=creds["api_hash"],
                    proxy=hydrogram_proxy,
                    device_model=account_data.get("device_name") or "ShadowGram-PC",
                )
                await client.connect()

                latest_seen = min_message_id
                start_time = time.monotonic()
                while True:
                    newest_id = None
                    async for message in client.get_chat_history(777000, limit=5):
                        newest_id = max(newest_id or 0, getattr(message, "id", 0))
                        if not getattr(message, "text", None):
                            continue

                        current_id = getattr(message, "id", 0)
                        if latest_seen is not None and current_id <= latest_seen:
                            continue

                        match = cls.CODE_PATTERN.search(message.text)
                        if match and not read_only:
                            return match.group(1), current_id

                    if read_only:
                        return None, newest_id

                    if time.monotonic() - start_time >= timeout:
                        return None, newest_id

                    await asyncio.sleep(2)
            except Exception as exc:
                last_error = exc
            finally:
                try:
                    if client and client.is_connected:
                        await client.disconnect()
                except Exception:
                    pass
                if gost_process:
                    gost_process.terminate()
                    gost_process.wait()

        if last_error:
            raise RuntimeError(str(last_error)) from last_error
        return None, None

    @classmethod
    def read_latest_message_id(cls, account_data: dict, timeout: int = 25) -> Optional[int]:
        return asyncio.run(cls._read_latest_message_id(account_data, timeout=timeout))

    @classmethod
    def wait_for_code(
        cls, account_data: dict, min_message_id: Optional[int], timeout: int = 90
    ) -> Optional[str]:
        code, _ = asyncio.run(cls._read_code(account_data, min_message_id=min_message_id, timeout=timeout))
        return code


class MassSessionWorker(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(
        self,
        accounts: list[dict],
        target_mode: str,
        output_dir: str,
        session_template: str,
        use_telethon: bool,
        delay_from: int,
        delay_to: int,
    ):
        super().__init__()
        self.accounts = accounts
        self.target_mode = target_mode
        self.output_dir = output_dir
        self.session_template = session_template
        self.use_telethon = use_telethon
        self.delay_from = delay_from
        self.delay_to = delay_to
        self._running = True
        self._auth_worker = None

    def cancel(self):
        self._running = False
        if self._auth_worker:
            self._auth_worker.cancel()

    def run(self):
        try:
            total = len(self.accounts)
            for index, account in enumerate(self.accounts, start=1):
                if not self._running:
                    self.log.emit("Процесс отменён пользователем.")
                    break

                self.progress.emit(f"Аккаунт {index}/{total}: {account.get('name', 'account')}")
                self._run_account(account, index, total)

                if not self._running or index == total:
                    continue

                delay_seconds = random.randint(self.delay_from, self.delay_to)
                self.log.emit(f"Пауза перед следующим аккаунтом: {delay_seconds} сек.")
                for _ in range(delay_seconds):
                    if not self._running:
                        break
                    time.sleep(1)
        finally:
            self.finished.emit()

    def _build_session_name(self, account: dict) -> str:
        session_name = self.session_template.replace("{name}", account.get("name", "account")).strip()
        if not session_name:
            session_name = account.get("name", "account")
        bad_chars = '<>:"/\\|?*'
        session_name = "".join("_" if char in bad_chars else char for char in session_name)
        return session_name.rstrip(". ")

    def _build_output_dir(self, account: dict) -> str:
        if self.target_mode == "profile":
            return account.get("workdir", "")
        return self.output_dir

    def _run_account(self, account: dict, index: int, total: int):
        account_name = account.get("name", f"acc{index}")
        output_dir = self._build_output_dir(account)
        session_name = self._build_session_name(account)
        target_path = Path(output_dir) / f"{session_name}.session"

        if not account.get("phone"):
            self.log.emit(f"[{account_name}] Пропуск. У аккаунта нет номера телефона.")
            return

        api_id, api_hash = resolve_account_api(account)
        if not api_id or not api_hash:
            self.log.emit(f"[{account_name}] Пропуск. Не настроены API ID / API Hash.")
            return

        if target_path.exists():
            self.log.emit(f"[{account_name}] Пропуск. Файл уже существует: {target_path}")
            return

        baseline_message_id = None
        try:
            self.log.emit(f"[{account_name}] Читаем текущую точку 777000...")
            baseline_message_id = AuthCodeReader.read_latest_message_id(account)
        except Exception as exc:
            self.log.emit(f"[{account_name}] Не удалось прочитать 777000 до старта: {exc}")

        self.log.emit(f"[{account_name}] Создаём новую {'Telethon' if self.use_telethon else 'Hydrogram'} session...")

        auth_worker = AuthWorker(
            phone=account.get("phone", ""),
            api_id=api_id,
            api_hash=api_hash,
            workdir=account.get("workdir", ""),
            proxy_url=account.get("proxy_url"),
            device_name=account.get("device_name", "ShadowGram-PC"),
            session_name=session_name,
            output_dir=output_dir,
            use_telethon=self.use_telethon,
        )
        self._auth_worker = auth_worker

        result = {"success": None, "error": None, "missing_password": False}

        auth_worker.signal_log.connect(lambda text, name=account_name: self.log.emit(f"[{name}] {text}"))
        auth_worker.signal_success.connect(lambda path: result.__setitem__("success", path))
        auth_worker.signal_error.connect(lambda text: result.__setitem__("error", text))

        def handle_code_request():
            thread = threading.Thread(
                target=self._provide_code,
                args=(auth_worker, account, account_name, baseline_message_id, result),
                daemon=True,
            )
            thread.start()

        def handle_password_request():
            password = str(account.get("password", "") or "").strip()
            if not password:
                result["missing_password"] = True
                self.log.emit(f"[{account_name}] У аккаунта нет сохранённого 2FA пароля. Прерываем этот профиль.")
                auth_worker.cancel()
                return
            self.log.emit(f"[{account_name}] Подставляем 2FA пароль из базы.")
            auth_worker.provide_input(password)

        auth_worker.signal_ask_code.connect(handle_code_request)
        auth_worker.signal_ask_password.connect(handle_password_request)
        auth_worker.run()
        self._auth_worker = None

        if result["success"]:
            self.log.emit(f"[{account_name}] Успех. Сессия сохранена: {result['success']}")
            return

        if result["missing_password"]:
            self.log.emit(f"[{account_name}] Ошибка. Требуется 2FA пароль в базе.")
            return

        if result["error"]:
            self.log.emit(f"[{account_name}] Ошибка: {result['error']}")
            return

        if not self._running:
            self.log.emit(f"[{account_name}] Остановлено пользователем.")
            return

        self.log.emit(f"[{account_name}] Неизвестный результат. Сессия не создана.")

    def _provide_code(
        self,
        auth_worker: AuthWorker,
        account: dict,
        account_name: str,
        baseline_message_id: Optional[int],
        result: dict,
    ):
        try:
            self.log.emit(f"[{account_name}] Ждём код от 777000...")
            code = AuthCodeReader.wait_for_code(account, min_message_id=baseline_message_id, timeout=90)
            if not code:
                result["error"] = "Код не пришёл или не был найден в 777000."
                self.log.emit(f"[{account_name}] Код не найден. Останавливаем этот аккаунт.")
                auth_worker.cancel()
                return
            self.log.emit(f"[{account_name}] Код получен автоматически.")
            auth_worker.provide_input(code)
        except Exception as exc:
            result["error"] = f"Не удалось получить код: {exc}"
            self.log.emit(f"[{account_name}] Не удалось получить код: {exc}")
            auth_worker.cancel()


class MassSessionService(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.thread = None
        self.account_checks = []
        self.setObjectName("PageRoot")
        self.init_ui()
        self.load_accounts()

    def create_card(self, title, subtitle=None):
        card = QFrame()
        card.setObjectName("PageCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("ServiceTitle")
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("PageSubtitle")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        return card, layout

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("PageHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(6)

        eyebrow = QLabel("AUTO SESSION BUILDER")
        eyebrow.setObjectName("PageEyebrow")
        hero_layout.addWidget(eyebrow)

        title = QLabel("Массовое создание дополнительных сессий")
        title.setObjectName("PageTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            "Берёт существующую Hydrogram session аккаунта, ловит код из 777000, подставляет 2FA из базы и создаёт новую `.session` с задержками."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(subtitle)

        main_layout.addWidget(hero)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setObjectName("ScrollContent")
        content = QVBoxLayout(container)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(16)

        accounts_card, accounts_layout = self.create_card(
            "Аккаунты",
            "Выбери аккаунты с уже существующей Hydrogram session. Именно она будет использоваться для чтения кода.",
        )
        select_row = QHBoxLayout()
        select_row.setSpacing(10)

        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_all.setObjectName("GhostBtn")
        self.btn_select_all.clicked.connect(self.select_all_accounts)
        select_row.addWidget(self.btn_select_all)

        self.btn_unselect_all = QPushButton("Снять все")
        self.btn_unselect_all.setObjectName("GhostBtn")
        self.btn_unselect_all.clicked.connect(self.clear_all_accounts)
        select_row.addWidget(self.btn_unselect_all)
        select_row.addStretch()

        self.label_selected = QLabel("Выбрано: 0")
        self.label_selected.setObjectName("StatHint")
        select_row.addWidget(self.label_selected)
        accounts_layout.addLayout(select_row)

        self.accounts_wrap = QWidget()
        self.accounts_grid = QGridLayout(self.accounts_wrap)
        self.accounts_grid.setContentsMargins(0, 0, 0, 0)
        self.accounts_grid.setHorizontalSpacing(12)
        self.accounts_grid.setVerticalSpacing(8)
        accounts_layout.addWidget(self.accounts_wrap)
        content.addWidget(accounts_card)

        target_card, target_layout = self.create_card(
            "Куда сохранять",
            "Можно класть новые session в папку каждого профиля или в одну общую директорию.",
        )
        self.radio_profile_dir = QRadioButton("В папку профиля")
        self.radio_profile_dir.setChecked(True)
        self.radio_profile_dir.toggled.connect(self.update_output_state)
        target_layout.addWidget(self.radio_profile_dir)

        self.radio_custom_dir = QRadioButton("В выбранную папку")
        self.radio_custom_dir.toggled.connect(self.update_output_state)
        target_layout.addWidget(self.radio_custom_dir)

        output_row = QHBoxLayout()
        output_row.setSpacing(10)
        self.input_output_dir = QLineEdit()
        self.input_output_dir.setPlaceholderText("Общая папка для новых session")
        output_row.addWidget(self.input_output_dir, 1)

        self.btn_browse = QPushButton("Выбрать")
        self.btn_browse.setObjectName("GhostBtn")
        self.btn_browse.clicked.connect(self.choose_output_dir)
        output_row.addWidget(self.btn_browse)
        target_layout.addLayout(output_row)
        content.addWidget(target_card)

        options_card, options_layout = self.create_card(
            "Параметры",
            "Имя новой session строится по шаблону. Можно использовать `{name}`.",
        )

        options_form = QGridLayout()
        options_form.setHorizontalSpacing(10)
        options_form.setVerticalSpacing(10)

        options_form.addWidget(QLabel("Шаблон имени:"), 0, 0)
        self.input_session_template = QLineEdit("{name}_extra")
        options_form.addWidget(self.input_session_template, 0, 1)

        options_form.addWidget(QLabel("Тип session:"), 1, 0)
        self.combo_library = QComboBox()
        self.combo_library.addItems(["Hydrogram", "Telethon"])
        options_form.addWidget(self.combo_library, 1, 1)

        options_form.addWidget(QLabel("Задержка от, сек:"), 2, 0)
        self.spin_delay_from = QSpinBox()
        self.spin_delay_from.setRange(0, 3600)
        self.spin_delay_from.setValue(10)
        options_form.addWidget(self.spin_delay_from, 2, 1)

        options_form.addWidget(QLabel("Задержка до, сек:"), 3, 0)
        self.spin_delay_to = QSpinBox()
        self.spin_delay_to.setRange(0, 3600)
        self.spin_delay_to.setValue(25)
        options_form.addWidget(self.spin_delay_to, 3, 1)

        options_layout.addLayout(options_form)
        content.addWidget(options_card)

        action_bar = QFrame()
        action_bar.setObjectName("ToolbarCard")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(14, 12, 14, 12)
        action_layout.setSpacing(10)

        self.status_label = QLabel("Ожидание запуска.")
        self.status_label.setObjectName("PageSubtitle")
        self.status_label.setWordWrap(True)
        action_layout.addWidget(self.status_label, 1)

        self.btn_start = QPushButton("Запустить")
        self.btn_start.setObjectName("LaunchBtn")
        self.btn_start.clicked.connect(self.start_mass_creation)
        action_layout.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("Отменить")
        self.btn_cancel.setObjectName("GhostBtn")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_mass_creation)
        action_layout.addWidget(self.btn_cancel)
        content.addWidget(action_bar)

        logs_card, logs_layout = self.create_card(
            "Логи",
            "Здесь виден весь поток: отправка кода, чтение 777000, 2FA и сохранение файла.",
        )
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(260)
        logs_layout.addWidget(self.log_output)
        content.addWidget(logs_card)

        content.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

        self.update_output_state()

    def append_log(self, text: str):
        self.log_output.appendPlainText(text)

    def choose_output_dir(self):
        start_dir = self.input_output_dir.text().strip() or str(Path.cwd())
        selected = QFileDialog.getExistingDirectory(self, "Выберите папку для session", start_dir)
        if selected:
            self.input_output_dir.setText(selected)

    def load_accounts(self):
        for index in reversed(range(self.accounts_grid.count())):
            item = self.accounts_grid.itemAt(index)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.account_checks.clear()
        config = _read_config(CONFIG_FILE)
        accounts = config.get("accounts", [])

        for index, account in enumerate(accounts):
            checkbox = QCheckBox(
                f"{account.get('name', 'account')}  |  {account.get('phone', 'без номера')}  |  {account.get('device_name', 'device')}"
            )
            checkbox.account_data = account
            checkbox.stateChanged.connect(self.update_selected_count)
            row = index // 2
            col = index % 2
            self.accounts_grid.addWidget(checkbox, row, col)
            self.account_checks.append(checkbox)

        self.update_selected_count()

    def update_selected_count(self):
        selected = sum(1 for checkbox in self.account_checks if checkbox.isChecked())
        self.label_selected.setText(f"Выбрано: {selected}")

    def select_all_accounts(self):
        for checkbox in self.account_checks:
            checkbox.setChecked(True)

    def clear_all_accounts(self):
        for checkbox in self.account_checks:
            checkbox.setChecked(False)

    def update_output_state(self):
        custom_enabled = self.radio_custom_dir.isChecked()
        self.input_output_dir.setEnabled(custom_enabled)
        self.btn_browse.setEnabled(custom_enabled)

    def collect_selected_accounts(self) -> list[dict]:
        return [checkbox.account_data for checkbox in self.account_checks if checkbox.isChecked()]

    def validate_form(self) -> Optional[dict]:
        accounts = self.collect_selected_accounts()
        if not accounts:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один аккаунт.")
            return None

        delay_from = self.spin_delay_from.value()
        delay_to = self.spin_delay_to.value()
        if delay_to < delay_from:
            QMessageBox.warning(self, "Ошибка", "Максимальная задержка не может быть меньше минимальной.")
            return None

        session_template = self.input_session_template.text().strip()
        if not session_template:
            QMessageBox.warning(self, "Ошибка", "Укажите шаблон имени session.")
            return None

        target_mode = "profile" if self.radio_profile_dir.isChecked() else "custom"
        output_dir = self.input_output_dir.text().strip()
        if target_mode == "custom":
            if not output_dir:
                QMessageBox.warning(self, "Ошибка", "Укажите общую папку для session.")
                return None
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        for account in accounts:
            target_dir = account.get("workdir", "") if target_mode == "profile" else output_dir
            session_name = session_template.replace("{name}", account.get("name", "account")).strip()
            if not session_name:
                QMessageBox.warning(self, "Ошибка", f"Пустое имя session для {account.get('name', 'account')}.")
                return None
            target_path = Path(target_dir) / f"{session_name}.session"
            if target_path.exists():
                QMessageBox.warning(
                    self,
                    "Конфликт файлов",
                    f"Файл уже существует и будет мешать запуску:\n{target_path}",
                )
                return None

        return {
            "accounts": accounts,
            "target_mode": target_mode,
            "output_dir": output_dir,
            "session_template": session_template,
            "use_telethon": self.combo_library.currentText() == "Telethon",
            "delay_from": delay_from,
            "delay_to": delay_to,
        }

    def start_mass_creation(self):
        payload = self.validate_form()
        if not payload:
            return

        self.log_output.clear()
        self.status_label.setText("Запуск массового создания session...")
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        self.thread = QThread(self)
        self.worker = MassSessionWorker(**payload)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.append_log)
        self.worker.progress.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def cancel_mass_creation(self):
        if self.worker:
            self.append_log("Отмена запрошена. Останавливаем текущий процесс...")
            self.status_label.setText("Отмена процесса...")
            self.worker.cancel()

    def on_worker_finished(self):
        self.status_label.setText("Процесс завершён.")
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.worker = None
        self.thread = None

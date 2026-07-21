from pathlib import Path

from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.auth import AuthWorker
from src.core.constants import CONFIG_FILE
from src.core.managers import account_manager, config_manager

class LoginWindow(QDialog):
    def __init__(self, account_data, parent=None):
        super().__init__(parent)
        self.account_data = account_data
        self.setWindowTitle(f"Авторизация: {account_data.get('name', 'Аккаунт')}")
        self.setFixedSize(520, 500)
        self.worker = None
        self.thread = None
        self.current_stage = "idle"
        self.auth_success = False

        self.init_ui()
        self.load_api_keys()
        self.load_defaults()
        self.validate_session_target()

    def load_api_keys(self):
        self.api_id = 0
        self.api_hash = ""

        raw_api_id = str(self.account_data.get("api_id", "")).strip()
        raw_api_hash = str(self.account_data.get("api_hash", "")).strip()

        if raw_api_id.isdigit() and raw_api_hash:
            self.api_id = int(raw_api_id)
            self.api_hash = raw_api_hash
            return

        try:
            config = config_manager._read_config(CONFIG_FILE)
            settings = config.get("settings", {})

            default_api_id = str(settings.get("default_tg_api_id", "")).strip()
            default_api_hash = str(settings.get("default_tg_api_hash", "")).strip()
            if default_api_id.isdigit() and default_api_hash:
                self.api_id = int(default_api_id)
                self.api_hash = default_api_hash
                return
        except Exception:
            pass

    def load_defaults(self):
        profile_name = self.account_data.get("name", "account").strip() or "account"
        self.input_session_name.setText(profile_name)
        self.input_output_dir.setText(self.account_data.get("workdir", ""))
        phone = self.account_data.get("phone") or ""
        self.input_phone.setText(phone)
        self.update_target_preview()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)

        self.stack = QStackedWidget(self)
        self.layout.addWidget(self.stack)

        setup_page = QWidget(self)
        setup_layout = QVBoxLayout(setup_page)
        setup_layout.setSpacing(10)

        info_label = QLabel(
            f"<b>Профиль:</b> {self.account_data.get('name')}<br>"
            f"<b>Устройство:</b> {self.account_data.get('device_name', 'ShadowGram-PC')}<br>"
            f"<b>Прокси:</b> {self.account_data.get('proxy_url', 'Нет')}"
        )
        info_label.setWordWrap(True)
        setup_layout.addWidget(info_label)

        setup_layout.addWidget(QLabel("Номер телефона (+7...):"))
        self.input_phone = QLineEdit()
        setup_layout.addWidget(self.input_phone)

        setup_layout.addWidget(QLabel("Имя файла сессии:"))
        self.input_session_name = QLineEdit()
        self.input_session_name.textChanged.connect(self.validate_session_target)
        setup_layout.addWidget(self.input_session_name)

        setup_layout.addWidget(QLabel("Папка для сохранения:"))
        output_row = QHBoxLayout()
        self.input_output_dir = QLineEdit()
        self.input_output_dir.textChanged.connect(self.validate_session_target)
        output_row.addWidget(self.input_output_dir)
        self.btn_browse = QPushButton("Выбрать")
        self.btn_browse.clicked.connect(self.choose_output_dir)
        output_row.addWidget(self.btn_browse)
        setup_layout.addLayout(output_row)

        self.label_target_preview = QLabel()
        self.label_target_preview.setWordWrap(True)
        setup_layout.addWidget(self.label_target_preview)

        self.label_conflict = QLabel()
        self.label_conflict.setWordWrap(True)
        setup_layout.addWidget(self.label_conflict)

        self.check_telethon = QCheckBox("Создать Telethon session")
        setup_layout.addWidget(self.check_telethon)

        self.btn_start = QPushButton("Запустить")
        self.btn_start.clicked.connect(self.start_auth)
        setup_layout.addWidget(self.btn_start)

        self.stack.addWidget(setup_page)

        auth_page = QWidget(self)
        auth_layout = QVBoxLayout(auth_page)
        auth_layout.setSpacing(10)

        self.status_label = QLabel("Ожидание...")
        self.status_label.setWordWrap(True)
        auth_layout.addWidget(self.status_label)

        auth_layout.addWidget(QLabel("Логи процесса:"))
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        auth_layout.addWidget(self.log_output, 1)

        self.input_label = QLabel("Код из Telegram:")
        auth_layout.addWidget(self.input_label)

        self.input_value = QLineEdit()
        self.input_value.setEnabled(False)
        auth_layout.addWidget(self.input_value)

        buttons_row = QHBoxLayout()
        self.btn_submit = QPushButton("Подтвердить")
        self.btn_submit.setEnabled(False)
        self.btn_submit.clicked.connect(self.submit_current_input)
        buttons_row.addWidget(self.btn_submit)

        self.btn_cancel = QPushButton("Отменить")
        self.btn_cancel.clicked.connect(self.cancel_auth)
        buttons_row.addWidget(self.btn_cancel)
        auth_layout.addLayout(buttons_row)

        self.stack.addWidget(auth_page)

    def choose_output_dir(self):
        current_dir = self.input_output_dir.text().strip() or self.account_data.get("workdir", "")
        selected = QFileDialog.getExistingDirectory(self, "Выберите папку для сессии", current_dir)
        if selected:
            self.input_output_dir.setText(selected)

    def sanitize_session_name(self, value: str) -> str:
        bad_chars = '<>:"/\\|?*'
        cleaned = "".join("_" if ch in bad_chars else ch for ch in value.strip())
        return cleaned.rstrip(". ")

    def update_target_preview(self):
        session_name = self.sanitize_session_name(self.input_session_name.text())
        output_dir = self.input_output_dir.text().strip()
        session_path = Path(output_dir) / f"{session_name}.session" if output_dir and session_name else None
        self.label_target_preview.setText(
            f"Итоговый файл: {session_path}" if session_path else "Итоговый файл: не задан"
        )

    def validate_session_target(self):
        self.update_target_preview()
        session_name = self.sanitize_session_name(self.input_session_name.text())
        output_dir = self.input_output_dir.text().strip()

        self.label_conflict.setStyleSheet("")
        if not session_name:
            self.label_conflict.setText("Имя файла сессии не может быть пустым.")
            self.btn_start.setEnabled(False)
            return False

        if session_name != self.input_session_name.text().strip():
            self.label_conflict.setText("Недопустимые символы будут заменены на '_'.")
        else:
            self.label_conflict.setText("")

        if not output_dir:
            self.label_conflict.setText("Укажите папку для сохранения сессии.")
            self.btn_start.setEnabled(False)
            return False

        target_path = Path(output_dir) / f"{session_name}.session"
        if target_path.exists():
            self.label_conflict.setStyleSheet("color: #ff5a5a;")
            self.label_conflict.setText(f"Файл уже существует: {target_path.name}")
            self.btn_start.setEnabled(False)
            return False

        self.btn_start.setEnabled(True)
        return True

    def append_log(self, text: str):
        self.log_output.appendPlainText(text)

    def set_input_mode(self, stage: str):
        self.current_stage = stage
        if stage == "code":
            self.input_label.setText("Код из Telegram:")
            self.input_value.setEchoMode(QLineEdit.EchoMode.Normal)
            self.input_value.clear()
            self.input_value.setEnabled(True)
            self.btn_submit.setEnabled(True)
            self.input_value.setFocus()
            return
        if stage == "password":
            self.input_label.setText("Пароль 2FA:")
            self.input_value.setEchoMode(QLineEdit.EchoMode.Password)
            self.input_value.clear()
            self.input_value.setEnabled(True)
            self.btn_submit.setEnabled(True)
            self.input_value.setFocus()
            return

        self.input_value.clear()
        self.input_value.setEnabled(False)
        self.btn_submit.setEnabled(False)

    def start_auth(self):
        phone = self.input_phone.text().strip()
        if not phone:
            QMessageBox.warning(self, "Ошибка", "Заполните номер телефона.")
            return

        if not self.api_id or not self.api_hash:
            QMessageBox.warning(
                self,
                "Ошибка",
                "API ID и API Hash не настроены для этого аккаунта. Откройте профиль аккаунта и укажите их.",
            )
            return

        if not self.validate_session_target():
            return

        session_name = self.sanitize_session_name(self.input_session_name.text())
        output_dir = self.input_output_dir.text().strip()
        proxy_str = self.account_data.get("proxy_url")
        device_name = self.account_data.get("device_name", "ShadowGram-PC")
        use_telethon = self.check_telethon.isChecked()

        self.thread = QThread()
        self.worker = AuthWorker(
            phone=phone,
            api_id=self.api_id,
            api_hash=self.api_hash,
            workdir=self.account_data.get("workdir"),
            proxy_url=proxy_str,
            device_name=device_name,
            session_name=session_name,
            output_dir=output_dir,
            use_telethon=use_telethon,
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.signal_status.connect(self.update_status)
        self.worker.signal_log.connect(self.append_log)
        self.worker.signal_stage.connect(self.set_input_mode)
        self.worker.signal_success.connect(self.on_success)
        self.worker.signal_error.connect(self.on_error)

        self.stack.setCurrentIndex(1)
        self.log_output.clear()
        self.append_log(
            f"Старт создания сессии. Библиотека: {'Telethon' if use_telethon else 'Hydrogram'}."
        )
        self.append_log(f"API ID: {self.api_id}")
        self.append_log(f"Путь сохранения: {Path(output_dir) / f'{session_name}.session'}")
        self.set_input_mode("waiting")
        self.thread.start()

    def update_status(self, text):
        self.status_label.setText(text)

    def submit_current_input(self):
        if not self.worker:
            return
        value = self.input_value.text().strip()
        if not value:
            return
        self.btn_submit.setEnabled(False)
        self.input_value.setEnabled(False)
        self.worker.provide_input(value)

    def cancel_auth(self):
        if self.worker:
            self.append_log("Отмена процесса пользователем.")
            self.worker.cancel()
        self.cleanup_thread()
        self.stack.setCurrentIndex(0)
        self.set_input_mode("idle")
        self.update_status("Процесс отменён.")

    def on_success(self, session_path):
        self.auth_success = True
        self.append_log("Создание сессии прошло успешно.")
        account_manager.update_account_profile_data(
            CONFIG_FILE,
            self.account_data.get("workdir"),
            phone=self.input_phone.text().strip(),
        )
        QMessageBox.information(
            self,
            "Успех",
            f"Сессия успешно создана:\n{session_path}",
        )
        self.cleanup_thread()
        self.accept()

    def on_error(self, err):
        self.append_log(f"Ошибка: {err}")
        QMessageBox.critical(self, "Ошибка", err)
        self.cleanup_thread()
        self.stack.setCurrentIndex(0)
        self.set_input_mode("idle")

    def cleanup_thread(self):
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        self.thread = None
        self.worker = None

    def closeEvent(self, event):
        if self.worker:
            self.worker.cancel()
        self.cleanup_thread()
        super().closeEvent(event)

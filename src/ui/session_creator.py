from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.auth import AuthWorker
from src.core.constants import CONFIG_FILE
from src.core.managers import config_manager


class SessionCreatorWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание сессии (Hydrogram)")
        self.setFixedSize(520, 520)
        self.setObjectName("PageRoot")
        self.worker = None
        self.thread = None

        self.config = config_manager._read_config(CONFIG_FILE)
        self.accounts = self.config.get("accounts", [])

        self.init_ui()

    def _build_page_shell(self, eyebrow, title, subtitle):
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        page_eyebrow = QLabel(eyebrow)
        page_eyebrow.setObjectName("PageEyebrow")
        layout.addWidget(page_eyebrow)

        page_title = QLabel(title)
        page_title.setObjectName("ServiceTitle")
        layout.addWidget(page_title)

        page_subtitle = QLabel(subtitle)
        page_subtitle.setObjectName("PageSubtitle")
        page_subtitle.setWordWrap(True)
        layout.addWidget(page_subtitle)

        return page, layout

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("PageHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(6)

        eyebrow = QLabel("SESSION WIZARD")
        eyebrow.setObjectName("PageEyebrow")
        hero_layout.addWidget(eyebrow)

        title = QLabel("Создание Hydrogram-сессии")
        title.setObjectName("PageTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            "Пошаговый мастер авторизации: выбор профиля, отправка кода, подтверждение и при необходимости ввод 2FA."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(subtitle)

        layout.addWidget(hero)

        shell = QFrame()
        shell.setObjectName("PageCard")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(20, 20, 20, 20)
        shell_layout.setSpacing(14)

        self.stack = QStackedWidget(self)
        shell_layout.addWidget(self.stack)
        layout.addWidget(shell, 1)

        page1, p1_layout = self._build_page_shell(
            "STEP 1",
            "Аккаунт и первичные параметры",
            "Выберите профиль, проверьте API-пару и укажите телефон, на который придет код.",
        )

        p1_layout.addWidget(QLabel("Аккаунт"))
        self.combo_accounts = QComboBox()
        for account in self.accounts:
            self.combo_accounts.addItem(f"{account.get('name')} ({account.get('workdir')})", account)
        self.combo_accounts.currentIndexChanged.connect(self.on_account_selected)
        p1_layout.addWidget(self.combo_accounts)

        p1_layout.addWidget(QLabel("API ID"))
        self.input_api_id = QLineEdit("6")
        p1_layout.addWidget(self.input_api_id)

        p1_layout.addWidget(QLabel("API Hash"))
        self.input_api_hash = QLineEdit("eb06d4abfb49dc3eeb1aeb98ae0f581e")
        p1_layout.addWidget(self.input_api_hash)

        p1_layout.addWidget(QLabel("Номер телефона"))
        self.input_phone = QLineEdit()
        self.input_phone.setPlaceholderText("+7...")
        p1_layout.addWidget(self.input_phone)

        self.btn_next1 = QPushButton("Отправить код")
        self.btn_next1.setObjectName("LaunchBtn")
        self.btn_next1.clicked.connect(self.start_auth)
        p1_layout.addWidget(self.btn_next1)
        p1_layout.addStretch()
        self.stack.addWidget(page1)

        page2, p2_layout = self._build_page_shell(
            "STEP 2",
            "Код подтверждения",
            "После отправки запроса дождитесь кода в Telegram и введите его в поле ниже.",
        )

        self.status_label = QLabel("Ожидание...")
        self.status_label.setObjectName("MetaBadge")
        self.status_label.setWordWrap(True)
        p2_layout.addWidget(self.status_label)

        p2_layout.addWidget(QLabel("Код из Telegram"))
        self.input_code = QLineEdit()
        p2_layout.addWidget(self.input_code)

        self.btn_next2 = QPushButton("Подтвердить код")
        self.btn_next2.setObjectName("LaunchBtn")
        self.btn_next2.clicked.connect(self.submit_code)
        p2_layout.addWidget(self.btn_next2)
        p2_layout.addStretch()
        self.stack.addWidget(page2)

        page3, p3_layout = self._build_page_shell(
            "STEP 3",
            "Облачный пароль",
            "Если на аккаунте включен двухфакторный пароль, укажите его для завершения авторизации.",
        )

        p3_layout.addWidget(QLabel("Пароль 2FA"))
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        p3_layout.addWidget(self.input_password)

        self.btn_next3 = QPushButton("Войти")
        self.btn_next3.setObjectName("LaunchBtn")
        self.btn_next3.clicked.connect(self.submit_password)
        p3_layout.addWidget(self.btn_next3)
        p3_layout.addStretch()
        self.stack.addWidget(page3)

        self.on_account_selected()

    def on_account_selected(self):
        account = self.combo_accounts.currentData()
        if account and account.get("name", "").startswith("+"):
            self.input_phone.setText(account.get("name"))

    def start_auth(self):
        account = self.combo_accounts.currentData()
        if not account:
            return

        phone = self.input_phone.text().strip()
        api_id_str = self.input_api_id.text().strip()
        api_hash = self.input_api_hash.text().strip()

        if not phone or not api_id_str or not api_hash:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return

        try:
            api_id = int(api_id_str)
        except Exception:
            QMessageBox.warning(self, "Ошибка", "API ID должен быть числом")
            return

        workdir = account.get("workdir")
        proxy_str = account.get("proxy_url")
        device_name = account.get("device_name", "ShadowGram-PC")

        self.thread = QThread()
        self.worker = AuthWorker(phone, api_id, api_hash, workdir, proxy_str, device_name)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.signal_status.connect(self.update_status)
        self.worker.signal_ask_code.connect(self.ask_code)
        self.worker.signal_ask_password.connect(self.ask_password)
        self.worker.signal_success.connect(self.on_success)
        self.worker.signal_error.connect(self.on_error)

        self.stack.setCurrentIndex(1)
        self.btn_next1.setEnabled(False)
        self.btn_next2.setEnabled(False)
        self.update_status("Подключение и отправка кода...")
        self.thread.start()

    def update_status(self, text):
        self.status_label.setText(text)

    def ask_code(self, phone_code_hash):
        _ = phone_code_hash
        self.update_status("Код отправлен. Введите его в поле ниже.")
        self.btn_next2.setEnabled(True)

    def submit_code(self):
        code = self.input_code.text().strip()
        if code:
            self.btn_next2.setEnabled(False)
            self.update_status("Проверка кода...")
            self.worker.provide_input(code)

    def ask_password(self):
        self.stack.setCurrentIndex(2)
        self.btn_next3.setEnabled(True)

    def submit_password(self):
        password = self.input_password.text().strip()
        if password:
            self.btn_next3.setEnabled(False)
            self.worker.provide_input(password)

    def on_success(self, workdir):
        _ = workdir
        QMessageBox.information(self, "Успех", "Сессия успешно создана!")
        self.accept()

    def on_error(self, err):
        QMessageBox.critical(self, "Ошибка", err)
        self.btn_next1.setEnabled(True)
        self.btn_next2.setEnabled(True)
        self.btn_next3.setEnabled(True)
        self.stack.setCurrentIndex(0)

    def closeEvent(self, event):
        if self.worker:
            self.worker.cancel()
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        super().closeEvent(event)

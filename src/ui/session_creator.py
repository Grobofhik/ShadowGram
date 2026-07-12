from src.core.constants import *
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QStackedWidget, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt, QThread
from src.core.auth import AuthWorker
from src.core.managers import config_manager
from src.core.constants import CONFIG_FILE
from src import styles

class SessionCreatorWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание сессии (Hydrogram)")
        self.setFixedSize(450, 450)
        self.worker = None
        self.thread = None
        
        self.config = config_manager._read_config(CONFIG_FILE)
        self.accounts = self.config.get("accounts", [])
        
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.stack = QStackedWidget(self)
        self.layout.addWidget(self.stack)

        # Страница 1: Выбор аккаунта и ввод данных
        page1 = QDialog(self)
        p1_layout = QVBoxLayout(page1)
        
        p1_layout.addWidget(QLabel("Выберите аккаунт:"))
        self.combo_accounts = QComboBox()
        for acc in self.accounts:
            self.combo_accounts.addItem(f"{acc.get('name')} ({acc.get('workdir')})", acc)
        self.combo_accounts.currentIndexChanged.connect(self.on_account_selected)
        p1_layout.addWidget(self.combo_accounts)
        
        p1_layout.addSpacing(10)
        
        # По умолчанию ставим ключи от Android, чтобы избежать банов и API_ID_INVALID
        p1_layout.addWidget(QLabel("API ID (Официальный Android):"))
        self.input_api_id = QLineEdit("6")
        p1_layout.addWidget(self.input_api_id)
        
        p1_layout.addWidget(QLabel("API Hash:"))
        self.input_api_hash = QLineEdit("eb06d4abfb49dc3eeb1aeb98ae0f581e")
        p1_layout.addWidget(self.input_api_hash)
        
        p1_layout.addSpacing(10)
        p1_layout.addWidget(QLabel("Номер телефона (+7...):"))
        self.input_phone = QLineEdit()
        p1_layout.addWidget(self.input_phone)
        
        self.btn_next1 = QPushButton("Отправить код")
        self.btn_next1.clicked.connect(self.start_auth)
        self.btn_next1.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY}; color: black; font-weight: bold; padding: 8px;")
        p1_layout.addWidget(self.btn_next1)
        self.stack.addWidget(page1)

        # Страница 2: Ввод кода
        page2 = QDialog(self)
        p2_layout = QVBoxLayout(page2)
        self.status_label = QLabel("Ожидание...")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #FFB300; font-weight: bold;")
        p2_layout.addWidget(self.status_label)
        
        p2_layout.addSpacing(10)
        p2_layout.addWidget(QLabel("Код из Telegram:"))
        self.input_code = QLineEdit()
        p2_layout.addWidget(self.input_code)
        
        self.btn_next2 = QPushButton("Подтвердить код")
        self.btn_next2.clicked.connect(self.submit_code)
        p2_layout.addWidget(self.btn_next2)
        self.stack.addWidget(page2)

        # Страница 3: Ввод 2FA
        page3 = QDialog(self)
        p3_layout = QVBoxLayout(page3)
        p3_layout.addWidget(QLabel("Облачный пароль (2FA):"))
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        p3_layout.addWidget(self.input_password)

        self.btn_next3 = QPushButton("Войти")
        self.btn_next3.clicked.connect(self.submit_password)
        p3_layout.addWidget(self.btn_next3)
        self.stack.addWidget(page3)
        
        self.on_account_selected()

    def on_account_selected(self):
        acc = self.combo_accounts.currentData()
        if acc:
            # Берем телефон из имени, если оно похоже на номер, иначе оставляем пустым
            if acc.get("name", "").startswith("+"):
                self.input_phone.setText(acc.get("name"))

    def start_auth(self):
        acc = self.combo_accounts.currentData()
        if not acc:
            return
            
        phone = self.input_phone.text().strip()
        api_id_str = self.input_api_id.text().strip()
        api_hash = self.input_api_hash.text().strip()

        if not phone or not api_id_str or not api_hash:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return
            
        try:
            api_id = int(api_id_str)
        except:
            QMessageBox.warning(self, "Ошибка", "API ID должен быть числом")
            return

        workdir = acc.get("workdir")
        proxy_str = acc.get("proxy_url")
        device_name = acc.get("device_name", "ShadowGram-PC")
        
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
        self.btn_next2.setEnabled(False)
        self.update_status("Подключение и отправка кода...")
        self.thread.start()

    def update_status(self, text):
        self.status_label.setText(text)

    def ask_code(self, phone_code_hash):
        self.update_status("Успешно! Введите код, отправленный в Telegram:")
        self.btn_next2.setEnabled(True)

    def submit_code(self):
        code = self.input_code.text().strip()
        if code:
            self.btn_next2.setEnabled(False)
            self.update_status("Проверка кода...")
            self.worker.provide_input(code)

    def ask_password(self):
        self.stack.setCurrentIndex(2)

    def submit_password(self):
        pwd = self.input_password.text().strip()
        if pwd:
            self.btn_next3.setEnabled(False)
            self.worker.provide_input(pwd)

    def on_success(self, workdir):
        QMessageBox.information(self, "Успех", "Сессия успешно создана!")
        self.accept()

    def on_error(self, err):
        QMessageBox.critical(self, "Ошибка", err)
        self.stack.setCurrentIndex(0)
        
    def closeEvent(self, event):
        if self.worker:
            self.worker.cancel()
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        super().closeEvent(event)

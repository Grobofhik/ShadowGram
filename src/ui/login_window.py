from src.core.constants import *
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QStackedWidget, QMessageBox)
from PyQt6.QtCore import Qt, QThread
from src.core.auth import AuthWorker
from src.core.managers import proxy_manager, farm_manager, config_manager, hw_manager, process_manager, account_manager
from src.core.constants import CONFIG_FILE
import json
import os

class LoginWindow(QDialog):
    def __init__(self, account_data, parent=None):
        super().__init__(parent)
        self.account_data = account_data
        self.setWindowTitle(f"Авторизация: {account_data.get('name', 'Аккаунт')}")
        self.setFixedSize(400, 300)
        self.worker = None
        self.thread = None
        
        self.init_ui()
        self.load_api_keys()

    def load_api_keys(self):
        try:
            self.api_id = int(self.account_data.get("api_id", 0))
            self.api_hash = self.account_data.get("api_hash", "")
        except Exception:
            self.api_id = 0
            self.api_hash = ""

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.stack = QStackedWidget(self)
        self.layout.addWidget(self.stack)

        # Страница 1: Ввод номера телефона (остальное берется из профиля)
        page1 = QDialog(self)
        p1_layout = QVBoxLayout(page1)
        
        info_label = QLabel(
            f"<b>Профиль:</b> {self.account_data.get('name')}<br>"
            f"<b>Устройство:</b> {self.account_data.get('device_name', 'ShadowGram-PC')}<br>"
            f"<b>Прокси:</b> {self.account_data.get('proxy_url', 'Нет')}"
        )
        p1_layout.addWidget(info_label)
        p1_layout.addSpacing(10)
        
        p1_layout.addWidget(QLabel("Введите номер телефона (+7...):"))
        self.input_phone = QLineEdit()
        p1_layout.addWidget(self.input_phone)
        
        self.btn_next1 = QPushButton("Получить код")
        self.btn_next1.clicked.connect(self.start_auth)
        p1_layout.addWidget(self.btn_next1)
        self.stack.addWidget(page1)

        # Страница 2: Ввод кода
        page2 = QDialog(self)
        p2_layout = QVBoxLayout(page2)
        self.status_label = QLabel("Ожидание...")
        p2_layout.addWidget(self.status_label)
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

    def start_auth(self):
        phone = self.input_phone.text().strip()

        if not phone:
            QMessageBox.warning(self, "Ошибка", "Заполните номер телефона")
            return
            
        if not self.api_id or not self.api_hash:
            QMessageBox.warning(self, "Ошибка", "API ID и API Hash не настроены для этого аккаунта! Откройте профиль аккаунта (нажав на аватарку) и укажите их в режиме редактирования.")
            return

        workdir = self.account_data.get("workdir")
        proxy_str = self.account_data.get("proxy_url")
        device_name = self.account_data.get("device_name", "ShadowGram-PC")
        
        self.thread = QThread()
        self.worker = AuthWorker(phone, self.api_id, self.api_hash, workdir, proxy_str, device_name)
        self.worker.moveToThread(self.thread)
        
        self.thread.started.connect(self.worker.run)
        self.worker.signal_status.connect(self.update_status)
        self.worker.signal_ask_code.connect(self.ask_code)
        self.worker.signal_ask_password.connect(self.ask_password)
        self.worker.signal_success.connect(self.on_success)
        self.worker.signal_error.connect(self.on_error)
        
        self.stack.setCurrentIndex(1)
        self.btn_next2.setEnabled(False)
        self.thread.start()

    def update_status(self, text):
        self.status_label.setText(text)

    def ask_code(self, phone_code_hash):
        self.update_status("Введите код, отправленный в Telegram:")
        self.btn_next2.setEnabled(True)

    def submit_code(self):
        code = self.input_code.text().strip()
        if code:
            self.btn_next2.setEnabled(False)
            self.worker.provide_input(code)

    def ask_password(self):
        self.stack.setCurrentIndex(2)

    def submit_password(self):
        pwd = self.input_password.text().strip()
        if pwd:
            self.btn_next3.setEnabled(False)
            self.worker.provide_input(pwd)

    def on_success(self, workdir):
        QMessageBox.information(self, "Успех", f"Аккаунт {self.account_data.get('name')} успешно авторизован!")
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

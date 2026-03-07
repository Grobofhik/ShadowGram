import json
import os
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox, QFileDialog
from PyQt6.QtCore import pyqtSignal

from src.core import logic
from src.core.constants import CONFIG_FILE
from src.ui.docs_window import DocsWindow

"""
Страница настроек приложения.
Функции:

- init_ui: инициализация элементов управления настройками
- load_settings: загрузка API ключей из файла конфигурации
- save_settings: сохранение введенных API ключей в конфиг
- run_export: запуск процесса создания резервной копии
- run_import: запуск процесса восстановления из резервной копии
"""

class SettingsPage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.docs_window = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        btn_back = QPushButton("← Назад")
        btn_back.setObjectName("BackBtn")
        btn_back.setFixedWidth(120)
        btn_back.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(btn_back)

        header_layout.addStretch()

        btn_docs = QPushButton("📖 Документация")
        btn_docs.setFixedWidth(150)
        btn_docs.setStyleSheet("background-color: #0277bd; border: 1px solid #01579b;")
        btn_docs.clicked.connect(self.show_docs)
        header_layout.addWidget(btn_docs)

        layout.addLayout(header_layout)

        label_title = QLabel("Настройки")
        label_title.setObjectName("SettingsTitle")
        label_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #4caf50;")
        layout.addWidget(label_title)

        layout.addWidget(QLabel("API ID:", objectName="SettingLabel"))
        self.input_api_id = QLineEdit(); layout.addWidget(self.input_api_id)

        layout.addWidget(QLabel("API Hash:", objectName="SettingLabel"))
        self.input_api_hash = QLineEdit(); layout.addWidget(self.input_api_hash)

        btn_save = QPushButton("💾 Сохранить настройки")
        btn_save.setFixedHeight(45)
        btn_save.clicked.connect(self.save_settings)
        layout.addWidget(btn_save)

        layout.addSpacing(30)
        layout.addWidget(QLabel("Резервное копирование:", objectName="SettingLabel"))
        
        backup_layout = QHBoxLayout()
        btn_export = QPushButton("📤 Экспорт ZIP")
        btn_export.setFixedHeight(40)
        btn_export.clicked.connect(self.run_export)
        backup_layout.addWidget(btn_export)

        btn_import = QPushButton("📥 Импорт ZIP")
        btn_import.setFixedHeight(40)
        btn_import.clicked.connect(self.run_import)
        backup_layout.addWidget(btn_import)
        
        layout.addLayout(backup_layout)
        layout.addStretch()

    def show_docs(self):
        try:
            if self.docs_window is None:
                self.docs_window = DocsWindow()
            self.docs_window.show()
            self.docs_window.raise_()
            self.docs_window.activateWindow()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть документацию: {e}")

    def load_settings(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
                s = data.get("settings", {})
                self.input_api_id.setText(str(s.get("api_id", "")))
                self.input_api_hash.setText(s.get("api_hash", ""))
        except: pass

    def save_settings(self):
        try:
            data = {"settings": {}, "accounts": []}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            
            data["settings"] = {
                "api_id": int(self.input_api_id.text()) if self.input_api_id.text().isdigit() else 0, 
                "api_hash": self.input_api_hash.text().strip()
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Успех", "Настройки сохранены!")
        except Exception as e: QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def run_export(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить бэкап", f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip", "ZIP Files (*.zip)")
        if file_path:
            success, msg = logic.export_backup(CONFIG_FILE, file_path)
            if success: QMessageBox.information(self, "Бэкап", msg)
            else: QMessageBox.critical(self, "Ошибка", msg)

    def run_import(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите бэкап", "", "ZIP Files (*.zip)")
        if file_path:
            reply = QMessageBox.warning(self, "Внимание", "Импорт перезапишет текущий список. Продолжить?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                success, msg = logic.import_backup(file_path, CONFIG_FILE)
                if success: QMessageBox.information(self, "Бэкап", msg)
                else: QMessageBox.critical(self, "Ошибка", msg)

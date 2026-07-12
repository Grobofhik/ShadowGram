from src.core.constants import *
from PyQt6.QtGui import QIcon
import json
import random
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem,
                             QMessageBox, QFrame, QTextEdit, QLineEdit)
from PyQt6.QtCore import Qt

from src.core.constants import CONFIG_FILE
from src.core.managers import config_manager
from src import styles

# Пул популярных официальных ключей Telegram
API_KEYS_POOL = [
    {"id": "6", "hash": "eb06d4abfb49dc3eeb1aeb98ae0f581e", "name": "Android Official"},
    {"id": "2040", "hash": "b18441a1ff607e10a989891a5462e627", "name": "Desktop Official"},
    {"id": "10840", "hash": "33c45224029d59cb3889c8969766562b", "name": "iOS Official"},
    {"id": "2834", "hash": "68875f756c9b437a8b5b6a826bc42c03", "name": "macOS Official"},
    {"id": "2496", "hash": "8da85b0d5bfe62527e5b244c209159c3", "name": "WebK"},
    {"id": "14227303", "hash": "a09f7a731efbd9e7fc1fbb891a4b4e54", "name": "WebZ"},
    {"id": "21724", "hash": "3e0cb5efcd52300aec5994fdfc5bdc16", "name": "Android X"},
]

class ApiGeneratorWindow(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setStyleSheet(f"background-color: {styles.COLOR_BG}; color: {styles.COLOR_TEXT_MAIN};")
        
        self.accounts = config_manager.load_config(CONFIG_FILE)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 10px; }}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)
        
        lbl_info = QLabel("Этот сервис случайным образом распределит официальные ключи Telegram (Android, iOS, Desktop) между вашими аккаунтами. Это значительно снижает риск банов при работе фермы.")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 14px; border: none;")
        card_layout.addWidget(lbl_info)
        
        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск аккаунта...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {styles.COLOR_CONSOLE_BG};
                color: {styles.COLOR_TEXT_MAIN};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {styles.COLOR_PRIMARY};
            }}
        """)
        self.search_input.textChanged.connect(self.filter_accounts)
        card_layout.addWidget(self.search_input)

        # Список аккаунтов
        self.acc_list = QListWidget()
        self.acc_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.acc_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {styles.COLOR_CONSOLE_BG}; 
                border: 1px solid {styles.COLOR_BORDER}; 
                border-radius: 8px; 
                padding: 10px;
                font-size: 14px;
            }}
            QListWidget::item {{
                padding: 5px;
            }}
            QListWidget::item:selected {{
                background-color: {styles.COLOR_PRIMARY_DARK};
                color: #FFFFFF;
                border-radius: 4px;
            }}
        """)
        
        for acc in self.accounts:
            item = QListWidgetItem(f"📱 {acc.get('name', 'Unknown')} (Текущий ID: {acc.get('api_id', 'Нет')})")
            item.setData(Qt.ItemDataRole.UserRole, acc)
            self.acc_list.addItem(item)
            
        card_layout.addWidget(self.acc_list, 1)
        
        btn_layout = QHBoxLayout()
        btn_select_all = QPushButton("Выбрать все")
        btn_select_all.setIcon(QIcon(str(START_ICON_PATH)))
        btn_select_all.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_HOVER_BG};
                color: {styles.COLOR_TEXT_MAIN};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_BORDER};
            }}
        """)
        btn_select_all.clicked.connect(self.select_all)
        btn_layout.addWidget(btn_select_all)
        
        btn_generate = QPushButton("Сгенерировать и применить")
        btn_generate.setIcon(QIcon(str(ROCKET_ICON_PATH)))
        btn_generate.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_PRIMARY};
                color: #000000;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_PRIMARY_LIGHT};
            }}
        """)
        btn_generate.clicked.connect(self.generate_api_keys)
        btn_layout.addWidget(btn_generate)
        
        card_layout.addLayout(btn_layout)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(f"""
            QTextEdit {{
                background-color: {styles.COLOR_CONSOLE_BG}; 
                color: {styles.COLOR_PRIMARY}; 
                font-family: monospace;
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        self.log_output.setFixedHeight(120)
        card_layout.addWidget(self.log_output)
        
        layout.addWidget(card)

    def filter_accounts(self, text):
        query = text.lower()
        for i in range(self.acc_list.count()):
            item = self.acc_list.item(i)
            item.setHidden(query not in item.text().lower())

    def select_all(self):
        all_selected = True
        for i in range(self.acc_list.count()):
            item = self.acc_list.item(i)
            if not item.isHidden() and not item.isSelected():
                all_selected = False
                break
                
        for i in range(self.acc_list.count()):
            item = self.acc_list.item(i)
            if not item.isHidden():
                item.setSelected(not all_selected)

    def generate_api_keys(self):
        selected_items = self.acc_list.selectedItems()
                
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один аккаунт!")
            return
            
        data = config_manager._read_config(CONFIG_FILE)
        acc_dict = {a["workdir"]: a for a in data.get("accounts", [])}
        
        self.log_output.clear()
        self.log_output.append("Начинаем генерацию API ключей...\n")
        
        for item in selected_items:
            acc = item.data(Qt.ItemDataRole.UserRole)
            workdir = acc.get("workdir")
            
            if workdir in acc_dict:
                # Берем рандомный ключ из пула
                new_key = random.choice(API_KEYS_POOL)
                
                acc_dict[workdir]["api_id"] = new_key["id"]
                acc_dict[workdir]["api_hash"] = new_key["hash"]
                
                # Сохраняем какое устройство мы ему дали (для удобства)
                acc_dict[workdir]["api_device_type"] = new_key["name"]
                
                self.log_output.append(f"[{acc.get('name')}] Установлен {new_key['name']} (ID: {new_key['id']})")
                
                # Обновляем текст в списке
                item.setText(f"📱 {acc.get('name')} (Текущий ID: {new_key['id']})")
                
        # Сохраняем в конфиг
        config_manager._write_config(CONFIG_FILE, data)
        self.log_output.append("\n Все ключи успешно обновлены и сохранены!")
        
        # Обновим UI менеджера
        if hasattr(self.manager, 'load_accounts'):
            self.manager.load_accounts()

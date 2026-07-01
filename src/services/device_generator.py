import random
import string
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QListWidget, QMessageBox, QFrame)
from PyQt6.QtCore import Qt
from src.core.managers import proxy_manager, farm_manager, config_manager, hw_manager, process_manager, account_manager
from src.core.constants import CONFIG_FILE
from src import styles

class DeviceNameGeneratorService(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Генератор имён устройств")
        self.setStyleSheet(f"background-color: {styles.COLOR_BG}; color: {styles.COLOR_TEXT_MAIN};")
        self.all_selected = False
        self.init_ui()
        self.load_accounts()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 10px; }}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)

        info_label = QLabel("Выберите аккаунты, которым нужно сгенерировать новые имена устройств. Это поможет сделать ваши сессии уникальными для Telegram.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 14px; border: none;")
        card_layout.addWidget(info_label)

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

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.setStyleSheet(f"""
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
        card_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("✅ Выбрать все")
        self.btn_select_all.setStyleSheet(f"""
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
        self.btn_select_all.clicked.connect(self.toggle_select_all)
        btn_layout.addWidget(self.btn_select_all)

        btn_generate = QPushButton("🚀 Сгенерировать")
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
        btn_generate.clicked.connect(self.generate_names)
        btn_layout.addWidget(btn_generate)

        card_layout.addLayout(btn_layout)
        layout.addWidget(card)

    def load_accounts(self):
        self.accounts = config_manager.load_config(CONFIG_FILE)
        for acc in self.accounts:
            self.list_widget.addItem(acc['name'])

    def filter_accounts(self, text):
        query = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(query not in item.text().lower())

    def toggle_select_all(self):
        self.all_selected = not self.all_selected
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                item.setSelected(self.all_selected)
        
        if self.all_selected:
            self.btn_select_all.setText("Снять выделение")
        else:
            self.btn_select_all.setText("✅ Выбрать все")

    def generate_random_device_name(self):
        return hw_manager.generate_random_device_name()

    def generate_names(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы один аккаунт!")
            return

        selected_names = [item.text() for item in selected_items]
        updated_count = 0

        for acc in self.accounts:
            if acc['name'] in selected_names:
                new_name = self.generate_random_device_name()
                if account_manager.update_device_info(CONFIG_FILE, acc['workdir'], new_name):
                    updated_count += 1

        QMessageBox.information(self, "Успех", f"Успешно обновлено {updated_count} имён устройств.")

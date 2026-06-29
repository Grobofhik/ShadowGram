import random
import string
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QListWidget, QMessageBox
from PyQt6.QtCore import Qt
from src.core.managers import proxy_manager, farm_manager, config_manager, hw_manager, process_manager, account_manager
from src.core.constants import CONFIG_FILE
from src import styles

class DeviceNameGeneratorService(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Генератор имён устройств")
        self.setFixedSize(350, 480)
        self.all_selected = False
        self.init_ui()
        self.load_accounts()

    def init_ui(self):
        layout = QVBoxLayout(self)

        info_label = QLabel("Выберите аккаунты, которым нужно\nсгенерировать новые имена устройств:")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск аккаунта...")
        self.search_input.textChanged.connect(self.filter_accounts)
        layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_all.clicked.connect(self.toggle_select_all)
        btn_layout.addWidget(self.btn_select_all)

        btn_generate = QPushButton("Сгенерировать")
        btn_generate.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: {'#000000' if styles.COLOR_PRIMARY == '#00E676' else '#FFFFFF'}; font-weight: bold;")
        btn_generate.clicked.connect(self.generate_names)
        btn_layout.addWidget(btn_generate)

        layout.addLayout(btn_layout)

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
            self.btn_select_all.setText("Выбрать все")

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
        self.accept()

import random
import string
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QListWidget, QMessageBox
from PyQt6.QtCore import Qt
from src.core import logic
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
        self.accounts = logic.load_config(CONFIG_FILE)
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
        devices = [
            # Apple
            "MacBook-Pro-14", "MacBook-Pro-16", "MacBook-Air-M1", "MacBook-Air-M2", 
            "MacBook-Air-M3", "iMac-24", "Mac-mini", "Mac-Studio", "Mac-Pro",
            "iPhone-13", "iPhone-13-Pro", "iPhone-14", "iPhone-14-Pro", "iPhone-15", 
            "iPhone-15-Pro-Max", "iPad-Pro-11", "iPad-Air",
            # Samsung
            "Galaxy-S21", "Galaxy-S22-Ultra", "Galaxy-S23", "Galaxy-S23-Ultra", 
            "Galaxy-S24", "Galaxy-S24-Ultra", "Galaxy-Z-Fold5", "Galaxy-Z-Flip5",
            "Galaxy-Tab-S9", "Galaxy-Book3-Pro",
            # Laptops & PCs (Windows)
            "Dell-XPS-15", "Dell-XPS-13", "Dell-Inspiron", "Dell-Alienware-m16",
            "Lenovo-ThinkPad-X1", "Lenovo-Legion-Pro-5", "Lenovo-IdeaPad", "Lenovo-Yoga",
            "Asus-ROG-Zephyrus", "Asus-ZenBook-14", "Asus-TUF-Gaming", "Asus-VivoBook",
            "HP-Spectre-x360", "HP-Envy", "HP-Omen", "HP-Pavilion",
            "Acer-Predator-Helios", "Acer-Nitro-5", "Acer-Swift",
            "MSI-Stealth", "MSI-Raider", "MSI-Katana",
            "Razer-Blade-15", "Razer-Blade-14",
            "Microsoft-Surface-Pro", "Microsoft-Surface-Laptop",
            # Google
            "Pixel-6", "Pixel-6-Pro", "Pixel-7", "Pixel-7-Pro", "Pixel-8", "Pixel-8-Pro",
            # Xiaomi, OnePlus, etc.
            "Xiaomi-13-Pro", "Xiaomi-14", "Redmi-Note-12", "Redmi-Note-13",
            "OnePlus-11", "OnePlus-12", "Poco-F5"
        ]
        
        base_device = random.choice(devices)
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{base_device}-{suffix}"

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
                if logic.update_device_info(CONFIG_FILE, acc['workdir'], new_name):
                    updated_count += 1

        QMessageBox.information(self, "Успех", f"Успешно обновлено {updated_count} имён устройств.")
        self.accept()

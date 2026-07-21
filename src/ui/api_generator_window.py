import random

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src import styles
from src.core.constants import CONFIG_FILE
from src.core.managers import config_manager
from src.core.managers.api_manager import get_official_api_pool


LIST_STYLE = f"""
QListWidget {{
    background-color: {styles.COLOR_CONSOLE_BG};
    border: 1px solid {styles.COLOR_BORDER};
    border-radius: 12px;
    padding: 8px;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 6px;
}}
QListWidget::item:selected {{
    background-color: {styles.COLOR_PRIMARY_DARK};
    color: #FFFFFF;
}}
QListWidget::item:hover {{
    background-color: {styles.COLOR_HOVER_BG};
}}
"""


class ApiGeneratorWindow(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.accounts = config_manager.load_config(CONFIG_FILE)
        self.setObjectName("PageRoot")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("PageHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(6)

        eyebrow = QLabel("API ROTATION")
        eyebrow.setObjectName("PageEyebrow")
        hero_layout.addWidget(eyebrow)

        title = QLabel("Генератор API-ключей")
        title.setObjectName("PageTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            "Назначает аккаунтам vetted local fallback-пары Telegram API и сразу записывает их в конфиг."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(subtitle)

        layout.addWidget(hero)

        content = QFrame()
        content.setObjectName("PageCard")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        section_title = QLabel("Аккаунты для обновления")
        section_title.setObjectName("ServiceTitle")
        header_row.addWidget(section_title)

        header_row.addStretch()

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("MetaBadge")
        header_row.addWidget(self.summary_label)
        content_layout.addLayout(header_row)

        info = QLabel(
            "Это локальный vetted-список fallback-пар. Для стабильной работы авторизации предпочтительнее свои `api_id` / `api_hash` из `my.telegram.org`."
        )
        info.setObjectName("PageSubtitle")
        info.setWordWrap(True)
        content_layout.addWidget(info)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск аккаунта...")
        self.search_input.textChanged.connect(self.filter_accounts)
        content_layout.addWidget(self.search_input)

        self.acc_list = QListWidget()
        self.acc_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.acc_list.setStyleSheet(LIST_STYLE)
        self.acc_list.itemSelectionChanged.connect(self.update_summary)

        for account in self.accounts:
            item = QListWidgetItem(self.format_account_text(account))
            item.setData(Qt.ItemDataRole.UserRole, account)
            self.acc_list.addItem(item)

        content_layout.addWidget(self.acc_list, 1)

        toolbar = QFrame()
        toolbar.setObjectName("ToolbarCard")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 12, 14, 12)
        toolbar_layout.setSpacing(10)

        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_all.setObjectName("GhostBtn")
        self.btn_select_all.clicked.connect(self.select_all)
        toolbar_layout.addWidget(self.btn_select_all)

        toolbar_layout.addStretch()

        self.btn_generate = QPushButton("Сгенерировать и применить")
        self.btn_generate.setObjectName("LaunchBtn")
        self.btn_generate.clicked.connect(self.generate_api_keys)
        toolbar_layout.addWidget(self.btn_generate)

        content_layout.addWidget(toolbar)

        self.log_output = QTextEdit()
        self.log_output.setObjectName("LogOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(140)
        content_layout.addWidget(self.log_output)

        layout.addWidget(content, 1)
        self.update_summary()

    def format_account_text(self, account):
        current_id = account.get("api_id", "Нет")
        return f"{account.get('name', 'Unknown')}  |  ID: {current_id}"

    def filter_accounts(self, text):
        query = text.lower()
        for index in range(self.acc_list.count()):
            item = self.acc_list.item(index)
            item.setHidden(query not in item.text().lower())
        self.update_summary()

    def select_all(self):
        all_selected = True
        for index in range(self.acc_list.count()):
            item = self.acc_list.item(index)
            if not item.isHidden() and not item.isSelected():
                all_selected = False
                break

        for index in range(self.acc_list.count()):
            item = self.acc_list.item(index)
            if not item.isHidden():
                item.setSelected(not all_selected)

        self.btn_select_all.setText("Снять выделение" if not all_selected else "Выбрать все")
        self.update_summary()

    def update_summary(self):
        visible_count = 0
        for index in range(self.acc_list.count()):
            if not self.acc_list.item(index).isHidden():
                visible_count += 1
        self.summary_label.setText(f"{len(self.acc_list.selectedItems())} выбрано / {visible_count} видно")

    def generate_api_keys(self):
        selected_items = self.acc_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один аккаунт!")
            return

        data = config_manager._read_config(CONFIG_FILE)
        acc_dict = {account["workdir"]: account for account in data.get("accounts", [])}

        self.log_output.clear()
        self.log_output.append("Старт распределения API-ключей.\n")

        for item in selected_items:
            account = item.data(Qt.ItemDataRole.UserRole)
            workdir = account.get("workdir")

            if workdir in acc_dict:
                new_key = random.choice(get_official_api_pool())

                acc_dict[workdir]["api_id"] = str(new_key["api_id"])
                acc_dict[workdir]["api_hash"] = new_key["api_hash"]
                acc_dict[workdir]["api_device_type"] = new_key["name"]

                self.log_output.append(
                    f"[{account.get('name')}] назначен {new_key['name']} (ID: {new_key['api_id']})"
                )

                item.setText(
                    f"{account.get('name', 'Unknown')}  |  ID: {new_key['api_id']}"
                )

        config_manager._write_config(CONFIG_FILE, data)
        self.log_output.append("\nИзменения сохранены в конфиг.")

        if hasattr(self.manager, "load_accounts"):
            self.manager.load_accounts()

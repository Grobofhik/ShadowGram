from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from src import styles
from src.core.constants import CONFIG_FILE
from src.core.managers import account_manager, config_manager, hw_manager


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


class DeviceNameGeneratorService(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Генератор имен устройств")
        self.resize(760, 620)
        self.setObjectName("PageRoot")
        self.all_selected = False
        self.accounts = []
        self.init_ui()
        self.load_accounts()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("PageHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(6)

        eyebrow = QLabel("DEVICE IDENTITY")
        eyebrow.setObjectName("PageEyebrow")
        hero_layout.addWidget(eyebrow)

        title = QLabel("Генератор имен устройств")
        title.setObjectName("PageTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            "Обновляет device name для выбранных аккаунтов, чтобы сессии выглядели менее однотипно."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(subtitle)

        layout.addWidget(hero)

        card = QFrame()
        card.setObjectName("PageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        section_title = QLabel("Выбор аккаунтов")
        section_title.setObjectName("ServiceTitle")
        header_row.addWidget(section_title)

        header_row.addStretch()

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("MetaBadge")
        header_row.addWidget(self.summary_label)
        card_layout.addLayout(header_row)

        section_hint = QLabel(
            "Поиск работает по имени аккаунта. Массовое обновление затрагивает только выделенные строки."
        )
        section_hint.setObjectName("PageSubtitle")
        section_hint.setWordWrap(True)
        card_layout.addWidget(section_hint)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск аккаунта...")
        self.search_input.textChanged.connect(self.filter_accounts)
        card_layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.setStyleSheet(LIST_STYLE)
        self.list_widget.itemSelectionChanged.connect(self.update_summary)
        card_layout.addWidget(self.list_widget, 1)

        toolbar = QFrame()
        toolbar.setObjectName("ToolbarCard")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 12, 14, 12)
        toolbar_layout.setSpacing(10)

        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_all.setObjectName("GhostBtn")
        self.btn_select_all.clicked.connect(self.toggle_select_all)
        toolbar_layout.addWidget(self.btn_select_all)

        toolbar_layout.addStretch()

        self.btn_generate = QPushButton("Сгенерировать")
        self.btn_generate.setObjectName("LaunchBtn")
        self.btn_generate.clicked.connect(self.generate_names)
        toolbar_layout.addWidget(self.btn_generate)

        card_layout.addWidget(toolbar)
        layout.addWidget(card, 1)

    def load_accounts(self):
        self.accounts = config_manager.load_config(CONFIG_FILE)
        self.list_widget.clear()
        for account in self.accounts:
            self.list_widget.addItem(account["name"])
        self.update_summary()

    def filter_accounts(self, text):
        query = text.lower()
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            item.setHidden(query not in item.text().lower())
        self.all_selected = False
        self.btn_select_all.setText("Выбрать все")
        self.update_summary()

    def toggle_select_all(self):
        self.all_selected = not self.all_selected
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if not item.isHidden():
                item.setSelected(self.all_selected)

        self.btn_select_all.setText("Снять выделение" if self.all_selected else "Выбрать все")
        self.update_summary()

    def update_summary(self):
        visible_count = 0
        for index in range(self.list_widget.count()):
            if not self.list_widget.item(index).isHidden():
                visible_count += 1
        selected_count = len(self.list_widget.selectedItems())
        self.summary_label.setText(f"{selected_count} выбрано / {visible_count} в списке")

    def generate_random_device_name(self):
        return hw_manager.generate_random_device_name()

    def generate_names(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы один аккаунт!")
            return

        selected_names = [item.text() for item in selected_items]
        updated_count = 0

        for account in self.accounts:
            if account["name"] in selected_names:
                new_name = self.generate_random_device_name()
                if account_manager.update_device_info(CONFIG_FILE, account["workdir"], new_name):
                    updated_count += 1

        QMessageBox.information(
            self,
            "Успех",
            f"Успешно обновлено {updated_count} имен устройств.",
        )

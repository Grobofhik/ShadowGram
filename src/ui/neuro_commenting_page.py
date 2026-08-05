import datetime
import json

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from src import styles
from src.core.constants import CONFIG_FILE
from src.core.managers.neuro_engine import NeuroEngineThread


LIST_STYLE = f"""
QListWidget {{
    background-color: {styles.COLOR_CONSOLE_BG};
    border: 1px solid {styles.COLOR_BORDER};
    border-radius: 10px;
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


TABLE_STYLE = f"""
QTableWidget {{
    background-color: {styles.COLOR_CONSOLE_BG};
    border: 1px solid {styles.COLOR_BORDER};
    border-radius: 12px;
    gridline-color: {styles.COLOR_BORDER};
    selection-background-color: {styles.COLOR_SELECT_BG};
    selection-color: {styles.COLOR_TEXT_MAIN};
}}
QHeaderView::section {{
    background-color: {styles.COLOR_ACCENT_BG};
    color: {styles.COLOR_TEXT_MUTED};
    padding: 10px 12px;
    border: none;
    border-bottom: 1px solid {styles.COLOR_BORDER};
    font-weight: bold;
}}
"""


class PromptDialog(QDialog):
    def __init__(self, account_name, current_prompts, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Пул промптов: {account_name}")
        self.resize(680, 560)
        self.setObjectName("PageRoot")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        card = QFrame()
        card.setObjectName("PageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 22, 22, 22)
        card_layout.setSpacing(14)

        eyebrow = QLabel("PROMPT POOL")
        eyebrow.setObjectName("PageEyebrow")
        card_layout.addWidget(eyebrow)

        title = QLabel(f"Промпты для {account_name}")
        title.setObjectName("PageTitle")
        card_layout.addWidget(title)

        subtitle = QLabel("Для каждого комментария будет использоваться случайный промпт из списка.")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        card_layout.addWidget(subtitle)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(LIST_STYLE)
        for prompt in current_prompts:
            self.list_widget.addItem(prompt)
        card_layout.addWidget(self.list_widget, 1)

        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(10)

        btn_add = QPushButton("Добавить")
        btn_add.setObjectName("GhostBtn")
        btn_add.clicked.connect(self.add_prompt)
        tools_layout.addWidget(btn_add)

        btn_edit = QPushButton("Изменить")
        btn_edit.setObjectName("GhostBtn")
        btn_edit.clicked.connect(self.edit_prompt)
        tools_layout.addWidget(btn_edit)

        btn_delete = QPushButton("Удалить")
        btn_delete.setObjectName("DeleteBtn")
        btn_delete.clicked.connect(self.del_prompt)
        tools_layout.addWidget(btn_delete)

        tools_layout.addStretch()
        card_layout.addLayout(tools_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_button:
            ok_button.setObjectName("LaunchBtn")
            ok_button.setText("Применить")
        if cancel_button:
            cancel_button.setObjectName("GhostBtn")
            cancel_button.setText("Отмена")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        card_layout.addWidget(button_box)

        layout.addWidget(card)

    def add_prompt(self):
        text, ok = QInputDialog.getMultiLineText(self, "Новый промпт", "Введите текст промпта:")
        if ok and text.strip():
            self.list_widget.addItem(text.strip())

    def edit_prompt(self):
        current = self.list_widget.currentItem()
        if current:
            text, ok = QInputDialog.getMultiLineText(
                self, "Изменить промпт", "Введите текст промпта:", current.text()
            )
            if ok and text.strip():
                current.setText(text.strip())

    def del_prompt(self):
        current = self.list_widget.currentItem()
        if current:
            self.list_widget.takeItem(self.list_widget.row(current))

    def get_prompts(self):
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]


class NeuroCommentingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.is_running = False
        self.is_stopping = False
        self.account_prompts = {}
        self.selected_accounts_cache = []

        self.setObjectName("PageRoot")
        self.setup_ui()
        self.load_settings()
        self.refresh_accounts()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("PageHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(18)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(6)

        eyebrow = QLabel("AI COMMENT GRID")
        eyebrow.setObjectName("PageEyebrow")
        hero_text.addWidget(eyebrow)

        title = QLabel("Нейрокомментинг")
        title.setObjectName("PageTitle")
        hero_text.addWidget(title)

        subtitle = QLabel(
            "Управление каналами, задержками и ролями аккаунтов для массового AI-комментинга "
            "из одного экрана."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        hero_text.addWidget(subtitle)

        hero_layout.addLayout(hero_text, 1)

        self.btn_save = QPushButton("Сохранить настройки")
        self.btn_save.setObjectName("GhostBtn")
        self.btn_save.setMinimumWidth(220)
        self.btn_save.clicked.connect(self.save_settings)
        hero_layout.addWidget(self.btn_save, alignment=Qt.AlignmentFlag.AlignTop)

        main_layout.addWidget(hero)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        self.stat_channels = self._create_stat_card("Цели", "Строки с каналами")
        self.stat_selected = self._create_stat_card("Аккаунты", "Выбраны для запуска")
        self.stat_prompts = self._create_stat_card("Промпты", "Аккаунты с ролями")
        for card, _ in [self.stat_channels, self.stat_selected, self.stat_prompts]:
            stats_layout.addWidget(card)
        main_layout.addLayout(stats_layout)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)

        channels_card = QFrame()
        channels_card.setObjectName("PageCard")
        channels_layout = QVBoxLayout(channels_card)
        channels_layout.setContentsMargins(20, 20, 20, 20)
        channels_layout.setSpacing(10)

        channels_title = QLabel("Целевые каналы")
        channels_title.setObjectName("ServiceTitle")
        channels_layout.addWidget(channels_title)

        channels_hint = QLabel("По одной ссылке или `@username` на строку.")
        channels_hint.setObjectName("PageSubtitle")
        channels_hint.setWordWrap(True)
        channels_layout.addWidget(channels_hint)

        self.channels_text = QTextEdit()
        self.channels_text.setPlaceholderText("https://t.me/durov\n@telegram")
        self.channels_text.textChanged.connect(self.update_overview)
        channels_layout.addWidget(self.channels_text, 1)
        top_layout.addWidget(channels_card, 1)

        settings_card = QFrame()
        settings_card.setObjectName("PageCard")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(14)

        settings_title = QLabel("Глобальные настройки")
        settings_title.setObjectName("ServiceTitle")
        settings_layout.addWidget(settings_title)

        settings_hint = QLabel("Режим распределения и задержки между действиями аккаунтов.")
        settings_hint.setObjectName("PageSubtitle")
        settings_hint.setWordWrap(True)
        settings_layout.addWidget(settings_hint)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(
            ["Режим: Делить каналы поровну", "Режим: Каждый работает по всем"]
        )
        settings_layout.addWidget(self.mode_combo)

        delays_layout = QHBoxLayout()
        delays_layout.setSpacing(12)
        delays_layout.addLayout(self._create_spin_group("Подписка, сек", 5, 300, 30, "spin_sub"))
        delays_layout.addLayout(self._create_spin_group("Комментарий, сек", 10, 600, 60, "spin_com"))

        channel_delay_layout = QVBoxLayout()
        channel_delay_label = QLabel("Задержка между каналами, сек")
        channel_delay_label.setObjectName("StatHint")
        channel_delay_layout.addWidget(channel_delay_label)

        range_layout = QHBoxLayout()
        range_layout.setSpacing(8)
        self.spin_chan_min = QSpinBox()
        self.spin_chan_min.setRange(10, 3600)
        self.spin_chan_min.setValue(60)
        range_layout.addWidget(self.spin_chan_min)

        dash = QLabel("—")
        dash.setObjectName("PageSubtitle")
        dash.setAlignment(Qt.AlignmentFlag.AlignCenter)
        range_layout.addWidget(dash)

        self.spin_chan_max = QSpinBox()
        self.spin_chan_max.setRange(10, 3600)
        self.spin_chan_max.setValue(120)
        range_layout.addWidget(self.spin_chan_max)
        channel_delay_layout.addLayout(range_layout)
        delays_layout.addLayout(channel_delay_layout)

        settings_layout.addLayout(delays_layout)

        self.check_read_history = QCheckBox(
            "Анализировать последние комментарии перед ответом"
        )
        self.check_read_history.setChecked(True)
        settings_layout.addWidget(self.check_read_history)
        settings_layout.addStretch()
        top_layout.addWidget(settings_card, 1)

        main_layout.addLayout(top_layout)

        activity_card = QFrame()
        activity_card.setObjectName("PageCard")
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(20, 20, 20, 20)
        activity_layout.setSpacing(14)

        section_title = QLabel("Аккаунты и live-лог")
        section_title.setObjectName("ServiceTitle")
        activity_layout.addWidget(section_title)

        section_hint = QLabel(
            "Выбирайте аккаунты, задавайте индивидуальные роли и контролируйте статусы ядра в реальном времени."
        )
        section_hint.setObjectName("PageSubtitle")
        section_hint.setWordWrap(True)
        activity_layout.addWidget(section_hint)

        split_layout = QHBoxLayout()
        split_layout.setSpacing(16)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Участвует", "Аккаунт", "Промпт", "Статус", "Настройка"]
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemChanged.connect(self.on_table_item_changed)
        split_layout.addWidget(self.table, 6)

        self.terminal = QTextEdit()
        self.terminal.setObjectName("LogOutput")
        self.terminal.setReadOnly(True)
        self.terminal.setPlaceholderText("SYSTEM_STANDBY...\nAWAITING_INITIALIZATION...")
        split_layout.addWidget(self.terminal, 4)

        activity_layout.addLayout(split_layout, 1)

        toolbar = QFrame()
        toolbar.setObjectName("ToolbarCard")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 12, 14, 12)
        toolbar_layout.setSpacing(10)

        self.btn_refresh = QPushButton("Обновить список")
        self.btn_refresh.setObjectName("GhostBtn")
        self.btn_refresh.clicked.connect(self.refresh_accounts)
        toolbar_layout.addWidget(self.btn_refresh)

        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_all.setObjectName("GhostBtn")
        self.btn_select_all.clicked.connect(self.select_all_accounts)
        toolbar_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Снять выбор")
        self.btn_deselect_all.setObjectName("GhostBtn")
        self.btn_deselect_all.clicked.connect(self.deselect_all_accounts)
        toolbar_layout.addWidget(self.btn_deselect_all)

        toolbar_layout.addStretch()

        self.btn_run = QPushButton()
        self.btn_run.setObjectName("LaunchBtn")
        self.btn_run.setProperty("running", False)
        self.btn_run.setMinimumSize(220, 42)
        self.btn_run.clicked.connect(self.toggle_running)
        toolbar_layout.addWidget(self.btn_run)
        activity_layout.addWidget(toolbar)

        main_layout.addWidget(activity_card, 1)
        self._refresh_run_button()

    def _create_stat_card(self, label_text, hint_text):
        card = QFrame()
        card.setObjectName("StatCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)

        label = QLabel(label_text)
        label.setObjectName("StatLabel")
        layout.addWidget(label)

        value = QLabel("0")
        value.setObjectName("StatValue")
        layout.addWidget(value)

        hint = QLabel(hint_text)
        hint.setObjectName("StatHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        return card, value

    def _create_spin_group(self, label_text, min_value, max_value, default_value, attr_name):
        layout = QVBoxLayout()
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setObjectName("StatHint")
        layout.addWidget(label)

        spin = QSpinBox()
        spin.setRange(min_value, max_value)
        spin.setValue(default_value)
        setattr(self, attr_name, spin)
        layout.addWidget(spin)
        return layout

    def _refresh_run_button(self):
        if self.is_stopping:
            self.btn_run.setText("Останавливается...")
            self.btn_run.setProperty("running", True)
            self.btn_run.setEnabled(False)
        else:
            self.btn_run.setText("Остановить" if self.is_running else "Запустить")
            self.btn_run.setProperty("running", self.is_running)
            self.btn_run.setEnabled(True)

        self.btn_run.style().unpolish(self.btn_run)
        self.btn_run.style().polish(self.btn_run)
        self.btn_run.update()

    def update_overview(self):
        channel_count = len(
            [line.strip() for line in self.channels_text.toPlainText().splitlines() if line.strip()]
        )
        selected_count = 0
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected_count += 1
        prompt_count = sum(1 for prompts in self.account_prompts.values() if prompts)

        self.stat_channels[1].setText(str(channel_count))
        self.stat_selected[1].setText(str(selected_count))
        self.stat_prompts[1].setText(str(prompt_count))

    @pyqtSlot(QTableWidgetItem)
    def on_table_item_changed(self, item):
        if item.column() == 0:
            self.update_overview()

    def load_settings(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)

            neuro = data.get("settings", {}).get("neuro_v2", {})
            self.channels_text.setText(neuro.get("channels", ""))
            self.spin_sub.setValue(neuro.get("sub_delay", 30))
            self.spin_com.setValue(neuro.get("com_delay", 60))
            self.spin_chan_min.setValue(neuro.get("chan_delay_min", 60))
            self.spin_chan_max.setValue(neuro.get("chan_delay_max", 120))
            self.mode_combo.setCurrentIndex(neuro.get("mode", 0))
            self.check_read_history.setChecked(neuro.get("read_history", True))

            loaded_prompts = neuro.get("account_prompts", {})
            for account_name, value in loaded_prompts.items():
                if isinstance(value, str):
                    self.account_prompts[account_name] = [value] if value.strip() else []
                else:
                    self.account_prompts[account_name] = value

            self.selected_accounts_cache = neuro.get("selected_accounts", [])
            self.update_overview()
        except Exception as error:
            print(f"Failed to load neuro settings: {error}")

    def save_settings(self, show_msg=True):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)

            if "settings" not in data:
                data["settings"] = {}

            data["settings"]["neuro_v2"] = {
                "channels": self.channels_text.toPlainText(),
                "sub_delay": self.spin_sub.value(),
                "com_delay": self.spin_com.value(),
                "chan_delay_min": self.spin_chan_min.value(),
                "chan_delay_max": self.spin_chan_max.value(),
                "mode": self.mode_combo.currentIndex(),
                "read_history": self.check_read_history.isChecked(),
                "account_prompts": self.account_prompts,
                "selected_accounts": self.get_selected_accounts(),
            }

            with open(CONFIG_FILE, "w", encoding="utf-8") as file_obj:
                json.dump(data, file_obj, ensure_ascii=False, indent=4)

            if show_msg:
                QMessageBox.information(self, "Успех", "Настройки сохранены.")
        except Exception as error:
            if show_msg:
                QMessageBox.critical(self, "Ошибка", str(error))

    def refresh_accounts(self):
        if self.is_running:
            return

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
            accounts = data.get("accounts", [])
        except Exception:
            accounts = []

        self.table.blockSignals(True)
        self.table.setRowCount(0)

        for row_index, account in enumerate(accounts):
            account_name = account.get("name", f"Acc {row_index}")
            is_valid = account.get("is_valid", True)
            invalid_reason = account.get("invalid_reason", "")

            self.table.insertRow(row_index)
            self.table.setRowHeight(row_index, 48)

            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox_item.setCheckState(
                Qt.CheckState.Checked
                if (account_name in self.selected_accounts_cache and is_valid)
                else Qt.CheckState.Unchecked
            )
            
            if not is_valid:
                checkbox_item.setBackground(QColor(239, 68, 68, 45))
                checkbox_item.setToolTip(f"⚠️ Невалидный аккаунт: {invalid_reason}")
            self.table.setItem(row_index, 0, checkbox_item)

            name_item = QTableWidgetItem(f"{account_name} (НЕВАЛИДЕН)" if not is_valid else account_name)
            if not is_valid:
                name_item.setBackground(QColor(239, 68, 68, 45))
                name_item.setToolTip(f"⚠️ Невалидный аккаунт: {invalid_reason}")
            self.table.setItem(row_index, 1, name_item)

            prompt_list = self.account_prompts.get(account_name, [])
            if not prompt_list:
                preview = "Нет промптов"
            else:
                first_prompt = prompt_list[0]
                preview = f"[{len(prompt_list)}] " + (
                    f"{first_prompt[:46]}..." if len(first_prompt) > 46 else first_prompt
                )

            preview_item = QTableWidgetItem(preview)
            preview_item.setForeground(QColor(styles.COLOR_TEXT_MUTED))
            self.table.setItem(row_index, 2, preview_item)
            self.table.setItem(row_index, 3, QTableWidgetItem("Готов"))

            btn_edit = QPushButton("Настроить")
            btn_edit.setObjectName("GhostBtn")
            btn_edit.clicked.connect(
                lambda _checked=False, name=account_name, row=row_index: self.edit_prompt(name, row)
            )
            self.table.setCellWidget(row_index, 4, btn_edit)

        self.table.blockSignals(False)
        self.update_overview()

    def edit_prompt(self, account_name, row):
        current_prompts = self.account_prompts.get(account_name, [])
        dialog = PromptDialog(account_name, current_prompts, self)
        if dialog.exec():
            new_prompts = dialog.get_prompts()
            self.account_prompts[account_name] = new_prompts

            if not new_prompts:
                preview = "Нет промптов"
            else:
                first_prompt = new_prompts[0]
                preview = f"[{len(new_prompts)}] " + (
                    f"{first_prompt[:46]}..." if len(first_prompt) > 46 else first_prompt
                )

            self.table.item(row, 2).setText(preview)
            self.update_overview()
            self.save_settings()

    def get_selected_accounts(self):
        selected = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected.append(self.table.item(row, 1).text())
        return selected

    def select_all_accounts(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.flags() & Qt.ItemFlag.ItemIsEnabled:
                item.setCheckState(Qt.CheckState.Checked)
        self.update_overview()

    def deselect_all_accounts(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.flags() & Qt.ItemFlag.ItemIsEnabled:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.update_overview()

    def toggle_running(self):
        if not self.is_running:
            self.start_neuro()
        else:
            self.stop_neuro()

    def start_neuro(self):
        self.save_settings(show_msg=False)
        selected = self.get_selected_accounts()
        if not selected:
            QMessageBox.warning(
                self, "Внимание", "Отметьте хотя бы один аккаунт в таблице."
            )
            return

        self.is_running = True
        self.is_stopping = False
        self._refresh_run_button()

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            if item.checkState() == Qt.CheckState.Checked:
                self.table.item(row, 3).setText("Запуск ядра...")

        self.engine_thread = NeuroEngineThread(selected, parent=self)
        self.engine_thread.status_updated.connect(self.on_engine_status_updated)
        self.engine_thread.stopped.connect(self.on_engine_stopped)
        self.engine_thread.start()

    def on_engine_status_updated(self, account_name, message):
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.terminal.append(f"[{time_str}] [Acc: {account_name}] {message}")

        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        if account_name == "ALL":
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item.checkState() == Qt.CheckState.Checked:
                    self.table.item(row, 3).setText(message)
            return

        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).text() == account_name:
                self.table.item(row, 3).setText(message)
                break

    def on_engine_stopped(self):
        self.is_running = False
        self.is_stopping = False
        self._refresh_run_button()

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
            if item.checkState() == Qt.CheckState.Checked:
                self.table.item(row, 3).setText("Остановлен")

    def stop_neuro(self):
        self.is_stopping = True
        self._refresh_run_button()

        if hasattr(self, "engine_thread") and self.engine_thread.isRunning():
            self.engine_thread.stop()

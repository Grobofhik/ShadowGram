import json
import os
import shutil
import random
import threading
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QMessageBox, QFileDialog,
                             QTabWidget, QCheckBox, QSpinBox, QTextEdit, QScrollArea, QProgressBar, QComboBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog)
from PyQt6.QtCore import pyqtSignal, Qt, QThread

from src.core import logic
from src.core.constants import CONFIG_FILE
from src.ui.docs_window import DocsWindow
from src import styles

"""
Страница настроек приложения.
Функции:

- init_ui: инициализация элементов управления настроек с вкладками
- load_settings: загрузка настроек из файла
- save_settings: сохранение настроек
- distribute_proxies: распределение пула прокси по профилям
- deep_clean_farm: глубокая очистка кэша всех аккаунтов
- run_export, run_import: работа с бэкапами
- check_proxy_pool: асинхронная проверка всех введенных прокси
"""

class ProxyCheckerWorker(QThread):
    progress_update = pyqtSignal(int, int) # current, total
    proxy_checked = pyqtSignal(int, str, bool) # index, proxy_url, is_valid
    finished_check = pyqtSignal(list, list) # valid_proxies, invalid_proxies

    def __init__(self, proxies):
        super().__init__()
        self.proxies = proxies

    def run(self):
        valid = []
        invalid = []
        total = len(self.proxies)
        
        for i, proxy in enumerate(self.proxies):
            is_valid = logic.check_proxy_validity(proxy)
            if is_valid:
                valid.append(proxy)
            else:
                invalid.append(proxy)
            self.proxy_checked.emit(i, proxy, is_valid)
            self.progress_update.emit(i + 1, total)
            
        self.finished_check.emit(valid, invalid)


class SettingsPage(QWidget):
    back_requested = pyqtSignal()
    settings_saved = pyqtSignal() # Сигнал для обновления UI (компактный режим)

    def __init__(self):
        super().__init__()
        self.docs_window = None
        self.proxy_worker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        btn_back = QPushButton("← Назад")
        btn_back.setObjectName("BackBtn")
        btn_back.setFixedWidth(120)
        btn_back.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(btn_back)

        header_layout.addStretch()

        btn_docs = QPushButton("📖 Документация")
        btn_docs.setFixedWidth(150)
        btn_docs.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; border: 1px solid {styles.COLOR_BORDER_DARK}; color: {'#000000' if styles.COLOR_PRIMARY == '#00E676' else '#FFFFFF'}; font-weight: bold;")
        btn_docs.clicked.connect(self.show_docs)
        header_layout.addWidget(btn_docs)

        main_layout.addLayout(header_layout)

        label_title = QLabel("Настройки")
        label_title.setObjectName("SettingsTitle")
        label_title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {styles.COLOR_PRIMARY};")
        main_layout.addWidget(label_title)

        self.tabs = QTabWidget()
        
        # 1. API & AI
        tab_api = QWidget()
        l_api = QVBoxLayout(tab_api)
        l_api.addWidget(QLabel("API ID:", objectName="SettingLabel"))
        self.input_api_id = QLineEdit(); l_api.addWidget(self.input_api_id)
        l_api.addWidget(QLabel("API Hash:", objectName="SettingLabel"))
        self.input_api_hash = QLineEdit(); l_api.addWidget(self.input_api_hash)
        l_api.addWidget(QLabel("AI API Ключ (по умолчанию):", objectName="SettingLabel"))
        self.input_ai_api_key = QLineEdit(); self.input_ai_api_key.setEchoMode(QLineEdit.EchoMode.Password); l_api.addWidget(self.input_ai_api_key)
        l_api.addWidget(QLabel("AI Base URL (по умолчанию):", objectName="SettingLabel"))
        self.input_ai_base_url = QLineEdit(); l_api.addWidget(self.input_ai_base_url)
        l_api.addWidget(QLabel("AI Название модели (по умолчанию):", objectName="SettingLabel"))
        self.input_ai_model_name = QLineEdit(); l_api.addWidget(self.input_ai_model_name)
        l_api.addStretch()
        self.tabs.addTab(tab_api, "API & AI")

        # 2. Автоматизация и Безопасность
        tab_sec = QWidget()
        l_sec = QVBoxLayout(tab_sec)
        
        l_sec.addWidget(QLabel("Массовый запуск (Задержки):", objectName="SettingLabel"))
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Задержка между запусками Telegram (сек):"))
        self.spin_launch_delay = QSpinBox()
        self.spin_launch_delay.setRange(0, 60)
        self.spin_launch_delay.setValue(2)
        delay_layout.addWidget(self.spin_launch_delay)
        delay_layout.addStretch()
        l_sec.addLayout(delay_layout)

        l_sec.addSpacing(10)
        l_sec.addWidget(QLabel("Лимиты модулей:", objectName="SettingLabel"))
        
        flood_layout = QHBoxLayout()
        flood_layout.addWidget(QLabel("Макс. ожидание FloodWait (сек) (0 = ждать всегда):"))
        self.spin_flood_limit = QSpinBox()
        self.spin_flood_limit.setRange(0, 86400)
        self.spin_flood_limit.setValue(3600)
        flood_layout.addWidget(self.spin_flood_limit)
        flood_layout.addStretch()
        l_sec.addLayout(flood_layout)

        tasks_layout = QHBoxLayout()
        tasks_layout.addWidget(QLabel("Максимум одновременных задач в плагинах:"))
        self.spin_max_tasks = QSpinBox()
        self.spin_max_tasks.setRange(1, 100)
        self.spin_max_tasks.setValue(10)
        tasks_layout.addWidget(self.spin_max_tasks)
        tasks_layout.addStretch()
        l_sec.addLayout(tasks_layout)
        
        l_sec.addSpacing(10)
        l_sec.addWidget(QLabel("Поведение модулей:", objectName="SettingLabel"))
        self.cb_stealth_mode = QCheckBox("Режим Невидимки (+50% ко всем паузам в модулях)")
        l_sec.addWidget(self.cb_stealth_mode)
        
        l_sec.addStretch()
        self.tabs.addTab(tab_sec, "Автоматизация")

        # 3. Прокси Пул
        tab_proxy = QWidget()
        l_proxy = QVBoxLayout(tab_proxy)
        
        l_proxy.addWidget(QLabel("Быстрое добавление прокси (по одному на строку, http/socks5):", objectName="SettingLabel"))
        
        import_layout = QHBoxLayout()
        self.text_proxy_pool = QTextEdit()
        self.text_proxy_pool.setPlaceholderText("socks5://user:pass@192.168.1.1:1080\nhttp://user:pass@10.0.0.1:8080")
        self.text_proxy_pool.setFixedHeight(80)
        import_layout.addWidget(self.text_proxy_pool, 1)
        
        import_btns = QVBoxLayout()
        btn_add_to_pool = QPushButton("Добавить в пул")
        btn_add_to_pool.setStyleSheet("background-color: #00796b; color: white; font-weight: bold;")
        btn_add_to_pool.clicked.connect(self.add_text_to_pool)
        
        btn_clear_input = QPushButton("Очистить поле")
        btn_clear_input.clicked.connect(self.text_proxy_pool.clear)
        
        import_btns.addWidget(btn_add_to_pool)
        import_btns.addWidget(btn_clear_input)
        import_layout.addLayout(import_btns)
        l_proxy.addLayout(import_layout)
        
        l_proxy.addWidget(QLabel("Текущий пул прокси:", objectName="SettingLabel"))
        self.table_proxy_pool = QTableWidget()
        self.table_proxy_pool.setColumnCount(4)
        self.table_proxy_pool.setHorizontalHeaderLabels(["Прокси", "Протокол", "Статус", "Действие"])
        self.table_proxy_pool.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_proxy_pool.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_proxy_pool.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_proxy_pool.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_proxy_pool.setStyleSheet(f"""
            QTableWidget {{
                background-color: {styles.COLOR_CONSOLE_BG};
                border: 1px solid {styles.COLOR_BORDER};
                color: #B0BEC5;
                gridline-color: {styles.COLOR_BORDER};
            }}
            QHeaderView::section {{
                background-color: {styles.COLOR_ACCENT_BG};
                color: {styles.COLOR_PRIMARY};
                padding: 6px;
                border: 1px solid {styles.COLOR_BORDER};
            }}
        """)
        l_proxy.addWidget(self.table_proxy_pool)
        
        self.cb_overwrite_proxies = QCheckBox("Перезаписывать прокси у аккаунтов, у которых они уже настроены")
        self.cb_overwrite_proxies.setChecked(True)
        l_proxy.addWidget(self.cb_overwrite_proxies)
        
        self.proxy_progress = QProgressBar()
        self.proxy_progress.setVisible(False)
        l_proxy.addWidget(self.proxy_progress)

        proxy_btns = QHBoxLayout()
        
        self.btn_check_pool = QPushButton("Проверить весь пул")
        self.btn_check_pool.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: {'#000000' if styles.COLOR_PRIMARY == '#00E676' else '#FFFFFF'}; font-weight: bold;")
        self.btn_check_pool.clicked.connect(self.check_proxy_pool)
        proxy_btns.addWidget(self.btn_check_pool)
        
        btn_remove_dead = QPushButton("Удалить нерабочие")
        btn_remove_dead.setStyleSheet("background-color: #c62828; color: white;")
        btn_remove_dead.clicked.connect(self.remove_dead_proxies)
        proxy_btns.addWidget(btn_remove_dead)

        self.btn_distribute = QPushButton("Распределить по аккаунтам")
        self.btn_distribute.setStyleSheet("background-color: #ff9800; color: white;")
        self.btn_distribute.clicked.connect(self.distribute_proxies)
        proxy_btns.addWidget(self.btn_distribute)
        
        btn_clear_pool = QPushButton("Очистить весь пул")
        btn_clear_pool.clicked.connect(self.clear_proxy_pool)
        proxy_btns.addWidget(btn_clear_pool)
        
        l_proxy.addLayout(proxy_btns)
        self.tabs.addTab(tab_proxy, "Прокси")

        # 3.5. Вкладка Аккаунты и Прокси
        tab_accounts_proxy = QWidget()
        l_acc_proxy = QVBoxLayout(tab_accounts_proxy)
        l_acc_proxy.addWidget(QLabel("Прокси, подключенные к аккаунтам:", objectName="SettingLabel"))
        
        self.table_accounts_proxy = QTableWidget()
        self.table_accounts_proxy.setColumnCount(3)
        self.table_accounts_proxy.setHorizontalHeaderLabels(["Аккаунт", "Текущий прокси", "Действия"])
        self.table_accounts_proxy.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_accounts_proxy.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_accounts_proxy.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_accounts_proxy.setStyleSheet(f"""
            QTableWidget {{
                background-color: {styles.COLOR_CONSOLE_BG};
                border: 1px solid {styles.COLOR_BORDER};
                color: #B0BEC5;
                gridline-color: {styles.COLOR_BORDER};
            }}
            QHeaderView::section {{
                background-color: {styles.COLOR_ACCENT_BG};
                color: {styles.COLOR_PRIMARY};
                padding: 6px;
                border: 1px solid {styles.COLOR_BORDER};
            }}
        """)
        l_acc_proxy.addWidget(self.table_accounts_proxy)
        
        batch_layout = QHBoxLayout()
        btn_reset_all_proxies = QPushButton("Сбросить прокси у всех аккаунтов")
        btn_reset_all_proxies.setStyleSheet("background-color: #d32f2f; color: white;")
        btn_reset_all_proxies.clicked.connect(self.reset_all_account_proxies)
        batch_layout.addWidget(btn_reset_all_proxies)
        batch_layout.addStretch()
        l_acc_proxy.addLayout(batch_layout)
        
        self.tabs.addTab(tab_accounts_proxy, "Аккаунты & Прокси")

        # 4. Обслуживание
        tab_maint = QWidget()
        l_maint = QVBoxLayout(tab_maint)
        
        l_maint.addWidget(QLabel("Очистка данных:", objectName="SettingLabel"))
        self.cb_auto_clean = QCheckBox("Автоматически чистить кэш профиля при закрытии Telegram")
        l_maint.addWidget(self.cb_auto_clean)
        
        log_layout = QHBoxLayout()
        log_layout.addWidget(QLabel("Очищать логи старше (дней):"))
        self.spin_log_days = QSpinBox()
        self.spin_log_days.setRange(1, 365)
        self.spin_log_days.setValue(7)
        log_layout.addWidget(self.spin_log_days)
        log_layout.addStretch()
        l_maint.addLayout(log_layout)
        
        l_maint.addSpacing(20)
        btn_clean_logs = QPushButton("Очистить устаревшие логи сейчас")
        btn_clean_logs.clicked.connect(self.clean_old_logs)
        l_maint.addWidget(btn_clean_logs)

        btn_deep_clean = QPushButton("Глубокая очистка кэша всей фермы")
        btn_deep_clean.setStyleSheet("background-color: #d32f2f; color: white;")
        btn_deep_clean.clicked.connect(self.deep_clean_farm)
        l_maint.addWidget(btn_deep_clean)

        l_maint.addSpacing(20)
        l_maint.addWidget(QLabel("Управление модулями:", objectName="SettingLabel"))
        btn_import_module = QPushButton("📥 Импорт нового модуля (.py)")
        btn_import_module.setStyleSheet("background-color: #00796b; color: white;")
        btn_import_module.clicked.connect(self.import_module)
        l_maint.addWidget(btn_import_module)

        l_maint.addStretch()
        self.tabs.addTab(tab_maint, "Данные и Обслуживание")

        # 5. Интерфейс
        tab_ui = QWidget()
        l_ui = QVBoxLayout(tab_ui)
        self.cb_compact_mode = QCheckBox("Компактный режим (уменьшенные строки аккаунтов)")
        l_ui.addWidget(self.cb_compact_mode)
        
        l_ui.addSpacing(10)
        l_ui.addWidget(QLabel("Тема оформления интерфейса:", objectName="SettingLabel"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Кибер-зеленый (Cyber Green)", "Глубокий синий (Deep Blue)"])
        l_ui.addWidget(self.combo_theme)
        
        l_ui.addStretch()
        self.tabs.addTab(tab_ui, "Интерфейс")

        # 6. Бэкапы
        tab_backup = QWidget()
        l_backup = QVBoxLayout(tab_backup)
        l_backup.addWidget(QLabel("Управление резервными копиями:", objectName="SettingLabel"))
        
        btn_export = QPushButton("📤 Экспорт всех данных (ZIP)")
        btn_export.setFixedHeight(40)
        btn_export.clicked.connect(self.run_export)
        l_backup.addWidget(btn_export)

        btn_import = QPushButton("📥 Импорт из бэкапа (ZIP)")
        btn_import.setFixedHeight(40)
        btn_import.clicked.connect(self.run_import)
        l_backup.addWidget(btn_import)
        l_backup.addStretch()
        self.tabs.addTab(tab_backup, "Бэкапы")

        # 7. Управление фермами
        tab_farms = QWidget()
        l_farms = QVBoxLayout(tab_farms)
        l_farms.setSpacing(15)
        
        l_farms.addWidget(QLabel("Текущая активная ферма:", objectName="SettingLabel"))
        self.label_active_farm = QLabel("default")
        self.label_active_farm.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {styles.COLOR_PRIMARY}; padding: 12px; background-color: {styles.COLOR_ACCENT_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 8px;")
        l_farms.addWidget(self.label_active_farm)
        
        l_farms.addWidget(QLabel("Выбрать активную ферму:", objectName="SettingLabel"))
        farm_select_layout = QHBoxLayout()
        self.combo_farms = QComboBox()
        self.combo_farms.setStyleSheet(f"QComboBox {{ background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 8px; color: {styles.COLOR_PRIMARY}; }}")
        farm_select_layout.addWidget(self.combo_farms, 1)
        
        btn_switch_farm = QPushButton("Переключить")
        btn_switch_farm.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: {'#000000' if styles.COLOR_PRIMARY == '#00E676' else '#FFFFFF'}; font-weight: bold; height: 35px;")
        btn_switch_farm.clicked.connect(self.switch_farm)
        farm_select_layout.addWidget(btn_switch_farm)
        l_farms.addLayout(farm_select_layout)
        
        l_farms.addWidget(QLabel("Создать новую ферму:", objectName="SettingLabel"))
        farm_create_layout = QHBoxLayout()
        self.input_new_farm = QLineEdit()
        self.input_new_farm.setPlaceholderText("Имя новой фермы (например: crypto_farm)")
        farm_create_layout.addWidget(self.input_new_farm, 1)
        
        btn_create_farm = QPushButton("Создать")
        btn_create_farm.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: {'#000000' if styles.COLOR_PRIMARY == '#00E676' else '#FFFFFF'}; font-weight: bold; height: 35px;")
        btn_create_farm.clicked.connect(self.create_farm)
        farm_create_layout.addWidget(btn_create_farm)
        l_farms.addLayout(farm_create_layout)
        
        l_farms.addStretch()
        self.tabs.addTab(tab_farms, "Фермы")

        main_layout.addWidget(self.tabs)

        btn_save = QPushButton("💾 Сохранить настройки")
        btn_save.setFixedHeight(45)
        btn_save.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: {'#000000' if styles.COLOR_PRIMARY == '#00E676' else '#FFFFFF'}; font-weight: bold; font-size: 14px;")
        btn_save.clicked.connect(self.save_settings)
        main_layout.addWidget(btn_save)

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

    def add_proxy_to_table(self, proxy_str: str, status: str = "Не проверен"):
        normalized = logic.normalize_proxy_url(proxy_str)
        if not normalized:
            return
        
        # Determine protocol
        proto = "HTTP"
        if normalized.startswith("socks5://"):
            proto = "SOCKS5"
        elif normalized.startswith("socks4://"):
            proto = "SOCKS4"
        elif normalized.startswith("https://"):
            proto = "HTTPS"
            
        row = self.table_proxy_pool.rowCount()
        self.table_proxy_pool.insertRow(row)
        
        # Proxy item
        item_proxy = QTableWidgetItem(normalized)
        item_proxy.setFlags(item_proxy.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table_proxy_pool.setItem(row, 0, item_proxy)
        
        # Protocol item
        item_proto = QTableWidgetItem(proto)
        item_proto.setFlags(item_proto.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table_proxy_pool.setItem(row, 1, item_proto)
        
        # Status item
        item_status = QTableWidgetItem(status)
        item_status.setFlags(item_status.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if status == "Рабочий":
            item_status.setForeground(Qt.GlobalColor.green)
        elif status == "Мертвый":
            item_status.setForeground(Qt.GlobalColor.red)
        elif status.startswith("Проверяется") or status == "Проверка...":
            item_status.setForeground(Qt.GlobalColor.yellow)
        else:
            item_status.setForeground(Qt.GlobalColor.gray)
        self.table_proxy_pool.setItem(row, 2, item_status)
        
        # Action button
        btn_delete = QPushButton("Удалить")
        btn_delete.setStyleSheet("background-color: #c62828; color: white; padding: 2px 6px; font-size: 11px;")
        btn_delete.clicked.connect(self.delete_proxy_row)
        self.table_proxy_pool.setCellWidget(row, 3, btn_delete)

    def delete_proxy_row(self):
        button = self.sender()
        if button:
            index = self.table_proxy_pool.indexAt(button.pos())
            if index.isValid():
                self.table_proxy_pool.removeRow(index.row())

    def add_text_to_pool(self):
        text = self.text_proxy_pool.toPlainText().strip()
        if not text:
            return
        proxies = [p.strip() for p in text.split('\n') if p.strip()]
        for p in proxies:
            self.add_proxy_to_table(p)
        self.text_proxy_pool.clear()

    def clear_proxy_pool(self):
        self.table_proxy_pool.setRowCount(0)

    def remove_dead_proxies(self):
        row = 0
        while row < self.table_proxy_pool.rowCount():
            status_item = self.table_proxy_pool.item(row, 2)
            if status_item and status_item.text() == "Мертвый":
                self.table_proxy_pool.removeRow(row)
            else:
                row += 1

    def load_accounts_proxy_table(self, accounts):
        self.table_accounts_proxy.setRowCount(0)
        for acc in accounts:
            row = self.table_accounts_proxy.rowCount()
            self.table_accounts_proxy.insertRow(row)
            
            # Name item
            item_name = QTableWidgetItem(acc.get("name", ""))
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_accounts_proxy.setItem(row, 0, item_name)
            
            # Proxy item
            item_proxy = QTableWidgetItem(acc.get("proxy_url", ""))
            self.table_accounts_proxy.setItem(row, 1, item_proxy)
            
            # Action layout
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(2, 2, 2, 2)
            layout.setSpacing(4)
            
            btn_edit = QPushButton("Изменить")
            btn_edit.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: {'#000000' if styles.COLOR_PRIMARY == '#00E676' else '#FFFFFF'}; padding: 2px 6px; font-size: 11px; font-weight: bold;")
            btn_edit.clicked.connect(self.edit_account_proxy)
            
            btn_clear = QPushButton("Удалить")
            btn_clear.setStyleSheet("background-color: #c62828; color: white; padding: 2px 6px; font-size: 11px;")
            btn_clear.clicked.connect(self.clear_account_proxy)
            
            layout.addWidget(btn_edit)
            layout.addWidget(btn_clear)
            widget.setLayout(layout)
            self.table_accounts_proxy.setCellWidget(row, 2, widget)

    def edit_account_proxy(self):
        button = self.sender()
        if button:
            widget = button.parentWidget()
            index = self.table_accounts_proxy.indexAt(widget.pos())
            if index.isValid():
                row = index.row()
                current_val = ""
                item_proxy = self.table_accounts_proxy.item(row, 1)
                if item_proxy:
                    current_val = item_proxy.text()
                
                new_proxy, ok = QInputDialog.getText(self, "Изменить прокси", "Введите прокси:", text=current_val)
                if ok:
                    normalized = logic.normalize_proxy_url(new_proxy)
                    if item_proxy:
                        item_proxy.setText(normalized)
                    else:
                        self.table_accounts_proxy.setItem(row, 1, QTableWidgetItem(normalized))

    def clear_account_proxy(self):
        button = self.sender()
        if button:
            widget = button.parentWidget()
            index = self.table_accounts_proxy.indexAt(widget.pos())
            if index.isValid():
                row = index.row()
                item_proxy = self.table_accounts_proxy.item(row, 1)
                if item_proxy:
                    item_proxy.setText("")

    def reset_all_account_proxies(self):
        reply = QMessageBox.question(
            self, 
            "Сброс прокси", 
            "Вы уверены, что хотите удалить прокси у ВСЕХ аккаунтов?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for r in range(self.table_accounts_proxy.rowCount()):
                item = self.table_accounts_proxy.item(r, 1)
                if item:
                    item.setText("")

    def load_settings(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
                s = data.get("settings", {})
                
                # API
                self.input_api_id.setText(str(s.get("api_id", "")))
                self.input_api_hash.setText(s.get("api_hash", ""))
                self.input_ai_api_key.setText(s.get("default_ai_api_key", ""))
                self.input_ai_base_url.setText(s.get("default_ai_base_url", "https://api.groq.com/openai/v1"))
                self.input_ai_model_name.setText(s.get("default_ai_model_name", "llama-3.1-8b-instant"))
                
                # Security & Automation
                self.spin_launch_delay.setValue(s.get("launch_delay", 2))
                self.spin_flood_limit.setValue(s.get("max_flood_wait", 3600))
                self.spin_max_tasks.setValue(s.get("max_concurrent_tasks", 10))
                self.cb_stealth_mode.setChecked(s.get("stealth_mode", False))
                
                # Maintenance & UI
                self.cb_auto_clean.setChecked(s.get("auto_clean_cache", False))
                self.spin_log_days.setValue(s.get("log_rotation_days", 7))
                self.cb_compact_mode.setChecked(s.get("compact_mode", False))
                theme_val = s.get("theme", "green")
                self.combo_theme.setCurrentIndex(1 if theme_val == "blue" else 0)
                
                # Proxy Pool loading
                self.table_proxy_pool.setRowCount(0)
                pool = s.get("proxy_pool", [])
                for p in pool:
                    self.add_proxy_to_table(p)
                
                # Overwrite checkbox
                self.cb_overwrite_proxies.setChecked(s.get("overwrite_proxies", True))
                
                # Accounts and Proxies loading
                accounts = data.get("accounts", [])
                self.load_accounts_proxy_table(accounts)
                
            # Farms loading
            self.label_active_farm.setText(logic.get_active_farm_name())
            self.combo_farms.clear()
            farms = logic.list_available_farms()
            self.combo_farms.addItems(farms)
            active_name = logic.get_active_farm_name()
            idx = self.combo_farms.findText(active_name)
            if idx >= 0:
                self.combo_farms.setCurrentIndex(idx)
        except Exception as e:
            import traceback
            traceback.print_exc()

    def save_settings(self):
        try:
            data = {"settings": {}, "accounts": []}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            
            # Gather proxy pool list from table
            pool_list = []
            for r in range(self.table_proxy_pool.rowCount()):
                item = self.table_proxy_pool.item(r, 0)
                if item and item.text():
                    pool_list.append(item.text())
            
            data["settings"].update({
                "api_id": int(self.input_api_id.text()) if self.input_api_id.text().isdigit() else 0, 
                "api_hash": self.input_api_hash.text().strip(),
                "default_ai_api_key": self.input_ai_api_key.text().strip(),
                "default_ai_base_url": self.input_ai_base_url.text().strip(),
                "default_ai_model_name": self.input_ai_model_name.text().strip(),
                "launch_delay": self.spin_launch_delay.value(),
                "max_flood_wait": self.spin_flood_limit.value(),
                "max_concurrent_tasks": self.spin_max_tasks.value(),
                "stealth_mode": self.cb_stealth_mode.isChecked(),
                "auto_clean_cache": self.cb_auto_clean.isChecked(),
                "log_rotation_days": self.spin_log_days.value(),
                "compact_mode": self.cb_compact_mode.isChecked(),
                "theme": "blue" if self.combo_theme.currentIndex() == 1 else "green",
                "proxy_pool": pool_list,
                "overwrite_proxies": self.cb_overwrite_proxies.isChecked()
            })
            
            # Get updated accounts from Accounts & Proxies table
            accounts = data.get("accounts", [])
            for r in range(self.table_accounts_proxy.rowCount()):
                name_item = self.table_accounts_proxy.item(r, 0)
                proxy_item = self.table_accounts_proxy.item(r, 1)
                if name_item and proxy_item:
                    name = name_item.text()
                    proxy_val = proxy_item.text().strip()
                    for acc in accounts:
                        if acc.get("name") == name:
                            acc["proxy_url"] = proxy_val
                            break
            
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
            logic.save_active_farm_config()
            self.settings_saved.emit()
            QMessageBox.information(self, "Успех", "Настройки сохранены!")
        except Exception as e: QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def save_settings_silently(self):
        try:
            data = {"settings": {}, "accounts": []}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            
            # Gather proxy pool list from table
            pool_list = []
            for r in range(self.table_proxy_pool.rowCount()):
                item = self.table_proxy_pool.item(r, 0)
                if item and item.text():
                    pool_list.append(item.text())
            
            data["settings"].update({
                "api_id": int(self.input_api_id.text()) if self.input_api_id.text().isdigit() else 0, 
                "api_hash": self.input_api_hash.text().strip(),
                "default_ai_api_key": self.input_ai_api_key.text().strip(),
                "default_ai_base_url": self.input_ai_base_url.text().strip(),
                "default_ai_model_name": self.input_ai_model_name.text().strip(),
                "launch_delay": self.spin_launch_delay.value(),
                "max_flood_wait": self.spin_flood_limit.value(),
                "max_concurrent_tasks": self.spin_max_tasks.value(),
                "stealth_mode": self.cb_stealth_mode.isChecked(),
                "auto_clean_cache": self.cb_auto_clean.isChecked(),
                "log_rotation_days": self.spin_log_days.value(),
                "compact_mode": self.cb_compact_mode.isChecked(),
                "theme": "blue" if self.combo_theme.currentIndex() == 1 else "green",
                "proxy_pool": pool_list,
                "overwrite_proxies": self.cb_overwrite_proxies.isChecked()
            })
            
            # Get updated accounts from Accounts & Proxies table
            accounts = data.get("accounts", [])
            for r in range(self.table_accounts_proxy.rowCount()):
                name_item = self.table_accounts_proxy.item(r, 0)
                proxy_item = self.table_accounts_proxy.item(r, 1)
                if name_item and proxy_item:
                    name = name_item.text()
                    proxy_val = proxy_item.text().strip()
                    for acc in accounts:
                        if acc.get("name") == name:
                            acc["proxy_url"] = proxy_val
                            break
            
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
            logic.save_active_farm_config()
        except:
            pass

    def switch_farm(self):
        target_farm = self.combo_farms.currentText()
        if not target_farm:
            return
        
        current_farm = logic.get_active_farm_name()
        if target_farm == current_farm:
            return
            
        reply = QMessageBox.question(
            self, 
            "Переключение фермы", 
            f"Вы уверены, что хотите переключиться на ферму '{target_farm}'?\nЭто перезагрузит список аккаунтов.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.save_settings_silently()
            if logic.switch_active_farm(target_farm):
                self.load_settings()
                self.settings_saved.emit()
                QMessageBox.information(self, "Фермы", f"Вы успешно переключились на ферму '{target_farm}'!")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось переключить ферму.")

    def create_farm(self):
        name = self.input_new_farm.text().strip()
        if not name:
            QMessageBox.warning(self, "Внимание", "Введите имя новой фермы!")
            return
            
        if logic.create_new_farm(name):
            self.input_new_farm.clear()
            self.load_settings()
            idx = self.combo_farms.findText(name)
            if idx >= 0:
                self.combo_farms.setCurrentIndex(idx)
            QMessageBox.information(self, "Фермы", f"Ферма '{name}' успешно создана!\nВы можете выбрать её в списке и переключиться.")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось создать ферму. Возможно, она уже существует или имя содержит недопустимые символы.")

    def check_proxy_pool(self):
        proxies = []
        for r in range(self.table_proxy_pool.rowCount()):
            item = self.table_proxy_pool.item(r, 0)
            if item and item.text():
                proxies.append(item.text())
                status_item = self.table_proxy_pool.item(r, 2)
                if status_item:
                    status_item.setText("Проверка...")
                    status_item.setForeground(Qt.GlobalColor.yellow)
        
        if not proxies:
            QMessageBox.warning(self, "Ошибка", "Пул прокси пуст!")
            return
            
        self.btn_check_pool.setEnabled(False)
        self.btn_distribute.setEnabled(False)
        self.proxy_progress.setVisible(True)
        self.proxy_progress.setMaximum(len(proxies))
        self.proxy_progress.setValue(0)
        
        self.proxy_worker = ProxyCheckerWorker(proxies)
        self.proxy_worker.progress_update.connect(self.proxy_progress.setValue)
        self.proxy_worker.proxy_checked.connect(self.on_proxy_checked_row)
        self.proxy_worker.finished_check.connect(self.on_pool_checked)
        self.proxy_worker.start()

    def on_proxy_checked_row(self, index, proxy_url, is_valid):
        if index < self.table_proxy_pool.rowCount():
            status_item = self.table_proxy_pool.item(index, 2)
            if status_item:
                if is_valid:
                    status_item.setText("Рабочий")
                    status_item.setForeground(Qt.GlobalColor.green)
                else:
                    status_item.setText("Мертвый")
                    status_item.setForeground(Qt.GlobalColor.red)

    def on_pool_checked(self, valid, invalid):
        self.btn_check_pool.setEnabled(True)
        self.btn_distribute.setEnabled(True)
        self.proxy_progress.setVisible(False)
        
        msg = f"Проверка завершена!\n\nРабочих: {len(valid)}\nМертвых: {len(invalid)}"
        if invalid:
            msg += "\n\nВы можете удалить мертвые прокси кнопкой 'Удалить нерабочие'."
            
        QMessageBox.information(self, "Результат", msg)

    def distribute_proxies(self):
        proxies = []
        for r in range(self.table_proxy_pool.rowCount()):
            item = self.table_proxy_pool.item(r, 0)
            if item and item.text():
                proxies.append(item.text())
                
        if not proxies:
            QMessageBox.warning(self, "Ошибка", "Пул прокси пуст!")
            return
            
        reply = QMessageBox.question(self, "Распределение", f"Найдено {len(proxies)} прокси в пуле. Перемешать и распределить их по профилям?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                data = {"settings": {}, "accounts": []}
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
                
                accounts = data.get("accounts", [])
                if not accounts:
                    QMessageBox.warning(self, "Ошибка", "Нет созданных аккаунтов!")
                    return

                overwrite = self.cb_overwrite_proxies.isChecked()
                
                # Фильтруем аккаунты, если перезапись отключена
                target_accounts = accounts if overwrite else [acc for acc in accounts if not acc.get("proxy_url")]
                
                if not target_accounts:
                    QMessageBox.information(self, "Инфо", "Все аккаунты уже имеют настроенный прокси. Распределение пропущено.")
                    return
                
                random.shuffle(proxies)
                proxy_count = len(proxies)
                
                updated = 0
                for i, acc in enumerate(target_accounts):
                    acc["proxy_url"] = proxies[i % proxy_count]
                    updated += 1
                
                with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
                logic.save_active_farm_config()
                
                self.load_settings()
                QMessageBox.information(self, "Готово", f"Прокси успешно распределены по {updated} аккаунтам. Обновите список на главной.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def clean_old_logs(self):
        days = self.spin_log_days.value()
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0
        
        try:
            data = logic.load_config(CONFIG_FILE)
            for acc in data:
                workdir = acc.get("workdir")
                if not workdir or not os.path.exists(workdir): continue
                
                for filename in ["telegram_error.log", "gost_module.log"]:
                    filepath = os.path.join(workdir, filename)
                    if os.path.exists(filepath):
                        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                        if mtime < cutoff:
                            os.remove(filepath)
                            deleted += 1
                            
            QMessageBox.information(self, "Готово", f"Удалено {deleted} старых файлов логов.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def deep_clean_farm(self):
        reply = QMessageBox.question(self, "Глубокая очистка", "Вы уверены, что хотите удалить кэш и временные файлы из ВСЕХ профилей? Это может занять время.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                data = {"settings": {}, "accounts": []}
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
                
                accounts = data.get("accounts", [])
                total_cleaned = 0
                
                for acc in accounts:
                    success, _ = logic.clear_cache(acc["workdir"])
                    if success:
                        total_cleaned += 1
                
                QMessageBox.information(self, "Готово", f"Глубокая очистка завершена.\nОчищено профилей: {total_cleaned}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

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

    def import_module(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл модуля Python", "", "Python Files (*.py)")
        if file_path:
            try:
                dest_dir = os.path.join(os.getcwd(), "src", "modules", "plugins")
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, os.path.basename(file_path))
                
                shutil.copy2(file_path, dest_path)
                QMessageBox.information(self, "Успех", f"Модуль успешно импортирован!\nПерейдите в 'Модули' и обновите список.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось скопировать модуль: {e}")
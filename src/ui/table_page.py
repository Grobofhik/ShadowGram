from src.core.constants import *
from PyQt6.QtGui import QIcon
import os
import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QHBoxLayout, QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from src.core.managers import config_manager
from src.core.constants import CONFIG_FILE
from src import styles
import time
import socket
import re

class ProxyCheckThread(QThread):
    result_signal = pyqtSignal(int, bool)
    finished_signal = pyqtSignal()
    
    def __init__(self, items_to_check):
        super().__init__()
        self.items_to_check = items_to_check # list of (row, proxy_str)
        self._is_running = True
        
    def stop(self):
        self._is_running = False
        
    def run(self):
        for row, proxy_str in self.items_to_check:
            if not self._is_running:
                break
                
            if not proxy_str or proxy_str.strip() == "":
                continue
                
            alive = False
            try:
                # Basic IP/Port extraction logic
                match = re.search(r'(?:(?:socks5|http)://)?(?:[^:@]+:[^:@]+@)?([\d\.]+):(\d+)', proxy_str)
                if not match:
                    match = re.search(r'([\d\.]+):(\d+)', proxy_str)
                    
                if match:
                    ip = match.group(1)
                    port = int(match.group(2))
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(10.0)
                    s.connect((ip, port))
                    s.close()
                    alive = True
            except Exception:
                alive = False
                
            self.result_signal.emit(row, alive)
            time.sleep(0.3)
            
        self.finished_signal.emit()

class AccountTablePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Сводная таблица аккаунтов")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {styles.COLOR_PRIMARY};")
        header_layout.addWidget(title)
        
        header_layout.addStretch()

        btn_refresh = QPushButton("Обновить")
        btn_refresh.setIcon(QIcon(str(REFRESH_ICON_PATH)))
        btn_refresh.setFixedSize(120, 35)
        btn_refresh.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 5px;")
        btn_refresh.clicked.connect(self.refresh_data)
        header_layout.addWidget(btn_refresh)
        
        btn_export = QPushButton("📥 Скачать (CSV)")
        btn_export.setFixedSize(140, 35)
        btn_export.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY}; color: black; font-weight: bold; border-radius: 5px;")
        btn_export.clicked.connect(self.export_to_csv)
        header_layout.addWidget(btn_export)

        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "✓", "Имя", "Телефон", "Privacy Guard", "API ID", "API Hash", "Proxy", "Устройство", "Email", "2FA Пароль", "Заметки"
        ])
        
        # Table Styling
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {styles.COLOR_ACCENT_BG};
                color: white;
                gridline-color: {styles.COLOR_BORDER};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 8px;
            }}
            QHeaderView::section {{
                background-color: {styles.COLOR_BG};
                color: {styles.COLOR_PRIMARY};
                font-weight: bold;
                border: 1px solid {styles.COLOR_BORDER};
                padding: 5px;
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
        """)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)
        header.setStretchLastSection(True)
        
        layout.addWidget(self.table)
        
        # Bulk Actions Footer
        footer_layout = QHBoxLayout()
        
        lbl_bulk = QLabel("⚡ Массовые действия:")
        lbl_bulk.setStyleSheet(f"font-weight: bold; color: {styles.COLOR_PRIMARY};")
        footer_layout.addWidget(lbl_bulk)
        
        btn_bulk_proxy = QPushButton("Установить Proxy")
        btn_bulk_proxy.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 5px; padding: 5px 15px;")
        btn_bulk_proxy.clicked.connect(self.bulk_set_proxy)
        footer_layout.addWidget(btn_bulk_proxy)
        
        btn_bulk_api = QPushButton("Обновить API ключи")
        btn_bulk_api.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 5px; padding: 5px 15px;")
        btn_bulk_api.clicked.connect(self.bulk_set_api)
        footer_layout.addWidget(btn_bulk_api)
        
        footer_layout.addStretch()
        
        btn_check_proxies = QPushButton("📡 Проверить все прокси")
        btn_check_proxies.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY}; color: black; font-weight: bold; border-radius: 5px; padding: 5px 15px;")
        btn_check_proxies.clicked.connect(self.check_all_proxies)
        footer_layout.addWidget(btn_check_proxies)
        
        layout.addLayout(footer_layout)
        
        self.refresh_data()

    def refresh_data(self):
        try:
            data = config_manager._read_config(CONFIG_FILE)
            accounts = data.get("accounts", [])
        except Exception:
            accounts = []

        self.table.setRowCount(len(accounts))

        for row, acc in enumerate(accounts):
            privacy_status = "АКТИВЕН"if acc.get("privacy_guard") else "УЯЗВИМ"
            items = [
                "", # Checkbox column
                acc.get("name", ""),
                acc.get("phone", ""),
                privacy_status,
                str(acc.get("api_id", "")),
                str(acc.get("api_hash", "")),
                acc.get("proxy_url", ""),
                acc.get("device_name", ""),
                acc.get("email", ""),
                acc.get("password", ""),
                acc.get("notes", "")
            ]

            for col, text in enumerate(items):
                item = QTableWidgetItem(str(text))
                if col == 0:
                    item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Make read-only
                
                # Hidden data in column 1 to identify the account
                if col == 1:
                    item.setData(Qt.ItemDataRole.UserRole, acc.get("workdir"))
                    
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()

    def export_to_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить таблицу", "accounts.csv", "CSV/Excel Files (*.csv)")
        if not file_path:
            return
            
        try:
            # utf-8-sig adds BOM so Excel automatically recognizes UTF-8 Cyrillic characters
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file, delimiter=';')
                
                # Названия колонок
                headers = []
                for col in range(self.table.columnCount()):
                    headers.append(self.table.horizontalHeaderItem(col).text())
                writer.writerow(headers)
                
                # Строки с данными
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
                    
            QMessageBox.information(self, "Успех", f"Таблица успешно сохранена в файл:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")

    def get_selected_workdirs(self):
        workdirs = []
        for row in range(self.table.rowCount()):
            checkbox_item = self.table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                name_item = self.table.item(row, 1)
                workdir = name_item.data(Qt.ItemDataRole.UserRole)
                if workdir:
                    workdirs.append(workdir)
        return workdirs

    def bulk_set_proxy(self):
        workdirs = self.get_selected_workdirs()
        if not workdirs:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы один аккаунт (поставьте галочку в первом столбце)!")
            return
            
        from PyQt6.QtWidgets import QInputDialog
        proxy, ok = QInputDialog.getText(self, "Установить Proxy", "Введите прокси (ip:port:user:pass или socks5://...):")
        if ok:
            from src.core.managers import account_manager
            for wd in workdirs:
                account_manager.update_proxy(CONFIG_FILE, wd, proxy.strip())
            self.refresh_data()
            QMessageBox.information(self, "Успех", f"Прокси установлен для {len(workdirs)} аккаунтов!")

    def bulk_set_api(self):
        workdirs = self.get_selected_workdirs()
        if not workdirs:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы один аккаунт (поставьте галочку в первом столбце)!")
            return
            
        reply = QMessageBox.question(self, "Подтверждение", f"Сгенерировать случайные официальные API ключи для {len(workdirs)} аккаунтов?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            from src.core.managers import account_manager
            from src.core.managers.api_manager import get_dynamic_api_credentials
            import time
            import random
            
            for wd in workdirs:
                seed = str(time.time() + random.random())
                creds = get_dynamic_api_credentials(seed)
                account_manager.update_api_credentials(CONFIG_FILE, wd, str(creds['api_id']), creds['api_hash'])
            self.refresh_data()
            QMessageBox.information(self, "Успех", f"Официальные API ключи присвоены {len(workdirs)} аккаунтам!")

    def check_all_proxies(self):
        items_to_check = []
        for row in range(self.table.rowCount()):
            proxy_item = self.table.item(row, 6) # Proxy is column 6
            if proxy_item and proxy_item.text().strip():
                items_to_check.append((row, proxy_item.text().strip()))
                proxy_item.setBackground(QColor(100, 100, 100)) # Reset to gray
                
        if not items_to_check:
            return
            
        self.checker_thread = ProxyCheckThread(items_to_check)
        self.checker_thread.result_signal.connect(self.update_proxy_status)
        self.checker_thread.finished_signal.connect(lambda: QMessageBox.information(self, "Готово", "Все прокси проверены!"))
        self.checker_thread.start()
        
    def update_proxy_status(self, row, is_alive):
        proxy_item = self.table.item(row, 6)
        if proxy_item:
            if is_alive:
                proxy_item.setBackground(QColor(0, 100, 0)) # Dark green
                proxy_item.setToolTip("Proxy is alive")
            else:
                proxy_item.setBackground(QColor(150, 0, 0)) # Dark red
                proxy_item.setToolTip("Proxy is unreachable")

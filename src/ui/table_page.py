import os
import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QHBoxLayout, QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from src.core.managers import config_manager
from src.core.constants import CONFIG_FILE
from src import styles

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

        btn_refresh = QPushButton("🔄 Обновить")
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
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Имя", "Телефон", "API ID", "API Hash", "Proxy", "Устройство", "Email", "2FA Пароль", "Заметки"
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
        header.setStretchLastSection(True)
        
        layout.addWidget(self.table)
        self.refresh_data()

    def refresh_data(self):
        try:
            data = config_manager._read_config(CONFIG_FILE)
            accounts = data.get("accounts", [])
        except Exception:
            accounts = []

        self.table.setRowCount(len(accounts))

        for row, acc in enumerate(accounts):
            items = [
                acc.get("name", ""),
                acc.get("phone", ""),
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
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Make read-only
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

import os
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QProgressBar, QMessageBox, QListWidget, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from src import styles
from src.core.managers import account_manager, farm_manager

try:
    from opentele.td import TDesktop
    from opentele.api import API
except ImportError:
    TDesktop = None

class ConverterWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(int, int) # success, failed

    def __init__(self, tdata_folders, farm_path):
        super().__init__()
        self.tdata_folders = tdata_folders
        self.farm_path = Path(farm_path)

    def run(self):
        if not TDesktop:
            self.progress.emit(0, "Ошибка: не установлена библиотека opentele!")
            self.finished.emit(0, len(self.tdata_folders))
            return

        success = 0
        failed = 0
        total = len(self.tdata_folders)

        for i, folder in enumerate(self.tdata_folders):
            try:
                self.progress.emit(int(i / total * 100), f"Конвертация: {folder.name}...")
                
                # Создаем tdesktop инстанс
                tdesk = TDesktop(str(folder))
                
                # Генерируем уникальный workdir
                import uuid
                acc_id = str(uuid.uuid4())[:8]
                new_workdir = self.farm_path / "accounts" / f"converted_{acc_id}"
                new_workdir.mkdir(parents=True, exist_ok=True)
                
                # Конвертируем в Telethon MemorySession для получения ключей
                client = tdesk.ToTelethon(session=None, api_id=2040, api_hash="b18441a1ff607e10a989891a5462e627")
                
                auth_key = client.session.auth_key.key
                dc_id = client.session.dc_id
                
                # Создаем Hydrogram/Pyrogram совместимую SQLite базу данных (.session)
                import sqlite3
                import time
                
                session_path = new_workdir / f"{acc_id}.session"
                with sqlite3.connect(str(session_path)) as db:
                    db.execute("""CREATE TABLE sessions (
                        dc_id INTEGER PRIMARY KEY,
                        api_id INTEGER,
                        test_mode INTEGER,
                        auth_key BLOB,
                        date INTEGER,
                        user_id INTEGER,
                        is_bot INTEGER
                    )""")
                    db.execute("""CREATE TABLE peers (
                        id INTEGER PRIMARY KEY,
                        access_hash INTEGER,
                        type INTEGER,
                        username TEXT,
                        phone_number TEXT,
                        last_update_on INTEGER DEFAULT (CAST(STRFTIME('%s', 'now') AS INTEGER))
                    )""")
                    db.execute("""CREATE TABLE version (
                        number INTEGER PRIMARY KEY
                    )""")
                    db.execute("INSERT INTO version VALUES (3)")
                    db.execute(
                        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (dc_id, 2040, 0, auth_key, int(time.time()), 9999, 0)
                    )
                    db.commit()
                
                # Для 100% поддержки Pyrogram сессий из tdata нужен скрипт конвертации SQLite базы,
                # пока просто скопируем саму tdata чтобы она не потерялась
                shutil.copytree(folder, new_workdir / "tdata", dirs_exist_ok=True)
                
                from src.core.managers.config_manager import _read_config, _write_config
                config_file = self.farm_path / "config.json"
                
                account_manager.add_account(
                    config_file, 
                    str(new_workdir), 
                    api_id="2040", 
                    api_hash="b18441a1ff607e10a989891a5462e627"
                )
                
                success += 1
            except Exception as e:
                print(f"Converter error: {e}")
                failed += 1

        self.progress.emit(100, "Готово!")
        self.finished.emit(success, failed)


class TDataConverterWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tdata_folders = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Конвертер tdata -> session")
        self.setStyleSheet(f"background-color: {styles.COLOR_BG}; color: {styles.COLOR_TEXT_MAIN};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 10px; }}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)

        info_lbl = QLabel("Конвертируйте папки tdata от Telegram Desktop в .session файлы, готовые к использованию в ферме. Загрузите папки и начните процесс.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 14px; border: none;")
        card_layout.addWidget(info_lbl)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {styles.COLOR_CONSOLE_BG}; 
                border: 1px solid {styles.COLOR_BORDER}; 
                border-radius: 8px; 
                padding: 10px;
                font-size: 13px;
                color: {styles.COLOR_TEXT_MAIN};
            }}
            QListWidget::item {{
                padding: 5px;
            }}
        """)
        card_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("📁 Добавить tdata папки")
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_HOVER_BG};
                color: {styles.COLOR_TEXT_MAIN};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 10px 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_BORDER};
            }}
        """)
        self.btn_add.clicked.connect(self.add_folders)

        self.btn_clear = QPushButton("🗑 Очистить")
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{
                background-color: #ef4444;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #dc2626;
            }}
        """)
        self.btn_clear.clicked.connect(self.clear_folders)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_clear)
        card_layout.addLayout(btn_layout)

        self.lbl_status = QLabel("Ожидание...")
        self.lbl_status.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-style: italic; border: none;")
        card_layout.addWidget(self.lbl_status)

        self.progress = QProgressBar()
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                text-align: center;
                background-color: {styles.COLOR_CONSOLE_BG};
                color: {styles.COLOR_TEXT_MAIN};
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {styles.COLOR_PRIMARY};
                border-radius: 5px;
            }}
        """)
        self.progress.setValue(0)
        card_layout.addWidget(self.progress)

        self.btn_start = QPushButton("🚀 Начать конвертацию")
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_PRIMARY};
                color: #000000;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 15px;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_PRIMARY_LIGHT};
            }}
            QPushButton:disabled {{
                background-color: {styles.COLOR_HOVER_BG};
                color: {styles.COLOR_TEXT_MUTED};
            }}
        """)
        self.btn_start.clicked.connect(self.start_conversion)
        card_layout.addWidget(self.btn_start)

        layout.addWidget(card)

    def add_folders(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку, содержащую tdata")
        if folder:
            # Ищем tdata внутри, или это и есть tdata
            path = Path(folder)
            if path.name.lower() == "tdata":
                if path not in self.tdata_folders:
                    self.tdata_folders.append(path)
                    self.list_widget.addItem(str(path))
            else:
                tdata_path = path / "tdata"
                if tdata_path.exists():
                    if tdata_path not in self.tdata_folders:
                        self.tdata_folders.append(tdata_path)
                        self.list_widget.addItem(str(tdata_path))
                else:
                    QMessageBox.warning(self, "Ошибка", "В выбранной папке не найдена папка 'tdata'.")

    def clear_folders(self):
        self.tdata_folders.clear()
        self.list_widget.clear()

    def start_conversion(self):
        if not self.tdata_folders:
            return
            
        if not TDesktop:
            QMessageBox.critical(self, "Ошибка", "Не установлена библиотека opentele. Выполните pip install opentele")
            return

        farm_name = farm_manager.get_active_farm_name()
        if not farm_name:
            return
            
        from src.core.constants import FARMS_DIR
        farm_path = FARMS_DIR / farm_name

        self.btn_start.setEnabled(False)
        self.btn_add.setEnabled(False)
        
        self.worker = ConverterWorker(self.tdata_folders, farm_path)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def update_progress(self, val, text):
        self.progress.setValue(val)
        self.lbl_status.setText(text)

    def on_finished(self, success, failed):
        self.btn_start.setEnabled(True)
        self.btn_add.setEnabled(True)
        QMessageBox.information(self, "Готово", f"Конвертация завершена!\nУспешно: {success}\nОшибок: {failed}")
        self.clear_folders()

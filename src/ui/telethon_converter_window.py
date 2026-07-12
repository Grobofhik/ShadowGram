from src.core.constants import *
from PyQt6.QtGui import QIcon
import os
import sqlite3
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QFileDialog, QProgressBar, QTextEdit, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from src import styles
from src.core.constants import CONFIG_FILE
from src.core.managers.config_manager import _read_config

class TelethonConverterThread(QThread):
    progress = pyqtSignal(int, int)
    log = pyqtSignal(str)
    finished = pyqtSignal(int, int) # success, failed

    def __init__(self, in_dir, out_dir, api_id):
        super().__init__()
        self.in_dir = Path(in_dir)
        self.out_dir = Path(out_dir)
        self.api_id = api_id

    def run(self):
        try:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            files = list(self.in_dir.glob("*.session"))
            if not files:
                self.log.emit(" В папке не найдено .session файлов.")
                self.finished.emit(0, 0)
                return

            self.log.emit(f"🔍 Найдено {len(files)} файлов. Начинаем конвертацию...")
            success = 0
            failed = 0

            for i, f in enumerate(files, 1):
                self.log.emit(f" Конвертация {f.name}...")
                try:
                    with sqlite3.connect(f) as tc:
                        t_cur = tc.cursor()
                        # Попытка найти нужную таблицу sessions
                        t_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
                        if not t_cur.fetchone():
                            self.log.emit(f"  Файл {f.name} не похож на сессию Telethon (нет таблицы sessions).")
                            failed += 1
                            continue
                        
                        # Читаем Telethon
                        t_cur.execute("SELECT dc_id, auth_key FROM sessions")
                        row = t_cur.fetchone()
                        if not row:
                            self.log.emit(f"  Файл {f.name}: пустая таблица sessions.")
                            failed += 1
                            continue
                        dc_id, auth_key = row
                    
                    # Пишем Hydrogram
                    out_file = self.out_dir / f.name
                    if out_file.exists():
                        out_file.unlink()
                        
                    with sqlite3.connect(out_file) as hc:
                        h_cur = hc.cursor()
                        h_cur.execute("CREATE TABLE sessions (dc_id INTEGER PRIMARY KEY, api_id INTEGER, test_mode INTEGER, auth_key BLOB, date INTEGER, user_id INTEGER, is_bot INTEGER)")
                        h_cur.execute("CREATE TABLE peers (id INTEGER PRIMARY KEY, access_hash INTEGER, type INTEGER, username TEXT, phone_number TEXT, last_update_on DATETIME DEFAULT CURRENT_TIMESTAMP)")
                        h_cur.execute("CREATE TABLE version (version INTEGER PRIMARY KEY)")
                        
                        h_cur.execute("INSERT INTO version VALUES (1)")
                        h_cur.execute("INSERT INTO sessions VALUES (?, ?, 0, ?, 0, 0, 0)", (dc_id, self.api_id, auth_key))
                        hc.commit()
                        
                    self.log.emit(f"  {f.name} успешно сконвертирован!")
                    success += 1
                except Exception as e:
                    self.log.emit(f"  Ошибка с {f.name}: {e}")
                    failed += 1
                
                self.progress.emit(i, len(files))

            self.log.emit(f"🎉 Конвертация завершена. Успешно: {success}, Ошибок: {failed}")
            self.finished.emit(success, failed)
        except Exception as e:
            self.log.emit(f" Критическая ошибка: {e}")
            self.finished.emit(0, 0)

class TelethonConverterWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_default_api_id()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # In Dir
        in_layout = QHBoxLayout()
        self.inp_in_dir = QLineEdit()
        self.inp_in_dir.setPlaceholderText("Путь к папке с сессиями Telethon...")
        btn_in = QPushButton("Обзор")
        btn_in.clicked.connect(self.browse_in_dir)
        in_layout.addWidget(self.inp_in_dir)
        in_layout.addWidget(btn_in)
        layout.addWidget(QLabel("Исходная папка:"))
        layout.addLayout(in_layout)

        # Out Dir
        out_layout = QHBoxLayout()
        self.inp_out_dir = QLineEdit()
        self.inp_out_dir.setPlaceholderText("Путь к новой папке (создастся если нет)...")
        btn_out = QPushButton("Обзор")
        btn_out.clicked.connect(self.browse_out_dir)
        out_layout.addWidget(self.inp_out_dir)
        out_layout.addWidget(btn_out)
        layout.addWidget(QLabel("Папка для сохранения (Hydrogram):"))
        layout.addLayout(out_layout)

        # API ID
        layout.addWidget(QLabel("API ID (для новых сессий):"))
        self.inp_api_id = QLineEdit()
        layout.addWidget(self.inp_api_id)

        # Progress
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.hide()
        layout.addWidget(self.progress)

        # Start button
        self.btn_start = QPushButton("НАЧАТЬ КОНВЕРТАЦИЮ")
        self.btn_start.setIcon(QIcon(str(ROCKET_ICON_PATH)))
        self.btn_start.setFixedHeight(45)
        self.btn_start.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY}; font-weight: bold; border-radius: 6px;")
        self.btn_start.clicked.connect(self.start_conversion)
        layout.addWidget(self.btn_start)

        # Log
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; color: #00FF00; font-family: monospace; border-radius: 6px; padding: 10px;")
        layout.addWidget(self.log_console, 1)

    def load_default_api_id(self):
        try:
            cfg = _read_config(CONFIG_FILE)
            api_id = cfg.get("settings", {}).get("api_id", "")
            if api_id:
                self.inp_api_id.setText(str(api_id))
        except:
            pass

    def browse_in_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Выберите папку с Telethon сессиями")
        if d:
            self.inp_in_dir.setText(d)

    def browse_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if d:
            self.inp_out_dir.setText(d)

    def start_conversion(self):
        in_dir = self.inp_in_dir.text().strip()
        out_dir = self.inp_out_dir.text().strip()
        api_id_str = self.inp_api_id.text().strip()

        if not in_dir or not os.path.exists(in_dir):
            QMessageBox.warning(self, "Ошибка", "Укажите правильную исходную папку.")
            return
        if not out_dir:
            QMessageBox.warning(self, "Ошибка", "Укажите папку для сохранения.")
            return
        try:
            api_id = int(api_id_str)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "API ID должен быть числом.")
            return

        self.btn_start.setEnabled(False)
        self.progress.show()
        self.progress.setValue(0)
        self.log_console.clear()

        self.thread = TelethonConverterThread(in_dir, out_dir, api_id)
        self.thread.progress.connect(self.update_progress)
        self.thread.log.connect(self.append_log)
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def update_progress(self, val, total):
        self.progress.setMaximum(total)
        self.progress.setValue(val)

    def append_log(self, text):
        self.log_console.append(text)

    def on_finished(self, success, failed):
        self.btn_start.setEnabled(True)

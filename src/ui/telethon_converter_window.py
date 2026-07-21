import os
import sqlite3
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.constants import CONFIG_FILE
from src.core.managers.config_manager import _read_config


class TelethonConverterThread(QThread):
    progress = pyqtSignal(int, int)
    log = pyqtSignal(str)
    finished = pyqtSignal(int, int)

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
                self.log.emit("В папке не найдено .session файлов.")
                self.finished.emit(0, 0)
                return

            self.log.emit(f"Найдено {len(files)} файлов. Начинаем конвертацию...")
            success = 0
            failed = 0

            for index, session_file in enumerate(files, 1):
                self.log.emit(f"Конвертация {session_file.name}...")
                try:
                    with sqlite3.connect(session_file) as telethon_conn:
                        telethon_cursor = telethon_conn.cursor()
                        telethon_cursor.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
                        )
                        if not telethon_cursor.fetchone():
                            self.log.emit(
                                f"Файл {session_file.name} не похож на Telethon-сессию: нет таблицы sessions."
                            )
                            failed += 1
                            self.progress.emit(index, len(files))
                            continue

                        telethon_cursor.execute("SELECT dc_id, auth_key FROM sessions")
                        row = telethon_cursor.fetchone()
                        if not row:
                            self.log.emit(f"Файл {session_file.name}: таблица sessions пуста.")
                            failed += 1
                            self.progress.emit(index, len(files))
                            continue

                        dc_id, auth_key = row

                    out_file = self.out_dir / session_file.name
                    if out_file.exists():
                        out_file.unlink()

                    with sqlite3.connect(out_file) as hydrogram_conn:
                        hydrogram_cursor = hydrogram_conn.cursor()
                        hydrogram_cursor.execute(
                            "CREATE TABLE sessions (dc_id INTEGER PRIMARY KEY, api_id INTEGER, test_mode INTEGER, auth_key BLOB, date INTEGER, user_id INTEGER, is_bot INTEGER)"
                        )
                        hydrogram_cursor.execute(
                            "CREATE TABLE peers (id INTEGER PRIMARY KEY, access_hash INTEGER, type INTEGER, username TEXT, phone_number TEXT, last_update_on DATETIME DEFAULT CURRENT_TIMESTAMP)"
                        )
                        hydrogram_cursor.execute(
                            "CREATE TABLE version (version INTEGER PRIMARY KEY)"
                        )
                        hydrogram_cursor.execute("INSERT INTO version VALUES (1)")
                        hydrogram_cursor.execute(
                            "INSERT INTO sessions VALUES (?, ?, 0, ?, 0, 0, 0)",
                            (dc_id, self.api_id, auth_key),
                        )
                        hydrogram_conn.commit()

                    self.log.emit(f"{session_file.name} успешно сконвертирован.")
                    success += 1
                except Exception as error:
                    self.log.emit(f"Ошибка с {session_file.name}: {error}")
                    failed += 1

                self.progress.emit(index, len(files))

            self.log.emit(f"Конвертация завершена. Успешно: {success}, Ошибок: {failed}")
            self.finished.emit(success, failed)
        except Exception as error:
            self.log.emit(f"Критическая ошибка: {error}")
            self.finished.emit(0, 0)


class TelethonConverterWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = None
        self.setObjectName("PageRoot")
        self.init_ui()
        self.load_default_api_id()
        self.update_status("Ожидание запуска.")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("PageHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(6)

        eyebrow = QLabel("SESSION REWRITE")
        eyebrow.setObjectName("PageEyebrow")
        hero_layout.addWidget(eyebrow)

        title = QLabel("Конвертер Telethon")
        title.setObjectName("PageTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            "Перепаковывает Telethon `.session` файлы в Hydrogram/Pyrogram-совместимый SQLite формат с заданным `api_id`."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(subtitle)
        layout.addWidget(hero)

        settings_card = QFrame()
        settings_card.setObjectName("PageCard")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        section_title = QLabel("Параметры конвертации")
        section_title.setObjectName("ServiceTitle")
        header_row.addWidget(section_title)

        header_row.addStretch()

        self.status_badge = QLabel("не запущено")
        self.status_badge.setObjectName("MetaBadge")
        header_row.addWidget(self.status_badge)
        settings_layout.addLayout(header_row)

        info = QLabel(
            "Укажите папку с исходными Telethon-сессиями, каталог для вывода и `api_id`, который нужно записать в новые файлы."
        )
        info.setObjectName("PageSubtitle")
        info.setWordWrap(True)
        settings_layout.addWidget(info)

        settings_layout.addWidget(self._build_path_field(
            "Исходная папка",
            "Путь к папке с Telethon `.session`...",
            self.browse_in_dir,
            "Выбрать источник",
            "inp_in_dir",
        ))

        settings_layout.addWidget(self._build_path_field(
            "Папка назначения",
            "Путь к новой папке для Hydrogram-сессий...",
            self.browse_out_dir,
            "Выбрать папку",
            "inp_out_dir",
        ))

        api_block = QFrame()
        api_block.setObjectName("ToolbarCard")
        api_layout = QVBoxLayout(api_block)
        api_layout.setContentsMargins(16, 14, 16, 14)
        api_layout.setSpacing(8)

        api_label = QLabel("API ID")
        api_label.setObjectName("StatLabel")
        api_layout.addWidget(api_label)

        self.inp_api_id = QLineEdit()
        self.inp_api_id.setPlaceholderText("Например: 2040")
        api_layout.addWidget(self.inp_api_id)
        settings_layout.addWidget(api_block)

        progress_block = QFrame()
        progress_block.setObjectName("ToolbarCard")
        progress_layout = QVBoxLayout(progress_block)
        progress_layout.setContentsMargins(16, 14, 16, 14)
        progress_layout.setSpacing(8)

        progress_label = QLabel("Прогресс")
        progress_label.setObjectName("StatLabel")
        progress_layout.addWidget(progress_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("StatHint")
        self.status_label.setWordWrap(True)
        progress_layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        progress_layout.addWidget(self.progress)
        settings_layout.addWidget(progress_block)

        action_bar = QFrame()
        action_bar.setObjectName("ToolbarCard")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(14, 12, 14, 12)
        action_layout.setSpacing(10)
        action_layout.addStretch()

        self.btn_start = QPushButton("Начать конвертацию")
        self.btn_start.setObjectName("LaunchBtn")
        self.btn_start.clicked.connect(self.start_conversion)
        action_layout.addWidget(self.btn_start)
        settings_layout.addWidget(action_bar)

        layout.addWidget(settings_card)

        log_card = QFrame()
        log_card.setObjectName("PageCard")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(20, 20, 20, 20)
        log_layout.setSpacing(12)

        log_title = QLabel("Журнал выполнения")
        log_title.setObjectName("ServiceTitle")
        log_layout.addWidget(log_title)

        self.log_console = QTextEdit()
        self.log_console.setObjectName("LogOutput")
        self.log_console.setReadOnly(True)
        log_layout.addWidget(self.log_console, 1)

        layout.addWidget(log_card, 1)

    def _build_path_field(self, title, placeholder, handler, button_text, field_name):
        block = QFrame()
        block.setObjectName("ToolbarCard")
        block_layout = QVBoxLayout(block)
        block_layout.setContentsMargins(16, 14, 16, 14)
        block_layout.setSpacing(8)

        label = QLabel(title)
        label.setObjectName("StatLabel")
        block_layout.addWidget(label)

        row = QHBoxLayout()
        row.setSpacing(10)

        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        setattr(self, field_name, field)
        row.addWidget(field, 1)

        button = QPushButton(button_text)
        button.setObjectName("GhostBtn")
        button.clicked.connect(handler)
        row.addWidget(button)

        block_layout.addLayout(row)
        return block

    def update_status(self, text, badge=None):
        self.status_label.setText(text)
        if badge is not None:
            self.status_badge.setText(badge)

    def load_default_api_id(self):
        try:
            cfg = _read_config(CONFIG_FILE)
            api_id = cfg.get("settings", {}).get("api_id", "")
            if api_id:
                self.inp_api_id.setText(str(api_id))
        except Exception:
            pass

    def browse_in_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку с Telethon сессиями")
        if directory:
            self.inp_in_dir.setText(directory)

    def browse_out_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if directory:
            self.inp_out_dir.setText(directory)

    def start_conversion(self):
        in_dir = self.inp_in_dir.text().strip()
        out_dir = self.inp_out_dir.text().strip()
        api_id_str = self.inp_api_id.text().strip()

        if not in_dir or not os.path.exists(in_dir):
            QMessageBox.warning(self, "Ошибка", "Укажите корректную исходную папку.")
            return
        if not out_dir:
            QMessageBox.warning(self, "Ошибка", "Укажите папку для сохранения.")
            return
        try:
            api_id = int(api_id_str)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "API ID должен быть числом.")
            return

        self.thread = TelethonConverterThread(in_dir, out_dir, api_id)
        self.thread.progress.connect(self.update_progress)
        self.thread.log.connect(self.append_log)
        self.thread.finished.connect(self.on_finished)

        self.btn_start.setEnabled(False)
        self.btn_start.setProperty("running", True)
        self.btn_start.style().unpolish(self.btn_start)
        self.btn_start.style().polish(self.btn_start)
        self.btn_start.setText("Конвертация...")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.log_console.clear()
        self.update_status("Подготовка к чтению файлов.", "в работе")
        self.thread.start()

    def update_progress(self, value, total):
        total = max(total, 1)
        self.progress.setMaximum(total)
        self.progress.setValue(value)
        self.update_status(f"Обработано {value} из {total} файлов.", "в работе")

    def append_log(self, text):
        self.log_console.append(text)

    def on_finished(self, success, failed):
        self.thread = None
        self.btn_start.setEnabled(True)
        self.btn_start.setProperty("running", False)
        self.btn_start.style().unpolish(self.btn_start)
        self.btn_start.style().polish(self.btn_start)
        self.btn_start.setText("Начать конвертацию")
        self.update_status(
            f"Завершено. Успешно: {success}, ошибок: {failed}.",
            "готово",
        )
        QMessageBox.information(
            self,
            "Готово",
            f"Конвертация завершена.\nУспешно: {success}\nОшибок: {failed}",
        )

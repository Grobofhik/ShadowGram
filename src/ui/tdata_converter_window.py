import shutil
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src import styles
from src.core.constants import FARMS_DIR
from src.core.managers import account_manager, farm_manager

try:
    from opentele.td import TDesktop
except ImportError:
    TDesktop = None


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


class ConverterWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(int, int)

    def __init__(self, tdata_folders, farm_path):
        super().__init__()
        self.tdata_folders = tdata_folders
        self.farm_path = Path(farm_path)

    def run(self):
        if not TDesktop:
            self.progress.emit(0, "Ошибка: библиотека opentele не установлена.")
            self.finished.emit(0, len(self.tdata_folders))
            return

        success = 0
        failed = 0
        total = len(self.tdata_folders)

        for index, folder in enumerate(self.tdata_folders):
            try:
                self.progress.emit(int(index / total * 100), f"Конвертация: {folder.name}")

                tdesk = TDesktop(str(folder))

                import sqlite3
                import time
                import uuid

                acc_id = str(uuid.uuid4())[:8]
                new_workdir = self.farm_path / "accounts" / f"converted_{acc_id}"
                new_workdir.mkdir(parents=True, exist_ok=True)

                client = tdesk.ToTelethon(
                    session=None,
                    api_id=2040,
                    api_hash="b18441a1ff607e10a989891a5462e627",
                )

                auth_key = client.session.auth_key.key
                dc_id = client.session.dc_id

                session_path = new_workdir / f"{acc_id}.session"
                with sqlite3.connect(str(session_path)) as db:
                    db.execute(
                        """CREATE TABLE sessions (
                            dc_id INTEGER PRIMARY KEY,
                            api_id INTEGER,
                            test_mode INTEGER,
                            auth_key BLOB,
                            date INTEGER,
                            user_id INTEGER,
                            is_bot INTEGER
                        )"""
                    )
                    db.execute(
                        """CREATE TABLE peers (
                            id INTEGER PRIMARY KEY,
                            access_hash INTEGER,
                            type INTEGER,
                            username TEXT,
                            phone_number TEXT,
                            last_update_on INTEGER DEFAULT (CAST(STRFTIME('%s', 'now') AS INTEGER))
                        )"""
                    )
                    db.execute(
                        """CREATE TABLE version (
                            number INTEGER PRIMARY KEY
                        )"""
                    )
                    db.execute("INSERT INTO version VALUES (3)")
                    db.execute(
                        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (dc_id, 2040, 0, auth_key, int(time.time()), 9999, 0),
                    )
                    db.commit()

                shutil.copytree(folder, new_workdir / "tdata", dirs_exist_ok=True)

                config_file = self.farm_path / "config.json"
                account_manager.add_account(
                    config_file,
                    str(new_workdir),
                    api_id="2040",
                    api_hash="b18441a1ff607e10a989891a5462e627",
                )
                success += 1
            except Exception as error:
                print(f"Converter error: {error}")
                failed += 1

        self.progress.emit(100, "Готово")
        self.finished.emit(success, failed)


class TDataConverterWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tdata_folders = []
        self.worker = None
        self.setObjectName("PageRoot")
        self.init_ui()
        self.update_summary()
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

        eyebrow = QLabel("DESKTOP IMPORT")
        eyebrow.setObjectName("PageEyebrow")
        hero_layout.addWidget(eyebrow)

        title = QLabel("Конвертер tdata")
        title.setObjectName("PageTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            "Импортирует профили Telegram Desktop, создает рабочие `.session` файлы и добавляет новые аккаунты в активную ферму."
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

        section_title = QLabel("Очередь на конвертацию")
        section_title.setObjectName("ServiceTitle")
        header_row.addWidget(section_title)

        header_row.addStretch()

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("MetaBadge")
        header_row.addWidget(self.summary_label)
        content_layout.addLayout(header_row)

        info = QLabel(
            "Добавляйте папки `tdata` по одной. Если указана родительская директория профиля, сервис сам найдет вложенную папку `tdata`."
        )
        info.setObjectName("PageSubtitle")
        info.setWordWrap(True)
        content_layout.addWidget(info)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(LIST_STYLE)
        content_layout.addWidget(self.list_widget, 1)

        toolbar = QFrame()
        toolbar.setObjectName("ToolbarCard")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 12, 14, 12)
        toolbar_layout.setSpacing(10)

        self.btn_add = QPushButton("Добавить папку")
        self.btn_add.setObjectName("GhostBtn")
        self.btn_add.clicked.connect(self.add_folders)
        toolbar_layout.addWidget(self.btn_add)

        self.btn_clear = QPushButton("Очистить список")
        self.btn_clear.setObjectName("GhostBtn")
        self.btn_clear.clicked.connect(self.clear_folders)
        toolbar_layout.addWidget(self.btn_clear)

        toolbar_layout.addStretch()

        self.btn_start = QPushButton("Начать конвертацию")
        self.btn_start.setObjectName("LaunchBtn")
        self.btn_start.clicked.connect(self.start_conversion)
        toolbar_layout.addWidget(self.btn_start)

        content_layout.addWidget(toolbar)

        progress_card = QFrame()
        progress_card.setObjectName("ToolbarCard")
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(16, 14, 16, 14)
        progress_layout.setSpacing(10)

        progress_title = QLabel("Статус")
        progress_title.setObjectName("StatLabel")
        progress_layout.addWidget(progress_title)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("StatHint")
        self.lbl_status.setWordWrap(True)
        progress_layout.addWidget(self.lbl_status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        progress_layout.addWidget(self.progress)

        content_layout.addWidget(progress_card)
        layout.addWidget(content, 1)

    def update_summary(self):
        self.summary_label.setText(f"{len(self.tdata_folders)} папок в очереди")
        has_items = bool(self.tdata_folders)
        is_running = self.worker is not None and self.worker.isRunning()
        self.btn_clear.setEnabled(has_items and not is_running)
        self.btn_start.setEnabled(has_items and not is_running)
        self.btn_add.setEnabled(not is_running)

    def update_status(self, text):
        self.lbl_status.setText(text)

    def add_folders(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку, содержащую tdata")
        if not folder:
            return

        path = Path(folder)
        target_path = None

        if path.name.lower() == "tdata":
            target_path = path
        else:
            nested_path = path / "tdata"
            if nested_path.exists():
                target_path = nested_path

        if not target_path:
            QMessageBox.warning(self, "Ошибка", "В выбранной папке не найдена папка 'tdata'.")
            return

        if target_path in self.tdata_folders:
            self.update_status(f"Папка уже добавлена: {target_path}")
            return

        self.tdata_folders.append(target_path)
        self.list_widget.addItem(str(target_path))
        self.update_status(f"Добавлена папка: {target_path.name}")
        self.update_summary()

    def clear_folders(self):
        self.tdata_folders.clear()
        self.list_widget.clear()
        self.progress.setValue(0)
        self.update_status("Список очищен.")
        self.update_summary()

    def start_conversion(self):
        if not self.tdata_folders:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы одну папку `tdata`.")
            return

        if not TDesktop:
            QMessageBox.critical(
                self,
                "Ошибка",
                "Не установлена библиотека opentele. Выполните `pip install opentele`.",
            )
            return

        farm_name = farm_manager.get_active_farm_name()
        if not farm_name:
            return

        self.worker = ConverterWorker(self.tdata_folders, FARMS_DIR / farm_name)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)

        self.btn_start.setProperty("running", True)
        self.btn_start.style().unpolish(self.btn_start)
        self.btn_start.style().polish(self.btn_start)
        self.btn_start.setText("Конвертация...")
        self.progress.setValue(0)
        self.update_status("Подготовка очереди к обработке.")
        self.update_summary()
        self.worker.start()

    def update_progress(self, value, text):
        self.progress.setValue(value)
        self.update_status(text)

    def on_finished(self, success, failed):
        self.worker = None
        self.btn_start.setProperty("running", False)
        self.btn_start.style().unpolish(self.btn_start)
        self.btn_start.style().polish(self.btn_start)
        self.btn_start.setText("Начать конвертацию")
        self.tdata_folders.clear()
        self.list_widget.clear()
        self.progress.setValue(0)
        self.update_status(f"Завершено. Успешно: {success}, ошибок: {failed}.")
        self.update_summary()
        QMessageBox.information(
            self,
            "Готово",
            f"Конвертация завершена.\nУспешно: {success}\nОшибок: {failed}",
        )

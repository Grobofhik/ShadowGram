import os
import re
import json
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSlot, QThread
from PyQt6.QtGui import QColor, QFont, QTextCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextEdit, QLineEdit, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QFrame,
    QSplitter, QCheckBox, QMessageBox, QComboBox, QGroupBox,
    QAbstractItemView
)

from src import styles
from src.core.constants import CONFIG_FILE
from src.core.managers import config_manager
from src.core.managers.mass_sender_engine import MassSenderWorker

class MassSenderPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker_thread = None
        self.accounts_data = []
        self.init_ui()
        self.load_accounts()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {styles.COLOR_ACCENT_BG}; border-radius: 12px; padding: 15px;")
        header_layout = QHBoxLayout(header_frame)
        
        header_title = QLabel("📢 Модуль Гибкой Рассылки (Mass Sender)")
        header_title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {styles.COLOR_TEXT_MAIN};")
        header_layout.addWidget(header_title)
        header_layout.addStretch()

        # Stat badges
        self.lbl_sent = QLabel("Успешно: 0")
        self.lbl_sent.setStyleSheet(f"color: {styles.COLOR_SUCCESS}; font-weight: bold; font-size: 14px; margin-right: 15px;")
        self.lbl_failed = QLabel("Ошибок: 0")
        self.lbl_failed.setStyleSheet(f"color: {styles.COLOR_DANGER}; font-weight: bold; font-size: 14px; margin-right: 15px;")
        self.lbl_flood = QLabel("FloodWait: 0")
        self.lbl_flood.setStyleSheet(f"color: {styles.COLOR_WARNING}; font-weight: bold; font-size: 14px;")

        header_layout.addWidget(self.lbl_sent)
        header_layout.addWidget(self.lbl_failed)
        header_layout.addWidget(self.lbl_flood)

        main_layout.addWidget(header_frame)

        # Splitter (Left: Settings & Message Editor, Right: Receivers & Logs)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ==========================================
        # LEFT PANEL: EDITOR & FORMATTING TOOLS
        # ==========================================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(12)

        # Formatting Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet(f"background-color: {styles.COLOR_ACCENT_BG}; border-radius: 8px; padding: 5px;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setSpacing(5)
        tb_layout.setContentsMargins(5, 5, 5, 5)

        btn_bold = QPushButton("B")
        btn_bold.setToolTip("Жирный (**текст**)")
        btn_bold.setFixedWidth(32)
        btn_bold.setStyleSheet("font-weight: bold;")
        btn_bold.clicked.connect(lambda: self.insert_formatting("**", "**"))

        btn_italic = QPushButton("I")
        btn_italic.setToolTip("Курсив (__текст__)")
        btn_italic.setFixedWidth(32)
        btn_italic.setStyleSheet("font-style: italic;")
        btn_italic.clicked.connect(lambda: self.insert_formatting("__", "__"))

        btn_strike = QPushButton("S")
        btn_strike.setToolTip("Зачеркнутый (~~текст~~)")
        btn_strike.setFixedWidth(32)
        btn_strike.clicked.connect(lambda: self.insert_formatting("~~", "~~"))

        btn_code = QPushButton("Code")
        btn_code.setToolTip("Моноширинный (`текст`)")
        btn_code.clicked.connect(lambda: self.insert_formatting("`", "`"))

        btn_quote = QPushButton("💬 Цитата")
        btn_quote.setToolTip("Блок цитирования (> текст)")
        btn_quote.clicked.connect(lambda: self.insert_formatting("> ", ""))

        btn_link = QPushButton("🔗 Ссылка")
        btn_link.setToolTip("Вставить ссылку [Текст](URL)")
        btn_link.clicked.connect(self.insert_link)

        btn_spoiler = QPushButton("👁️ Спойлер")
        btn_spoiler.setToolTip("Спойлер (||текст||)")
        btn_spoiler.clicked.connect(lambda: self.insert_formatting("||", "||"))

        btn_emoji = QPushButton("⭐ Премиум-Эмодзи")
        btn_emoji.setToolTip("Вставить Telegram Custom Emoji по ID (:emoji_id:)")
        btn_emoji.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: white;")
        btn_emoji.clicked.connect(self.insert_premium_emoji)

        tb_layout.addWidget(btn_bold)
        tb_layout.addWidget(btn_italic)
        tb_layout.addWidget(btn_strike)
        tb_layout.addWidget(btn_code)
        tb_layout.addWidget(btn_quote)
        tb_layout.addWidget(btn_link)
        tb_layout.addWidget(btn_spoiler)
        tb_layout.addWidget(btn_emoji)
        tb_layout.addStretch()

        left_layout.addWidget(toolbar)

        # Editor & Preview Splitter
        editor_splitter = QSplitter(Qt.Orientation.Vertical)

        # Text Editor
        self.txt_message = QTextEdit()
        self.txt_message.setPlaceholderText("Введите текст сообщения...\n\nПоддерживается Markdown и Премиум-эмодзи синтаксис :custom_emoji_id:\nПример: Привет! :5386348405021235123: Подписывайся на наш канал!")
        self.txt_message.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 8px; padding: 10px; font-size: 14px;")
        self.txt_message.textChanged.connect(self.update_preview)
        editor_splitter.addWidget(self.txt_message)

        # Live Telegram Preview Box
        preview_box = QGroupBox("📱 Предпросмотр (Telegram Style)")
        preview_box.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-weight: bold;")
        preview_layout = QVBoxLayout(preview_box)
        
        self.lbl_preview = QLabel()
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setTextFormat(Qt.TextFormat.MarkdownText)
        self.lbl_preview.setStyleSheet(f"""
            background-color: #182533; 
            color: #FFFFFF; 
            border-radius: 12px; 
            padding: 12px; 
            font-size: 14px;
            font-family: 'Segoe UI', sans-serif;
        """)
        preview_layout.addWidget(self.lbl_preview)
        editor_splitter.addWidget(preview_box)

        left_layout.addWidget(editor_splitter)

        # Sending Controls Box
        controls_box = QGroupBox("⚙️ Настройки параметров рассылки")
        controls_box.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-weight: bold;")
        ctrl_layout = QHBoxLayout(controls_box)

        ctrl_layout.addWidget(QLabel("Задержка (сек):"))
        self.spin_delay_min = QSpinBox()
        self.spin_delay_min.setRange(1, 300)
        self.spin_delay_min.setValue(5)
        ctrl_layout.addWidget(self.spin_delay_min)

        ctrl_layout.addWidget(QLabel("—"))
        self.spin_delay_max = QSpinBox()
        self.spin_delay_max.setRange(1, 300)
        self.spin_delay_max.setValue(15)
        ctrl_layout.addWidget(self.spin_delay_max)

        ctrl_layout.addWidget(QLabel("Лимит на аккаунт:"))
        self.spin_limit_acc = QSpinBox()
        self.spin_limit_acc.setRange(1, 1000)
        self.spin_limit_acc.setValue(20)
        ctrl_layout.addWidget(self.spin_limit_acc)

        left_layout.addWidget(controls_box)

        splitter.addWidget(left_widget)

        # ==========================================
        # RIGHT PANEL: TARGET LIST & ACCOUNTS TABLE & LOGS
        # ==========================================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(12)

        # Target Receivers Text Area
        recv_box = QGroupBox("🎯 Список получателей (По одному юзернейму/ID на строку)")
        recv_box.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-weight: bold;")
        recv_layout = QVBoxLayout(recv_box)

        self.txt_targets = QTextEdit()
        self.txt_targets.setPlaceholderText("@durov\n@telegram\n123456789")
        self.txt_targets.setMaximumHeight(150)
        self.txt_targets.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 8px; padding: 8px;")
        recv_layout.addWidget(self.txt_targets)

        btn_load_txt = QPushButton("📁 Загрузить из .txt файла")
        btn_load_txt.clicked.connect(self.load_targets_from_file)
        recv_layout.addWidget(btn_load_txt)

        right_layout.addWidget(recv_box)

        # Accounts Selection Table
        acc_box = QGroupBox("👥 Выбор аккаунтов для рассылки")
        acc_box.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-weight: bold;")
        acc_layout = QVBoxLayout(acc_box)

        self.table_accs = QTableWidget()
        self.table_accs.setColumnCount(3)
        self.table_accs.setHorizontalHeaderLabels(["Выбор", "Имя аккаунта", "Прокси"])
        self.table_accs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_accs.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_accs.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER};")
        acc_layout.addWidget(self.table_accs)

        right_layout.addWidget(acc_box)

        # Execution Logs Box
        log_box = QGroupBox("📜 Лог выполнения")
        log_box.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-weight: bold;")
        log_layout = QVBoxLayout(log_box)

        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet(f"background-color: #0d1117; color: #c9d1d9; border-radius: 8px; font-family: monospace; font-size: 12px;")
        log_layout.addWidget(self.txt_logs)

        right_layout.addWidget(log_box)

        # Control Action Buttons
        btn_action_layout = QHBoxLayout()
        self.btn_start = QPushButton("🚀 Запустить рассылку")
        self.btn_start.setStyleSheet(f"background-color: {styles.COLOR_SUCCESS}; color: white; font-weight: bold; font-size: 15px; padding: 12px; border-radius: 8px;")
        self.btn_start.clicked.connect(self.start_sending)

        self.btn_stop = QPushButton("🛑 Остановить")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(f"background-color: {styles.COLOR_DANGER}; color: white; font-weight: bold; font-size: 15px; padding: 12px; border-radius: 8px;")
        self.btn_stop.clicked.connect(self.stop_sending)

        btn_action_layout.addWidget(self.btn_start)
        btn_action_layout.addWidget(self.btn_stop)

        right_layout.addLayout(btn_action_layout)

        splitter.addWidget(right_widget)
        main_layout.addWidget(splitter)

    def load_accounts(self):
        """Загрузка имеющихся аккаунтов из config.json"""
        try:
            cfg = config_manager._read_config(Path(CONFIG_FILE))
            self.accounts_data = cfg.get("accounts", [])
            self.table_accs.setRowCount(len(self.accounts_data))

            for idx, acc in enumerate(self.accounts_data):
                chk = QCheckBox()
                is_valid = acc.get("is_valid", True)
                invalid_reason = acc.get("invalid_reason", "")
                
                chk.setChecked(is_valid)
                self.table_accs.setCellWidget(idx, 0, chk)
                
                name_text = acc.get("name", "Unknown")
                if not is_valid:
                    name_text += " (НЕВАЛИДЕН)"

                name_item = QTableWidgetItem(name_text)
                proxy_item = QTableWidgetItem(acc.get("proxy_url") or "Без прокси")
                
                if not is_valid:
                    from PyQt6.QtGui import QColor
                    name_item.setBackground(QColor(239, 68, 68, 45))
                    proxy_item.setBackground(QColor(239, 68, 68, 45))
                    name_item.setToolTip(f"⚠️ Невалидный аккаунт: {invalid_reason}")
                    proxy_item.setToolTip(f"⚠️ Невалидный аккаунт: {invalid_reason}")
                
                self.table_accs.setItem(idx, 1, name_item)
                self.table_accs.setItem(idx, 2, proxy_item)

        except Exception as e:
            self.log(f"Ошибка загрузки аккаунтов: {e}", "error")

    def insert_formatting(self, prefix: str, suffix: str):
        cursor = self.txt_message.textCursor()
        selected = cursor.selectedText()
        cursor.insertText(f"{prefix}{selected if selected else 'текст'}{suffix}")

    def insert_link(self):
        from PyQt6.QtWidgets import QInputDialog
        url, ok = QInputDialog.getText(self, "Вставить гиперссылку", "Введите URL ссылки:")
        if ok and url:
            cursor = self.txt_message.textCursor()
            selected = cursor.selectedText()
            text = selected if selected else "текст ссылки"
            cursor.insertText(f"[{text}]({url})")

    def insert_premium_emoji(self):
        from PyQt6.QtWidgets import QInputDialog
        emoji_id, ok = QInputDialog.getText(self, "Премиум Эмодзи", "Введите Custom Emoji ID (число 18-20 знаков):")
        if ok and emoji_id and emoji_id.isdigit():
            cursor = self.txt_message.textCursor()
            cursor.insertText(f":{emoji_id}:")

    def update_preview(self):
        text = self.txt_message.toPlainText()
        # Заменяем в предпросмотре :emoji_id: на иконку звезд
        preview_text = re.sub(r":\d+:", "⭐", text)
        self.lbl_preview.setText(preview_text if preview_text else "Предпросмотр сообщения появится здесь...")

    def load_targets_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл с получателями", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.txt_targets.setText(content)
                self.log(f"Загружено получателей из {os.path.basename(file_path)}", "info")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось прочитать файл: {e}")

    def start_sending(self):
        msg_text = self.txt_message.toPlainText().strip()
        if not msg_text:
            QMessageBox.warning(self, "Внимание", "Введите текст сообщения!")
            return

        targets_raw = self.txt_targets.toPlainText().strip().split("\n")
        targets = [t.strip() for t in targets_raw if t.strip()]
        if not targets:
            QMessageBox.warning(self, "Внимание", "Укажите список получателей!")
            return

        selected_accs = []
        for idx in range(self.table_accs.rowCount()):
            chk = self.table_accs.cellWidget(idx, 0)
            if chk and chk.isChecked():
                selected_accs.append(self.accounts_data[idx])

        if not selected_accs:
            QMessageBox.warning(self, "Внимание", "Отметьте хотя бы один аккаунт для рассылки!")
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self.worker_thread = MassSenderWorker(
            accounts=selected_accs,
            target_usernames=targets,
            message_text=msg_text,
            delay_min=self.spin_delay_min.value(),
            delay_max=self.spin_delay_max.value(),
            limit_per_acc=self.spin_limit_acc.value()
        )
        self.worker_thread.progress_signal.connect(self.log_progress)
        self.worker_thread.stat_signal.connect(self.update_stats)
        self.worker_thread.finished_signal.connect(self.on_worker_finished)
        self.worker_thread.start()

    def stop_sending(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.log("Отправка запроса на остановку...", "warning")

    def on_worker_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    @pyqtSlot(str, str, str)
    def log_progress(self, status, acc_name, message):
        color = "#c9d1d9"
        if status == "success": color = "#3fb950"
        elif status == "error": color = "#f85149"
        elif status == "warning": color = "#d29922"
        elif status == "info": color = "#58a6ff"

        log_entry = f"<span style='color: {color};'>[{acc_name}] {message}</span>"
        self.txt_logs.append(log_entry)

    @pyqtSlot(int, int, int)
    def update_stats(self, sent, failed, flood):
        self.lbl_sent.setText(f"Успешно: {sent}")
        self.lbl_failed.setText(f"Ошибок: {failed}")
        self.lbl_flood.setText(f"FloodWait: {flood}")

    def log(self, text, level="info"):
        self.log_progress(level, "Система", text)

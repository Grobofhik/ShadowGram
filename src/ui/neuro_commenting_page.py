from src.core.constants import *
from PyQt6.QtGui import QIcon
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QTextEdit, QLineEdit, QComboBox, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QScrollArea, QSpinBox, QCheckBox, QDialog, QDialogButtonBox,
    QAbstractItemView, QListWidget, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QFont

from src import styles
from src.core.constants import CONFIG_FILE
from src.core.managers.neuro_engine import NeuroEngineThread

class PromptDialog(QDialog):
    def __init__(self, account_name, current_prompts: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Пулл промптов для {account_name}")
        self.resize(600, 500)
        self.setStyleSheet(f"background-color: {styles.COLOR_BG}; color: {styles.COLOR_TEXT_MAIN};")
        
        layout = QVBoxLayout(self)
        
        label = QLabel("Пулл промптов. Для каждого коммента будет выбираться случайный:")
        label.setWordWrap(True)
        label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(label)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"background: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px;")
        for p in current_prompts:
            self.list_widget.addItem(p)
        layout.addWidget(self.list_widget)
        
        # Кнопки управления пулом
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Добавить")
        btn_add.setIcon(QIcon(str(START_ICON_PATH)))
        btn_edit = QPushButton("Изменить")
        btn_edit.setIcon(QIcon(str(NOTE_ICON_PATH)))
        btn_del = QPushButton("Удалить")
        btn_del.setIcon(QIcon(str(CANCEL_ICON_PATH)))
        
        for b in [btn_add, btn_edit, btn_del]:
            b.setStyleSheet(f"QPushButton {{ background-color: {styles.COLOR_ACCENT_BG}; border: 1px solid {styles.COLOR_BORDER}; padding: 5px; border-radius: 4px; color: {styles.COLOR_TEXT_MAIN}; }} QPushButton:hover {{ background-color: {styles.COLOR_HOVER_BG}; }}")
            btn_layout.addWidget(b)
            
        btn_add.clicked.connect(self.add_prompt)
        btn_edit.clicked.connect(self.edit_prompt)
        btn_del.clicked.connect(self.del_prompt)
        
        layout.addLayout(btn_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        
        for btn in btn_box.buttons():
            btn.setStyleSheet(f"QPushButton {{ background-color: {styles.COLOR_PRIMARY}; color: white; border: none; border-radius: 4px; padding: 6px 12px; }} QPushButton:hover {{ background-color: {styles.COLOR_PRIMARY_DARK}; }}")
        
        layout.addWidget(btn_box)
        
    def add_prompt(self):
        text, ok = QInputDialog.getMultiLineText(self, "Новый промпт", "Введите текст промпта:")
        if ok and text.strip():
            self.list_widget.addItem(text.strip())
            
    def edit_prompt(self):
        curr = self.list_widget.currentItem()
        if curr:
            text, ok = QInputDialog.getMultiLineText(self, "Изменить промпт", "Введите текст промпта:", curr.text())
            if ok and text.strip():
                curr.setText(text.strip())
                
    def del_prompt(self):
        curr = self.list_widget.currentItem()
        if curr:
            self.list_widget.takeItem(self.list_widget.row(curr))
            
    def get_prompts(self):
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]


class NeuroCommentingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.is_running = False
        
        # Храним промпты в памяти: { account_name: prompt_text }
        self.account_prompts = {}
        self.selected_accounts_cache = []
        
        self.setup_ui()
        self.load_settings()
        self.refresh_accounts()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # --- Шапка ---
        header_layout = QHBoxLayout()
        title = QLabel("Нейрокомментинг")
        title.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {styles.COLOR_TEXT_MAIN};")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.btn_save = QPushButton("Сохранить настройки")
        self.btn_save.setFixedWidth(200)
        self.btn_save.setStyleSheet(self._btn_style())
        self.btn_save.clicked.connect(self.save_settings)
        header_layout.addWidget(self.btn_save)
        main_layout.addLayout(header_layout)
        
        # --- Верхняя секция: Каналы и общие настройки ---
        top_layout = QHBoxLayout()
        
        # Левая часть - Каналы
        channels_frame = QFrame()
        channels_frame.setStyleSheet(self._frame_style())
        channels_layout = QVBoxLayout(channels_frame)
        
        lbl_chan = QLabel("Целевые Каналы")
        lbl_chan.setStyleSheet(self._subtitle_style())
        channels_layout.addWidget(lbl_chan)
        
        self.channels_text = QTextEdit()
        self.channels_text.setPlaceholderText("https://t.me/durov\n@telegram")
        self.channels_text.setStyleSheet(f"background: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; color: {styles.COLOR_TEXT_MAIN}; border-radius: 6px; padding: 8px;")
        channels_layout.addWidget(self.channels_text)
        top_layout.addWidget(channels_frame, 1) # proportion 1
        
        # Правая часть - Тайминги и глобальные настройки
        settings_frame = QFrame()
        settings_frame.setStyleSheet(self._frame_style())
        settings_layout = QVBoxLayout(settings_frame)
        
        lbl_set = QLabel("Глобальные настройки")
        lbl_set.setStyleSheet(self._subtitle_style())
        settings_layout.addWidget(lbl_set)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Режим: Делить каналы поровну", "Режим: Каждый работает по всем"])
        self.mode_combo.setStyleSheet(f"background: {styles.COLOR_CONSOLE_BG}; color: {styles.COLOR_TEXT_MAIN}; padding: 5px; border-radius: 4px; border: 1px solid {styles.COLOR_BORDER};")
        settings_layout.addWidget(self.mode_combo)
        
        # Паузы
        t_layout = QHBoxLayout()
        t1 = QVBoxLayout()
        t1.addWidget(QLabel("Пауза перед подпиской (сек):"))
        self.spin_sub = QSpinBox()
        self.spin_sub.setRange(5, 300)
        self.spin_sub.setValue(30)
        self.spin_sub.setStyleSheet(f"background: {styles.COLOR_CONSOLE_BG}; color: {styles.COLOR_TEXT_MAIN};")
        t1.addWidget(self.spin_sub)
        t_layout.addLayout(t1)
        
        t2 = QVBoxLayout()
        t2.addWidget(QLabel("Пауза перед комментом (сек):"))
        self.spin_com = QSpinBox()
        self.spin_com.setRange(10, 600)
        self.spin_com.setValue(60)
        self.spin_com.setStyleSheet(f"background: {styles.COLOR_CONSOLE_BG}; color: {styles.COLOR_TEXT_MAIN};")
        t2.addWidget(self.spin_com)
        t_layout.addLayout(t2)
        
        t3 = QVBoxLayout()
        t3.addWidget(QLabel("Задержка между каналами (сек):"))
        range_layout = QHBoxLayout()
        self.spin_chan_min = QSpinBox()
        self.spin_chan_min.setRange(10, 3600)
        self.spin_chan_min.setValue(60)
        self.spin_chan_min.setStyleSheet(f"background: {styles.COLOR_CONSOLE_BG}; color: {styles.COLOR_TEXT_MAIN};")
        self.spin_chan_max = QSpinBox()
        self.spin_chan_max.setRange(10, 3600)
        self.spin_chan_max.setValue(120)
        self.spin_chan_max.setStyleSheet(f"background: {styles.COLOR_CONSOLE_BG}; color: {styles.COLOR_TEXT_MAIN};")
        range_layout.addWidget(self.spin_chan_min)
        lbl_dash = QLabel("-")
        lbl_dash.setStyleSheet(f"color: {styles.COLOR_TEXT_MAIN};")
        range_layout.addWidget(lbl_dash)
        range_layout.addWidget(self.spin_chan_max)
        t3.addLayout(range_layout)
        t_layout.addLayout(t3)
        
        settings_layout.addLayout(t_layout)
        
        self.check_read_history = QCheckBox("Анализировать последние комментарии перед ответом")
        self.check_read_history.setChecked(True)
        settings_layout.addWidget(self.check_read_history)
        
        settings_layout.addStretch()
        top_layout.addWidget(settings_frame, 1) # proportion 1
        
        main_layout.addLayout(top_layout)
        
        # --- Нижняя секция: Аккаунты и Мониторинг ---
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet(self._frame_style())
        bottom_layout = QVBoxLayout(bottom_frame)
        
        lbl_acc = QLabel("Управление аккаунтами и Live-Лог (Матрица)")
        lbl_acc.setStyleSheet(self._subtitle_style())
        bottom_layout.addWidget(lbl_acc)
        
        split_layout = QHBoxLayout()
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Участвует", "Аккаунт", "Промпт (Личность)", "Статус / Мониторинг", "Настройка"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(f"background: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; color: {styles.COLOR_TEXT_MAIN};")
        split_layout.addWidget(self.table, 6)
        
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet(f"background: #050505; color: #00FF41; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; border: 1px solid {styles.COLOR_BORDER}; border-radius: 4px; padding: 5px;")
        self.terminal.setPlaceholderText("SYSTEM_STANDBY...\nAWAITING_INITIALIZATION...")
        split_layout.addWidget(self.terminal, 4)
        
        bottom_layout.addLayout(split_layout)
        
        # Кнопки управления
        control_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Обновить список")
        self.btn_refresh.setStyleSheet(self._btn_style())
        self.btn_refresh.clicked.connect(self.refresh_accounts)
        control_layout.addWidget(self.btn_refresh)
        
        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_all.setStyleSheet(self._btn_style())
        self.btn_select_all.clicked.connect(self.select_all_accounts)
        control_layout.addWidget(self.btn_select_all)
        
        self.btn_deselect_all = QPushButton("Снять выбор")
        self.btn_deselect_all.setStyleSheet(self._btn_style())
        self.btn_deselect_all.clicked.connect(self.deselect_all_accounts)
        control_layout.addWidget(self.btn_deselect_all)
        
        control_layout.addStretch()
        
        self.btn_run = QPushButton("ЗАПУСТИТЬ")
        self.btn_run.setFixedSize(200, 45)
        self.btn_run.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_PRIMARY};
                color: white; font-weight: bold; font-size: 16px; border-radius: 8px;
            }}
            QPushButton:hover {{ background-color: {styles.COLOR_PRIMARY_DARK}; }}
        """)
        self.btn_run.clicked.connect(self.toggle_running)
        control_layout.addWidget(self.btn_run)
        
        bottom_layout.addLayout(control_layout)
        main_layout.addWidget(bottom_frame, 1)

    def _frame_style(self):
        return f"QFrame {{ background-color: {styles.COLOR_ACCENT_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 8px; }}"

    def _subtitle_style(self):
        return f"font-size: 18px; font-weight: bold; color: {styles.COLOR_TEXT_MAIN}; margin-bottom: 10px;"
        
    def _btn_style(self):
        return f"""
            QPushButton {{ background-color: transparent; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 8px 16px; color: {styles.COLOR_TEXT_MAIN}; }}
            QPushButton:hover {{ background-color: {styles.COLOR_HOVER_BG}; }}
        """

    def load_settings(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            neuro = data.get("settings", {}).get("neuro_v2", {})
            self.channels_text.setText(neuro.get("channels", ""))
            self.spin_sub.setValue(neuro.get("sub_delay", 30))
            self.spin_com.setValue(neuro.get("com_delay", 60))
            self.spin_chan_min.setValue(neuro.get("chan_delay_min", 60))
            self.spin_chan_max.setValue(neuro.get("chan_delay_max", 120))
            self.mode_combo.setCurrentIndex(neuro.get("mode", 0))
            self.check_read_history.setChecked(neuro.get("read_history", True))
            
            # Конвертируем старые строковые промпты в пулл (список)
            loaded_prompts = neuro.get("account_prompts", {})
            for k, v in loaded_prompts.items():
                if isinstance(v, str):
                    self.account_prompts[k] = [v] if v.strip() else []
                else:
                    self.account_prompts[k] = v
                    
            self.selected_accounts_cache = neuro.get("selected_accounts", [])
        except Exception as e:
            print(f"Failed to load neuro settings: {e}")

    def save_settings(self, show_msg=True):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
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
                "selected_accounts": self.get_selected_accounts()
            }
            
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            if show_msg:
                QMessageBox.information(self, "Успех", "Настройки сохранены!")
        except Exception as e:
            if show_msg:
                QMessageBox.critical(self, "Ошибка", str(e))

    def refresh_accounts(self):
        if self.is_running:
            return
            
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            accounts = data.get("accounts", [])
        except:
            accounts = []
            
        self.table.setRowCount(0)
        for i, acc in enumerate(accounts):
            acc_name = acc.get("name", f"Acc {i}")
            self.table.insertRow(i)
            
            # Checkbox
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            if acc_name in self.selected_accounts_cache:
                chk.setCheckState(Qt.CheckState.Checked)
            else:
                chk.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(i, 0, chk)
            
            # Name
            self.table.setItem(i, 1, QTableWidgetItem(acc_name))
            
            # Prompt preview
            prompt_list = self.account_prompts.get(acc_name, [])
            if not prompt_list:
                preview = "Нет промптов (стандарт)"
            else:
                first_p = prompt_list[0]
                preview = f"[{len(prompt_list)}шт] " + ((first_p[:30] + '...') if len(first_p) > 30 else first_p)
            
            item_preview = QTableWidgetItem(preview)
            item_preview.setForeground(QColor(styles.COLOR_TEXT_MUTED))
            self.table.setItem(i, 2, item_preview)
            
            # Status
            self.table.setItem(i, 3, QTableWidgetItem("Готов"))
            
            # Edit Button
            btn_edit = QPushButton("Настроить")
            btn_edit.setStyleSheet(self._btn_style())
            # Сохраняем имя аккаунта в lambda
            btn_edit.clicked.connect(lambda checked, name=acc_name, row=i: self.edit_prompt(name, row))
            self.table.setCellWidget(i, 4, btn_edit)

    def edit_prompt(self, account_name, row):
        current_prompts = self.account_prompts.get(account_name, [])
        dialog = PromptDialog(account_name, current_prompts, self)
        if dialog.exec():
            new_prompts = dialog.get_prompts()
            self.account_prompts[account_name] = new_prompts
            
            if not new_prompts:
                preview = "Нет промптов (стандарт)"
            else:
                first_p = new_prompts[0]
                preview = f"[{len(new_prompts)}шт] " + ((first_p[:30] + '...') if len(first_p) > 30 else first_p)
                
            self.table.item(row, 2).setText(preview)
            
            # Auto-save changes
            self.save_settings()

    def get_selected_accounts(self):
        selected = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked:
                acc_name = self.table.item(row, 1).text()
                selected.append(acc_name)
        return selected

    def select_all_accounts(self):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).flags() & Qt.ItemFlag.ItemIsEnabled:
                self.table.item(row, 0).setCheckState(Qt.CheckState.Checked)

    def deselect_all_accounts(self):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).flags() & Qt.ItemFlag.ItemIsEnabled:
                self.table.item(row, 0).setCheckState(Qt.CheckState.Unchecked)

    def toggle_running(self):
        if not self.is_running:
            self.start_neuro()
        else:
            self.stop_neuro()
            
    def start_neuro(self):
        self.save_settings(show_msg=False)  # Save selected accounts
        selected = self.get_selected_accounts()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Отметьте галочкой хотя бы один аккаунт в таблице!")
            return
            
        self.is_running = True
        self.btn_run.setText("ОСТАНОВИТЬ")
        self.btn_run.setStyleSheet(f"QPushButton {{ background-color: #E74C3C; color: white; font-weight: bold; font-size: 16px; border-radius: 8px; }}")
        
        # Делаем чекбоксы неактивными
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            
            # Ставим статус "Ожидание" выбранным
            if item.checkState() == Qt.CheckState.Checked:
                self.table.item(row, 3).setText("Запуск ядра...")
                
        # Создаем и запускаем движок
        self.engine_thread = NeuroEngineThread(selected, parent=self)
        self.engine_thread.status_updated.connect(self.on_engine_status_updated)
        self.engine_thread.stopped.connect(self.on_engine_stopped)
        self.engine_thread.start()

    def on_engine_status_updated(self, account_name, message):
        import datetime
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        log_line = f"[{time_str}] [Acc: {account_name}] {message}"
        self.terminal.append(log_line)
        
        # Scroll to bottom
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        if account_name == "ALL":
            for row in range(self.table.rowCount()):
                if self.table.item(row, 0).checkState() == Qt.CheckState.Checked:
                    self.table.item(row, 3).setText(message)
            return
            
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).text() == account_name:
                self.table.item(row, 3).setText(message)
                break

    def on_engine_stopped(self):
        self.is_running = False
        self.btn_run.setText("ЗАПУСТИТЬ")
        self.btn_run.setStyleSheet(f"QPushButton {{ background-color: {styles.COLOR_PRIMARY}; color: white; font-weight: bold; font-size: 16px; border-radius: 8px; }}")
        
        # Возвращаем чекбоксы
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
            if item.checkState() == Qt.CheckState.Checked:
                self.table.item(row, 3).setText("Остановлен")

    def stop_neuro(self):
        self.is_running = False
        self.btn_run.setText("ОСТАНАВЛИВАЕТСЯ...")
        self.btn_run.setStyleSheet(f"QPushButton {{ background-color: #95A5A6; color: white; font-weight: bold; font-size: 16px; border-radius: 8px; }}")
        
        if hasattr(self, "engine_thread") and self.engine_thread.isRunning():
            self.engine_thread.stop()

    # Убрана заглушка simulate_dashboard_update, так как теперь есть реальный NeuroEngine

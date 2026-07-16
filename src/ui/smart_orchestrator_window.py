from src.core.constants import *
from PyQt6.QtGui import QIcon
import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, 
                             QMessageBox, QSpinBox, QTextEdit, QGridLayout,
                             QLineEdit, QCheckBox, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, pyqtSlot
from PyQt6.QtGui import QColor, QCursor

from src import styles

from src.core.managers.smart_orchestrator import SmartOrchestratorThread

class ModuleCard(QFrame):
    clicked = pyqtSignal(bool)
    
    def __init__(self, display_name, parent=None):
        super().__init__(parent)
        self.display_name = display_name
        self.is_selected = False
        
        self.setObjectName("ModuleCard")
        self.setStyleSheet("""
            QFrame#ModuleCard {
                background-color: #1e293b;
                border: 2px solid #334155;
                border-radius: 10px;
            }
            QFrame#ModuleCard:hover {
                border: 2px solid #6366f1;
                background-color: #2e3b52;
            }
        """)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.lbl = QLabel(display_name)
        self.lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #e2e8f0;")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setWordWrap(True)
        layout.addWidget(self.lbl)
        
    def mousePressEvent(self, event):
        self.is_selected = not self.is_selected
        if self.is_selected:
            self.setStyleSheet("""
                QFrame#ModuleCard {
                    background-color: #4f46e5;
                    border: 2px solid #818cf8;
                    border-radius: 10px;
                }
            """)
            self.lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff;")
        else:
            self.setStyleSheet("""
                QFrame#ModuleCard {
                    background-color: #1e293b;
                    border: 2px solid #334155;
                    border-radius: 10px;
                }
                QFrame#ModuleCard:hover {
                    border: 2px solid #6366f1;
                    background-color: #2e3b52;
                }
            """)
            self.lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #e2e8f0;")
        self.clicked.emit(self.is_selected)

class SmartOrchestratorWindow(QWidget):
    def __init__(self, get_accounts_callback, manager):
        super().__init__()
        self.get_accounts_callback = get_accounts_callback
        self.manager = manager
        
        all_plugins = self.manager.discover_modules()
        self.available_plugins = {k: v for k, v in all_plugins.items() if not getattr(v, "SINGLE_ACCOUNT", False)}
        
        self.setStyleSheet(styles.STYLESHEET)
        self.orchestrator_thread = None
        self.module_cards = []
        self.module_params_data = {}
        self.active_param_widgets = {}
        
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # --- LEFT PANEL (Settings) ---
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("1. Выберите модули (нажмите на карточку):", objectName="SectionTitle"))
        
        # Scroll area for module grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout(scroll_content)
        grid_layout.setSpacing(10)
        
        col = 0
        row = 0
        for p_name in self.available_plugins.keys():
            card = ModuleCard(p_name)
            card.clicked.connect(self.update_params_panel)
            self.module_cards.append(card)
            grid_layout.addWidget(card, row, col)
            col += 1
            if col > 1: # 2 columns
                col = 0
                row += 1
                
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll, 1)
        
        # --- NEW SECTION: Parameters of selected modules ---
        self.params_title_lbl = QLabel("2. Настройки выбранных модулей:", objectName="SectionTitle")
        left_layout.addWidget(self.params_title_lbl)
        
        self.params_scroll = QScrollArea()
        self.params_scroll.setWidgetResizable(True)
        self.params_scroll.setStyleSheet("QScrollArea { border: 1px solid #334155; border-radius: 8px; background-color: #0f172a; }")
        self.params_scroll.setMinimumHeight(150)
        self.params_scroll.setMaximumHeight(300)
        
        self.params_container = QWidget()
        self.params_container.setStyleSheet("background-color: transparent;")
        self.params_layout = QVBoxLayout(self.params_container)
        self.params_layout.setContentsMargins(10, 10, 10, 10)
        self.params_layout.setSpacing(15)
        
        self.params_scroll.setWidget(self.params_container)
        left_layout.addWidget(self.params_scroll)
        self.params_scroll.setVisible(False)
        self.params_title_lbl.setVisible(False)
        
        left_layout.addWidget(QLabel("3. Задержка между действиями (сек):", objectName="SectionTitle"))
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("От:"))
        self.spin_min = QSpinBox()
        self.spin_min.setRange(0, 3600)
        self.spin_min.setValue(10)
        delay_layout.addWidget(self.spin_min)
        
        delay_layout.addWidget(QLabel("До:"))
        self.spin_max = QSpinBox()
        self.spin_max.setRange(0, 3600)
        self.spin_max.setValue(30)
        delay_layout.addWidget(self.spin_max)
        left_layout.addLayout(delay_layout)
        
        self.btn_run = QPushButton("ЗАПУСТИТЬ ОРКЕСТРАТОР")
        self.btn_run.setIcon(QIcon(str(ROCKET_ICON_PATH)))
        self.btn_run.setFixedHeight(50)
        self.btn_run.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY}; font-weight: bold; font-size: 14px; border-radius: 8px;")
        self.btn_run.clicked.connect(self.run_orchestrator)
        left_layout.addWidget(self.btn_run)
        
        self.btn_stop = QPushButton("🛑 ОСТАНОВИТЬ")
        self.btn_stop.setFixedHeight(40)
        self.btn_stop.setStyleSheet("background-color: #d32f2f; font-weight: bold; border-radius: 8px;")
        self.btn_stop.clicked.connect(self.stop_orchestrator)
        self.btn_stop.setEnabled(False)
        left_layout.addWidget(self.btn_stop)
        
        layout.addWidget(left_frame, 1)
        
        # --- RIGHT PANEL (Logs) ---
        right_frame = QFrame()
        right_frame.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 8px;")
        right_layout = QVBoxLayout(right_frame)
        
        terminal_header = QHBoxLayout()
        terminal_title = QLabel("ORCHESTRATOR TERMINAL")
        terminal_title.setStyleSheet("color: #475569; font-weight: bold; letter-spacing: 1px; font-size: 11px;")
        terminal_header.addWidget(terminal_title)
        terminal_header.addStretch()
        right_layout.addLayout(terminal_header)
        
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet("border: none; background: transparent; color: #00FF00; font-family: monospace; font-size: 12px;")
        right_layout.addWidget(self.log_console, 1)
        
        layout.addWidget(right_frame, 1)

    def log_message(self, workdir, msg):
        t = datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"[{t}] <b>[{workdir}]</b> {msg}")
        scrollbar = self.log_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_params_panel(self):
        # 1. Save current active widget values into self.module_params_data
        for plugin_class_name, widgets in self.active_param_widgets.items():
            if plugin_class_name not in self.module_params_data:
                self.module_params_data[plugin_class_name] = {}
            for param_name, widget in widgets.items():
                if isinstance(widget, QLineEdit):
                    self.module_params_data[plugin_class_name][param_name] = widget.text()
                elif isinstance(widget, QTextEdit):
                    self.module_params_data[plugin_class_name][param_name] = widget.toPlainText()
                elif isinstance(widget, QCheckBox):
                    self.module_params_data[plugin_class_name][param_name] = widget.isChecked()

        # 2. Clear current parameter layout
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # 3. Build parameter forms for selected modules
        self.active_param_widgets = {}
        has_params = False

        for card in self.module_cards:
            if card.is_selected:
                p_class = self.available_plugins.get(card.display_name)
                if not p_class:
                    continue
                plugin_class_name = p_class.__name__
                params = getattr(p_class, "PARAMS", [])
                if not params:
                    continue

                has_params = True
                
                group_frame = QFrame()
                group_frame.setStyleSheet("""
                    QFrame {
                        background-color: #1e293b;
                        border: 1px solid #334155;
                        border-radius: 8px;
                    }
                """)
                group_layout = QVBoxLayout(group_frame)
                group_layout.setContentsMargins(10, 10, 10, 10)
                group_layout.setSpacing(8)

                title_lbl = QLabel(f"⚙️ {card.display_name}")
                title_lbl.setStyleSheet("font-weight: bold; color: #818cf8; font-size: 12px; border: none; background: transparent;")
                group_layout.addWidget(title_lbl)

                self.active_param_widgets[plugin_class_name] = {}

                for param in params:
                    p_name = param.get("name")
                    p_type = param.get("type", "text")
                    p_label = param.get("label", p_name)

                    saved_val = self.module_params_data.get(plugin_class_name, {}).get(p_name, None)

                    field_layout = QVBoxLayout()
                    field_layout.setSpacing(4)

                    if p_type == "checkbox":
                        cb = QCheckBox(p_label)
                        cb.setStyleSheet("QCheckBox { color: #e2e8f0; border: none; background: transparent; }")
                        if saved_val is not None:
                            cb.setChecked(bool(saved_val))
                        else:
                            cb.setChecked(False)
                        group_layout.addWidget(cb)
                        self.active_param_widgets[plugin_class_name][p_name] = cb
                    else:
                        lbl = QLabel(p_label)
                        lbl.setStyleSheet("color: #94a3b8; font-size: 11px; border: none; background: transparent;")
                        field_layout.addWidget(lbl)

                        if p_type == "textarea":
                            te = QTextEdit()
                            te.setStyleSheet("""
                                QTextEdit {
                                    background-color: #0f172a;
                                    border: 1px solid #475569;
                                    border-radius: 4px;
                                    color: #e2e8f0;
                                    font-size: 12px;
                                }
                            """)
                            te.setFixedHeight(60)
                            if saved_val is not None:
                                te.setPlainText(str(saved_val))
                            field_layout.addWidget(te)
                            self.active_param_widgets[plugin_class_name][p_name] = te
                        elif p_type in ["text", "folder"]:
                            le = QLineEdit()
                            le.setStyleSheet("""
                                QLineEdit {
                                    background-color: #0f172a;
                                    border: 1px solid #475569;
                                    border-radius: 4px;
                                    color: #e2e8f0;
                                    font-size: 12px;
                                    height: 24px;
                                    padding-left: 5px;
                                }
                            """)
                            if saved_val is not None:
                                le.setText(str(saved_val))

                            if p_type == "folder":
                                row_layout = QHBoxLayout()
                                row_layout.setContentsMargins(0, 0, 0, 0)
                                row_layout.setSpacing(5)
                                row_layout.addWidget(le, 1)

                                browse_btn = QPushButton("📁")
                                browse_btn.setStyleSheet("""
                                    QPushButton {
                                        background-color: #334155;
                                        border: none;
                                        border-radius: 4px;
                                        color: #e2e8f0;
                                        width: 30px;
                                        height: 24px;
                                    }
                                    QPushButton:hover {
                                        background-color: #475569;
                                    }
                                """)
                                def make_browse_handler(line_edit=le):
                                    def handle():
                                        path = QFileDialog.getExistingDirectory(self, "Выберите папку", line_edit.text() or os.getcwd())
                                        if path:
                                            line_edit.setText(path)
                                    return handle
                                browse_btn.clicked.connect(make_browse_handler(le))
                                row_layout.addWidget(browse_btn)
                                field_layout.addLayout(row_layout)
                            else:
                                field_layout.addWidget(le)

                            self.active_param_widgets[plugin_class_name][p_name] = le

                        group_layout.addLayout(field_layout)

                self.params_layout.addWidget(group_frame)

        self.params_scroll.setVisible(has_params)
        self.params_title_lbl.setVisible(has_params)

    def run_orchestrator(self):
        if callable(self.get_accounts_callback):
            selected_accounts = self.get_accounts_callback()
        else:
            selected_accounts = self.get_accounts_callback

        if not selected_accounts:
            QMessageBox.warning(self, "Внимание", "Сначала выберите аккаунты в списке слева!")
            return

        # Save values from current active widgets into self.module_params_data
        for plugin_class_name, widgets in self.active_param_widgets.items():
            if plugin_class_name not in self.module_params_data:
                self.module_params_data[plugin_class_name] = {}
            for param_name, widget in widgets.items():
                if isinstance(widget, QLineEdit):
                    self.module_params_data[plugin_class_name][param_name] = widget.text()
                elif isinstance(widget, QTextEdit):
                    self.module_params_data[plugin_class_name][param_name] = widget.toPlainText()
                elif isinstance(widget, QCheckBox):
                    self.module_params_data[plugin_class_name][param_name] = widget.isChecked()

        selected_modules = []
        for card in self.module_cards:
            if card.is_selected:
                p_class = self.available_plugins.get(card.display_name)
                selected_modules.append(p_class.__name__)
                
        if not selected_modules:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один модуль для запуска!")
            return
            
        min_delay = self.spin_min.value()
        max_delay = self.spin_max.value()
        if min_delay > max_delay:
            QMessageBox.warning(self, "Ошибка", "Минимальная задержка не может быть больше максимальной!")
            return
            
        workdirs = [acc.get("workdir") for acc in selected_accounts]
        
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log_console.clear()
        self.log_message("SYSTEM", f"Запуск на {len(workdirs)} аккаунтах. Выбрано модулей: {len(selected_modules)}")
        
        self.orchestrator_thread = SmartOrchestratorThread(workdirs, selected_modules, min_delay, max_delay, user_params=self.module_params_data)
        self.orchestrator_thread.signals.log_msg.connect(self.log_message)
        self.orchestrator_thread.signals.finished.connect(self.on_orchestrator_finished)
        self.orchestrator_thread.start()
        
    def stop_orchestrator(self):
        if self.orchestrator_thread and self.orchestrator_thread.isRunning():
            self.orchestrator_thread.stop()
            self.log_message("SYSTEM", "🛑 Получена команда остановки. Ждем завершения текущих шагов...")
            self.btn_stop.setEnabled(False)

    def on_orchestrator_finished(self):
        self.log_message("SYSTEM", "Все задачи завершены.")
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)

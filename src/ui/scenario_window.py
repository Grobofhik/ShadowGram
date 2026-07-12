from src.core.constants import *
from src.ui.icon_cache import get_icon
import json
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QTextEdit, QFrame, 
                             QMessageBox, QFileDialog, QLineEdit, QListWidget, 
                             QListWidgetItem, QAbstractItemView, QCheckBox)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from datetime import datetime

from src.core.constants import CONFIG_FILE, FOLDER_ICON_PATH

from src import styles

class ScenarioWindow(QWidget):
    def __init__(self, parent_window, manager, selected_accounts):
        super().__init__()
        self.parent_window = parent_window
        self.manager = manager
        self.selected_accounts = selected_accounts
        
        all_plugins = self.manager.discover_modules()
        if len(self.selected_accounts) > 1:
            self.available_plugins = {k: v for k, v in all_plugins.items() if not getattr(v, "SINGLE_ACCOUNT", False)}
        else:
            self.available_plugins = all_plugins
            
        self.scenario_steps = []
        self.param_widgets = {}
        
        self.setWindowTitle(f"Конструктор сценариев ({len(selected_accounts)} акк.)")
        self.resize(800, 600)
        self.setStyleSheet(styles.STYLESHEET)
        
        self.init_ui()
        self.update_params_panel()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Left Panel - Scenario Steps
        left_frame = QFrame()
        left_frame.setObjectName("SectionFrame")
        left_layout = QVBoxLayout(left_frame)
        left_layout.addWidget(QLabel("Шаги сценария", objectName="SectionTitle"))
        
        self.steps_list = QListWidget()
        self.steps_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.steps_list.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 8px; padding: 5px;")
        self.steps_list.model().rowsMoved.connect(self.on_rows_moved)
        left_layout.addWidget(self.steps_list, 1)
        
        btn_clear = QPushButton("Очистить сценарий")
        btn_clear.clicked.connect(self.clear_scenario)
        left_layout.addWidget(btn_clear)
        
        self.btn_run = QPushButton("ЗАПУСТИТЬ СЦЕНАРИЙ")
        self.btn_run.setIcon(QIcon(str(ROCKET_ICON_PATH)))
        self.btn_run.setFixedHeight(45)
        self.btn_run.clicked.connect(self.run_scenario)
        left_layout.addWidget(self.btn_run)
        
        layout.addWidget(left_frame, 1)
        
        # Right Panel - Add Step
        right_frame = QFrame()
        right_frame.setObjectName("SectionFrame")
        right_layout = QVBoxLayout(right_frame)
        right_layout.addWidget(QLabel("Добавить шаг", objectName="SectionTitle"))
        
        type_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItem("Пауза")
        self.type_combo.addItems(list(self.available_plugins.keys()))
        self.type_combo.currentTextChanged.connect(self.update_params_panel)
        type_layout.addWidget(self.type_combo, 1)
        right_layout.addLayout(type_layout)
        
        self.params_container = QFrame()
        self.params_layout = QVBoxLayout(self.params_container)
        self.params_layout.setContentsMargins(0, 10, 0, 10)
        right_layout.addWidget(self.params_container)
        
        btn_add = QPushButton("+ ДОБАВИТЬ В СЦЕНАРИЙ")
        btn_add.clicked.connect(self.add_step)
        right_layout.addWidget(btn_add)
        
        right_layout.addStretch()
        
        layout.addWidget(right_frame, 1)

    def on_rows_moved(self, parent, start, end, destination, row):
        new_steps = []
        for i in range(self.steps_list.count()):
            item = self.steps_list.item(i)
            new_steps.append(item.data(Qt.ItemDataRole.UserRole))
        self.scenario_steps = new_steps

    def update_params_panel(self):
        self._clear_layout(self.params_layout)
        self.param_widgets = {}
        
        sel_text = self.type_combo.currentText()
        if sel_text == "Пауза":
            l1 = QHBoxLayout()
            l1.addWidget(QLabel("От (секунд):"))
            min_input = QLineEdit("60")
            l1.addWidget(min_input)
            self.param_widgets["min_pause"] = min_input
            
            l2 = QHBoxLayout()
            l2.addWidget(QLabel("До (секунд):"))
            max_input = QLineEdit("120")
            l2.addWidget(max_input)
            self.param_widgets["max_pause"] = max_input
            
            self.params_layout.addLayout(l1)
            self.params_layout.addLayout(l2)
            return

        p_class = self.available_plugins.get(sel_text)
        if not p_class or not hasattr(p_class, 'PARAMS'): return

        settings = {}
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f).get("settings", {})
        except Exception:
            pass

        for param in p_class.PARAMS:
            param_layout = QHBoxLayout()
            param_layout.addWidget(QLabel(f"{param['label']}:"))
            
            p_type = param.get('type', 'text')
            p_name = param.get('name')

            if p_type == 'file':
                le = QLineEdit(); btn = QPushButton(); btn.setIcon(get_icon(FOLDER_ICON_PATH)); btn.setIconSize(QSize(20, 20)); btn.setFixedWidth(40)
                btn.clicked.connect(lambda ch, l=le: self.browse_file(l))
                param_layout.addWidget(le); param_layout.addWidget(btn); self.param_widgets[p_name] = le
            elif p_type in ['text', 'number']:
                le = QLineEdit()
                if p_type == 'number': le.setPlaceholderText("0")
                if p_name == 'api_key': le.setText(settings.get('default_ai_api_key', ''))
                elif p_name == 'api_base_url': le.setText(settings.get('default_ai_base_url', 'https://api.groq.com/openai/v1'))
                elif p_name == 'model_name': le.setText(settings.get('default_ai_model_name', 'llama-3.1-8b-instant'))
                param_layout.addWidget(le); self.param_widgets[p_name] = le
            elif p_type == 'textarea':
                te = QTextEdit(); te.setFixedHeight(80); param_layout.addWidget(te); self.param_widgets[p_name] = te
            elif p_type == 'number':
                le = QLineEdit(); le.setPlaceholderText("0"); param_layout.addWidget(le); self.param_widgets[p_name] = le
            elif p_type == 'checkbox':
                cb = QCheckBox(); param_layout.addWidget(cb); self.param_widgets[p_name] = cb
            self.params_layout.addLayout(param_layout)

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
                elif item.layout(): self._clear_layout(item.layout())

    def browse_file(self, le):
        fp, _ = QFileDialog.getOpenFileName(self, "Выбрать файл", "", "All Files (*)")
        if fp: le.setText(fp)

    def add_step(self):
        sel_text = self.type_combo.currentText()
        step_data = {"name": sel_text, "params": {}}
        
        if sel_text == "Пауза":
            try:
                min_p = int(self.param_widgets["min_pause"].text())
                max_p = int(self.param_widgets["max_pause"].text())
                if min_p > max_p: min_p, max_p = max_p, min_p
                step_data["type"] = "pause"
                step_data["params"] = {"min": min_p, "max": max_p}
                display_text = f"Пауза ({min_p} - {max_p} сек.)"
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Укажите корректные числа для паузы.")
                return
        else:
            step_data["type"] = "plugin"
            for n, w in self.param_widgets.items():
                if isinstance(w, QLineEdit): step_data["params"][n] = w.text()
                elif isinstance(w, QTextEdit): step_data["params"][n] = w.toPlainText()
                elif isinstance(w, QCheckBox): step_data["params"][n] = w.isChecked()
            display_text = f"🧩 Плагин: {sel_text}"

        self.scenario_steps.append(step_data)
        
        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, step_data)
        self.steps_list.addItem(item)

    def clear_scenario(self):
        self.steps_list.clear()
        self.scenario_steps.clear()

    def run_scenario(self):
        if not self.scenario_steps:
            QMessageBox.warning(self, "Ошибка", "Сценарий пуст!")
            return
        
        task_id = f"SCENARIO_{datetime.now().strftime('%H%M%S')}"
        if hasattr(self.parent_window, "start_scenario_execution"):
            self.parent_window.start_scenario_execution(self.selected_accounts, self.scenario_steps, task_id)
            self.close()
        else:
            QMessageBox.critical(self, "Ошибка", "Не найден обработчик сценариев в главном окне.")
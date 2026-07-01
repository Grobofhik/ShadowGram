from src.ui.icon_cache import get_icon
import json
import threading
import asyncio
import os
import random
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QCheckBox, QComboBox, 
                             QTextEdit, QFrame, QMessageBox, QFileDialog, QLineEdit, QTabWidget)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from datetime import datetime

"""
Обновленное окно управления модулями ShadowGram.
Поддерживает циклическую работу (ротации) и детальное логирование времени ожидания.
Функции:

- format_time: перевод секунд в формат "X ч. Y мин."
- run_plugins_batch: бесконечный цикл выполнения для параллельных задач
- start_scenario_execution: запуск составного сценария из конструктора
"""

from src.core.managers import proxy_manager, farm_manager, config_manager, hw_manager, process_manager, account_manager
from src.core.logger import logger
from src.core.constants import CONFIG_FILE, START_ICON_PATH, RELOAD_ICON_PATH, FOLDER_ICON_PATH
from src.core.module_manager import ModuleManager
from src.modules_styles import MODULES_STYLESHEET
from src.ui.active_tasks_window import ActiveTasksWindow
from src.ui.smart_orchestrator_window import SmartOrchestratorWindow
from src import styles

class ModulesPage(QWidget):
    log_signal = pyqtSignal(str)
    task_log_signal = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setStyleSheet(MODULES_STYLESHEET)
        
        self.manager = ModuleManager()
        self.available_plugins = self.manager.discover_modules()
        self.param_widgets = {}
        
        self.active_tasks_win = ActiveTasksWindow()
        self.active_tasks_win.stop_requested.connect(self.stop_running_task)
        
        self.running_tasks = {} # { task_id: (asyncio_task, loop) }
        self.local_tasks = {} # { task_id: { loop, tasks, instances } }
        self.scenario_win = None
        
        self.init_ui()
        self.log_signal.connect(self.append_log)
        self.task_log_signal.connect(self.active_tasks_win.append_log)
        self.update_params_panel()
        self.print_welcome_banner()

    def print_welcome_banner(self):
        banner = f"""
<span style='color: {styles.COLOR_PRIMARY}; font-family: monospace; white-space: pre;'>
  ██████  ██   ██  █████  ██████   ██████  ██     ██  ██████  ██████   █████  ███    ███ 
 ██       ██   ██ ██   ██ ██   ██ ██    ██ ██     ██ ██       ██   ██ ██   ██ ████  ████ 
  █████   ███████ ███████ ██   ██ ██    ██ ██  █  ██ ██   ███ ██████  ███████ ██ ████ ██ 
      ██  ██   ██ ██   ██ ██   ██ ██    ██ ██ ███ ██ ██    ██ ██   ██ ██   ██ ██  ██  ██ 
  ██████  ██   ██ ██   ██ ██████   ██████   ███ ███   ██████  ██   ██ ██   ██ ██      ██ 
</span>
<span style='color: {styles.COLOR_PRIMARY};'> --------------------------------------------------------------------------------------- </span>
<span style='color: #888;'> [ Платформа автоматизации ShadowGram v1.2 ] </span>
<span style='color: #888;'> [ Система готова к работе. Выберите плагин и аккаунты. ] </span>
        """
        self.log_output.append(banner)

    def format_time(self, seconds):
        """Превращает секунды в красивую строку"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        res = []
        if h > 0: res.append(f"{h} ч.")
        if m > 0: res.append(f"{m} мин.")
        if s > 0 and h == 0: res.append(f"{s} сек.")
        return " ".join(res) if res else "0 сек."

    def stop_running_task(self, task_id):
        if task_id in self.running_tasks:
            task, loop = self.running_tasks[task_id]
            self.task_log_signal.emit(task_id, "<b style='color: #ff5252;'>Запрос на остановку...</b>")
            loop.call_soon_threadsafe(task.cancel)


    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # ЛЕВАЯ ПАНЕЛЬ: АККАУНТЫ
        left_frame = QFrame()
        left_frame.setObjectName("SectionFrame")
        left_frame.setFixedWidth(320)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        acc_title = QLabel("Аккаунты", objectName="SectionTitle")
        header_layout.addWidget(acc_title)
        header_layout.addStretch()
        
        self.btn_active_tasks = QPushButton("АКТИВНЫЕ ЗАДАЧИ")
        self.btn_active_tasks.setStyleSheet("background-color: #6366f1; border: 1px solid #4f46e5; border-bottom: 3px solid #4338ca; font-size: 10px; border-radius: 6px; padding: 6px 12px;")
        self.btn_active_tasks.clicked.connect(self.active_tasks_win.show)
        header_layout.addWidget(self.btn_active_tasks)
        left_layout.addLayout(header_layout)
        
        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск аккаунта...")
        self.search_input.textChanged.connect(self.filter_accounts)
        left_layout.addWidget(self.search_input)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setSpacing(6)
        self.checkboxes = []
        self.load_accounts()
        self.scroll.setWidget(self.scroll_content)
        left_layout.addWidget(self.scroll)
        
        btn_all = QPushButton("ВЫБРАТЬ ВСЕ")
        btn_all.setObjectName("ExplorerBtn") # Использовать стиль акцентной кнопки
        btn_all.clicked.connect(self.toggle_all)
        left_layout.addWidget(btn_all)
        
        main_layout.addWidget(left_frame, 1)

        # ПРАВАЯ ПАНЕЛЬ: НАСТРОЙКИ
        # ПРАВАЯ ПАНЕЛЬ: НАСТРОЙКИ
        self.right_tabs = QTabWidget()
        self.right_tabs.setObjectName("SectionFrame")
        self.right_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #1e293b; border-radius: 8px; background-color: #0f172a; } 
            QTabBar::tab { background: #1e293b; color: #94a3b8; padding: 10px 20px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px; } 
            QTabBar::tab:selected { background: #0f172a; color: #6366f1; font-weight: bold; border: 1px solid #1e293b; border-bottom-color: #0f172a; }
        """)
        
        tab_single = QWidget()
        right_layout = QVBoxLayout(tab_single)
        right_layout.setSpacing(16)
        
        plugin_header = QHBoxLayout()
        plugin_header.addWidget(QLabel("Модуль", objectName="SectionTitle"))
        
        self.module_combo = QComboBox()
        self.module_combo.addItems(list(self.available_plugins.keys()))
        self.module_combo.currentTextChanged.connect(self.update_params_panel)
        plugin_header.addWidget(self.module_combo, 1)
        
        btn_refresh_plugins = QPushButton()
        btn_refresh_plugins.setIcon(get_icon(RELOAD_ICON_PATH))
        btn_refresh_plugins.setIconSize(QSize(16, 16))
        btn_refresh_plugins.setFixedWidth(40)
        btn_refresh_plugins.clicked.connect(self.refresh_plugins_list)
        plugin_header.addWidget(btn_refresh_plugins)
        
        right_layout.addLayout(plugin_header)
        
        # Контейнер параметров
        self.params_container = QFrame()
        self.params_container.setStyleSheet(f"QFrame {{ background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 8px; padding: 10px; }}")
        self.params_layout = QVBoxLayout(self.params_container)
        self.params_layout.setContentsMargins(10, 10, 10, 10)
        self.params_layout.setSpacing(12)
        right_layout.addWidget(self.params_container)
        
        # Кнопки управления
        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(12)
        
        self.btn_run = QPushButton(" ЗАПУСК")
        self.btn_run.setIcon(get_icon(START_ICON_PATH))
        self.btn_run.setIconSize(QSize(20, 20))
        self.btn_run.setObjectName("RunModuleBtn")
        self.btn_run.clicked.connect(self.start_module_execution)
        btns_layout.addWidget(self.btn_run, 2)
        
        # btn_scenario was removed
        self.btn_monitor = QPushButton("МОНИТОРИНГ")
        self.btn_monitor.setStyleSheet(f"background-color: {styles.COLOR_ACCENT_BG}; border: 1px solid {styles.COLOR_BORDER}; border-bottom: 3px solid {styles.COLOR_BORDER_DARK}; font-weight: bold; padding: 16px; border-radius: 10px;")
        self.btn_monitor.clicked.connect(self.open_monitor_config)
        btns_layout.addWidget(self.btn_monitor, 1)
        
        right_layout.addLayout(btns_layout)
        
        terminal_header = QHBoxLayout()
        terminal_title = QLabel("TERMINAL OUTPUT")
        terminal_title.setStyleSheet("color: #475569; font-weight: bold; letter-spacing: 1px; font-size: 11px;")
        terminal_header.addWidget(terminal_title)
        terminal_header.addStretch()
        # Имитация кнопок macOS
        mac_btns = QLabel("🔴 🟡 🟢")
        mac_btns.setStyleSheet("font-size: 10px; color: #334155;")
        terminal_header.addWidget(mac_btns)
        
        right_layout.addLayout(terminal_header)
        
        self.log_output = QTextEdit()
        self.log_output.setObjectName("LogOutput")
        self.log_output.setReadOnly(True)
        right_layout.addWidget(self.log_output, 1)
        
        self.right_tabs.addTab(tab_single, "Одиночный запуск")
        
        # Добавляем Оркестратор как вторую вкладку
        self.orchestrator_widget = SmartOrchestratorWindow(
            get_accounts_callback=lambda: [c.property("acc_data") for c in self.checkboxes if c.isChecked()],
            manager=self.manager
        )
        self.right_tabs.addTab(self.orchestrator_widget, "🎭 Умный Оркестратор")
        
        main_layout.addWidget(self.right_tabs, 2)

    def filter_accounts(self, text):
        for cb in self.checkboxes:
            card = cb.property("card_widget")
            if text.lower() in cb.text().lower():
                card.show()
            else:
                card.hide()

    def load_accounts(self):
        self._clear_layout(self.scroll_layout)
        self.checkboxes.clear()
        
        accounts = config_manager.load_config(CONFIG_FILE)
        if not accounts:
            no_acc = QLabel("Нет аккаунтов. Добавьте их в левом меню.")
            no_acc.setStyleSheet("color: #94a3b8; font-style: italic;")
            self.scroll_layout.addWidget(no_acc)
            return
            
        for acc in accounts:
            card = QFrame()
            card.setObjectName("SectionFrame")
            card.setStyleSheet("QFrame { background-color: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 2px; } QFrame:hover { background-color: rgba(255, 255, 255, 0.07); border: 1px solid #6366f1; }")
            
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(8, 8, 8, 8)
            card_layout.setSpacing(10)
            
            avatar = QLabel("👤")
            avatar.setStyleSheet("font-size: 16px; background: transparent; border: none;")
            card_layout.addWidget(avatar)
            
            cb = QCheckBox(f"{acc['name']}")
            cb.setStyleSheet("QCheckBox { background: transparent; border: none; font-weight: 500; font-size: 13px; } QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; }")
            cb.setProperty("acc_data", acc)
            cb.stateChanged.connect(lambda st, c=cb: self.on_account_toggled(st, c))
            
            card_layout.addWidget(cb, 1)
            
            # Сохраняем карточку в cb, чтобы filter_accounts мог скрыть всю карточку
            cb.setProperty("card_widget", card)
            
            self.scroll_layout.addWidget(card)
            self.checkboxes.append(cb)


    def open_monitor_config(self):
        # Быстрый переход к плагину Мониторинга
        index = self.module_combo.findText("👁️ Мониторинг канала (24/7)")
        if index >= 0:
            self.module_combo.setCurrentIndex(index)
            QMessageBox.information(self, "Мониторинг 24/7", "Включен режим мониторинга канала!\n\nНастройте параметры модуля ниже, отметьте нужные аккаунты слева и нажмите 'ЗАПУСТИТЬ ПЛАГИН'.\nАккаунты будут работать в фоновом режиме.")
        else:
            QMessageBox.warning(self, "Ошибка", "Модуль '👁️ Мониторинг канала (24/7)' не найден в системе.")

    def open_scenario_builder(self):
        selected_accounts = [c.property("acc_data") for c in self.checkboxes if c.isChecked()]
        if not selected_accounts:
            QMessageBox.warning(self, "Внимание", "Сначала выберите аккаунты для сценария!")
            return
            
        self.scenario_win = SmartOrchestratorWindow(selected_accounts, self.manager)
        self.scenario_win.show()

    def start_scenario_execution(self, accounts, steps, task_id):
        self.active_tasks_win.add_task_tab(task_id, f"Сценарий ({len(accounts)} акк.)")
        self.active_tasks_win.show()
        
        threading.Thread(target=self.run_scenario_batch, args=(accounts, steps, task_id), daemon=True).start()

    def run_scenario_batch(self, accounts, steps, task_id):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.local_tasks[task_id] = { "loop": loop, "tasks": [], "instances": [] }
        try:
            with open(CONFIG_FILE, "r") as f: cfg = json.load(f)
            max_concurrent = cfg.get("settings", {}).get("max_concurrent_tasks", 10)
            
            async def run_all():
                tasks = []
                concurrency_limit = asyncio.Semaphore(max_concurrent)
                
                for i, a in enumerate(accounts):
                    def log_f(msg, acc_name=a['name'], tid=task_id):
                        self.log_signal.emit(msg)
                        self.task_log_signal.emit(tid, msg)
                        
                    async def wrapped_run(acc_data, _log_f):
                        try:
                            async with concurrency_limit:
                                aid = acc_data.get("api_id", 0)
                                ah = acc_data.get("api_hash", "")
                                runner = ScenarioRunner(acc_data, aid, ah, _log_f)
                                delay = random.randint(1, 15)
                                _log_f(f"Запуск сценария через {self.format_time(delay)}", "warning")
                                await asyncio.sleep(delay)
                            
                                # Execute steps sequentially for this account
                                for step_idx, step in enumerate(steps):
                                    async with concurrency_limit:
                                        if step["type"] == "pause":
                                            pause_sec = random.randint(step["params"]["min"], step["params"]["max"])
                                            _log_f(f"[{step_idx+1}/{len(steps)}] ⏳ Пауза на {self.format_time(pause_sec)}...", "info")
                                            await asyncio.sleep(pause_sec)
                                            _log_f(f"[{step_idx+1}/{len(steps)}] ⏳ Пауза завершена.", "success")
                                        elif step["type"] == "plugin":
                                            p_name = step["name"]
                                            p_params = step["params"]
                                            p_class = self.manager.get_module_class(p_name)
                                        
                                            if not p_class:
                                                _log_f(f"[{step_idx+1}/{len(steps)}] ❌ Ошибка: плагин {p_name} не найден!", "error")
                                                continue
                                            
                                            _log_f(f"[{step_idx+1}/{len(steps)}] 🚀 Запуск: {p_name}...", "info")
                                            instance = p_class(acc_data, aid, ah, _log_f)
                                            self.local_tasks[task_id]["instances"].append(instance)
                                        
                                            try:
                                                if await instance.init_client():
                                                    await instance.run(**p_params)
                                            except Exception as e:
                                                _log_f(f"[{step_idx+1}/{len(steps)}] ❌ Ошибка плагина: {e}", "error")
                                            finally:
                                                await instance.cleanup()
                                            
                                _log_f("✅ Сценарий полностью выполнен!", "success")
                                            
                        except asyncio.CancelledError:
                            _log_f("❌ Сценарий отменен пользователем.", "error")
                            raise
                        except Exception as e:
                            _log_f(f"Критическая ошибка сценария: {e}", "error")

                    task_obj = loop.create_task(wrapped_run(a, log_f))
                    self.local_tasks[task_id]["tasks"].append(task_obj)
                    tasks.append(task_obj)
                
                await asyncio.gather(*tasks)

            main_task = loop.create_task(run_all())
            self.running_tasks[task_id] = (main_task, loop)
            loop.run_until_complete(main_task)
            self.task_log_signal.emit(task_id, f"<b style='color: {styles.COLOR_PRIMARY};'>Сессия сценариев завершена.</b>")
        except asyncio.CancelledError:
            self.task_log_signal.emit(task_id, "<b style='color: #ff5252;'>Все процессы в этой вкладке остановлены.</b>")
        finally:
            if task_id in self.running_tasks: del self.running_tasks[task_id]
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending: task.cancel()
                if pending: loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.run_until_complete(loop.shutdown_default_executor())
            except Exception as e:
                logger.error(f"Ошибка при закрытии цикла сценариев: {e}")
            finally:
                loop.close()
                asyncio.set_event_loop(None)

    def refresh_plugins_list(self):
        self.available_plugins = self.manager.discover_modules()
        self.module_combo.clear()
        self.module_combo.addItems(list(self.available_plugins.keys()))
        self.append_log("Список плагинов обновлен.")

    def update_params_panel(self):
        self._clear_layout(self.params_layout)
        self.param_widgets = {}
        plugin_name = self.module_combo.currentText()
        p_class = self.available_plugins.get(plugin_name)
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
                le = QLineEdit()
                btn = QPushButton()
                btn.setIcon(get_icon(FOLDER_ICON_PATH))
                btn.setIconSize(QSize(20, 20))
                btn.setFixedWidth(40)
                btn.clicked.connect(lambda ch, l=le: self.browse_file(l))
                param_layout.addWidget(le); param_layout.addWidget(btn); self.param_widgets[p_name] = le
            elif p_type in ['text', 'number']:
                le = QLineEdit()
                if p_type == 'number': le.setPlaceholderText("0")
                # Автозаполнение известных полей из настроек
                if p_name == 'api_key': le.setText(settings.get('default_ai_api_key', ''))
                elif p_name == 'api_base_url': le.setText(settings.get('default_ai_base_url', 'https://api.groq.com/openai/v1'))
                elif p_name == 'model_name': le.setText(settings.get('default_ai_model_name', 'llama-3.1-8b-instant'))
                param_layout.addWidget(le); self.param_widgets[p_name] = le
            elif p_type == 'textarea':
                te = QTextEdit(); te.setFixedHeight(80); param_layout.addWidget(te); self.param_widgets[p_name] = te
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

    def load_accounts(self):
        self._clear_layout(self.scroll_layout)
        self.checkboxes.clear()
        for acc in config_manager.load_config(CONFIG_FILE):
            cb = QCheckBox(f"{acc['name']}")
            cb.setProperty("acc_data", acc)
            cb.stateChanged.connect(lambda st, c=cb: self.on_account_toggled(st, c))
            self.scroll_layout.addWidget(cb); self.checkboxes.append(cb)

    def on_account_toggled(self, state, cb):
        if state == Qt.CheckState.Checked.value:
            p_class = self.available_plugins.get(self.module_combo.currentText())
            if p_class and getattr(p_class, "SINGLE_ACCOUNT", False):
                for other in self.checkboxes:
                    if other != cb and other.isChecked():
                        other.blockSignals(True); other.setChecked(False); other.blockSignals(False)

    def toggle_all(self):
        p_class = self.available_plugins.get(self.module_combo.currentText())
        if p_class and getattr(p_class, "SINGLE_ACCOUNT", False):
            QMessageBox.information(self, "Внимание", "Только один аккаунт разрешен!")
            return
        st = not all(c.isChecked() for c in self.checkboxes)
        for c in self.checkboxes: c.setChecked(st)

    def append_log(self, text):
        self.log_output.append(f"<span style='color: #888;'>[sys]:</span> {text}")
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def get_params_values(self):
        res = {}
        for n, w in self.param_widgets.items():
            if isinstance(w, QLineEdit): res[n] = w.text()
            elif isinstance(w, QTextEdit): res[n] = w.toPlainText()
            elif isinstance(w, QCheckBox): res[n] = w.isChecked()
        return res

    def start_module_execution(self):
        selected_accounts = [c.property("acc_data") for c in self.checkboxes if c.isChecked()]
        if not selected_accounts: return
        p_name = self.module_combo.currentText()
        p_class = self.manager.get_module_class(p_name)
        params = self.get_params_values()
        self.btn_run.setEnabled(False)
        QTimer.singleShot(2000, lambda: self.btn_run.setEnabled(True))
        
        task_id = f"{p_name}_{datetime.now().strftime('%H%M%S')}"
        
        self.active_tasks_win.add_task_tab(task_id, f"{p_name} ({len(selected_accounts)})")
        self.active_tasks_win.show()
        
        threading.Thread(target=self.run_plugins_batch, args=(selected_accounts, p_class, params, task_id), daemon=True).start()

    def run_plugins_batch(self, accounts, plugin_class, params, task_id):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.local_tasks[task_id] = { "loop": loop, "tasks": [], "instances": [] }
        try:
            with open(CONFIG_FILE, "r") as f: cfg = json.load(f)
            # API credentials are fetched per-account below
            
            max_concurrent = cfg.get("settings", {}).get("max_concurrent_tasks", 10)
            
            async def run_all():
                tasks = []
                concurrency_limit = asyncio.Semaphore(max_concurrent)
                
                cumulative_delay = 0
                
                for i, a in enumerate(accounts):
                    def log_f(msg, acc_name=a['name'], tid=task_id):
                        self.log_signal.emit(msg)
                        self.task_log_signal.emit(tid, msg)
                    
                    aid = a.get("api_id", 0)
                    ah = a.get("api_hash", "")    
                    instance = plugin_class(a, aid, ah, log_f)
                    self.local_tasks[task_id]["instances"].append(instance)
                    
                    async def wrapped_run(inst, p, added_delay=cumulative_delay):
                        try:
                            start_delay_range = getattr(inst, "START_DELAY", (1, 15))
                            is_cyclic = getattr(inst, "IS_CYCLIC", False)
                            cycle_delay_range = getattr(inst, "CYCLE_DELAY", (10800, 21600))
                            
                            delay = random.randint(start_delay_range[0], start_delay_range[1]) + added_delay
                            
                            if delay > 0:
                                inst.log(f"Запуск запланирован через {self.format_time(delay)}", "warning")
                                await asyncio.sleep(delay)
                            
                            while True:
                                async with concurrency_limit:
                                    inst.log("🚀 Начинаю активную фазу...", "info")
                                    try:
                                        if await inst.init_client():
                                            await inst.run(**p)
                                    except Exception as loop_e:
                                        inst.log(f"Ошибка в цикле: {loop_e}", "error")
                                    finally:
                                        await inst.cleanup()
                                
                                if not is_cyclic: 
                                    break 
                                
                                wait_seconds = random.randint(cycle_delay_range[0], cycle_delay_range[1])
                                inst.log(f"✅ Работа завершена. Сон: {self.format_time(wait_seconds)}", "success")
                                await asyncio.sleep(wait_seconds)
                                
                        except asyncio.CancelledError:
                            await inst.cleanup()
                            raise
                        except Exception as e:
                            inst.log(f"Ошибка: {e}", "error")
                        finally:
                            await inst.cleanup()

                    cumulative_delay += random.randint(40, 80)
                    task_obj = loop.create_task(wrapped_run(instance, params))
                    self.local_tasks[task_id]["tasks"].append(task_obj)
                    tasks.append(task_obj)
                
                await asyncio.gather(*tasks)

            main_task = loop.create_task(run_all())
            self.running_tasks[task_id] = (main_task, loop)
            loop.run_until_complete(main_task)
            self.task_log_signal.emit(task_id, f"<b style='color: {styles.COLOR_PRIMARY};'>Сессия задач завершена.</b>")
        except asyncio.CancelledError:
            self.task_log_signal.emit(task_id, "<b style='color: #ff5252;'>Все процессы в этой вкладке остановлены.</b>")
        finally:
            if task_id in self.running_tasks: del self.running_tasks[task_id]
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.run_until_complete(loop.shutdown_default_executor())
            except Exception as e:
                logger.error(f"Ошибка при закрытии цикла: {e}")
            finally:
                loop.close()
                asyncio.set_event_loop(None)
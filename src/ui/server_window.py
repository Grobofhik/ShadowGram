import json
import threading
import time
import os
import tempfile
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QCheckBox, QComboBox, 
                             QTextEdit, QFrame, QMessageBox, QFileDialog, QLineEdit)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize

from src.core import logic
from src.core.constants import (CONFIG_FILE, START_ICON_PATH, PING_ICON_PATH, 
                               RELOAD_ICON_PATH, ROCKET_ICON_PATH, SAVE_ICON_PATH)
from src.core.module_manager import ModuleManager
from src.modules_styles import MODULES_STYLESHEET
from src.ui.active_tasks_window import ActiveTasksWindow

class ServerWindow(QWidget):
    log_signal = pyqtSignal(str)
    task_log_signal = pyqtSignal(str, str)
    server_task_started_signal = pyqtSignal(str, str, int, str, str)
    ping_finished = pyqtSignal(bool, str, list)
    server_send_finished = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ShadowGram - Server Management")
        self.resize(950, 750)
        self.setStyleSheet(MODULES_STYLESHEET)
        
        self.manager = ModuleManager()
        self.available_plugins = self.manager.discover_modules()
        self.param_widgets = {}
        
        self.active_tasks_win = ActiveTasksWindow()
        self.active_tasks_win.stop_requested.connect(self.stop_running_task)
        
        self.server_tasks = {} # { task_id: {"ip": ip, "port": port, "stop_event": Event()} }
        
        self.init_ui()
        self.load_settings()
        
        self.log_signal.connect(self.append_log)
        self.task_log_signal.connect(self.active_tasks_win.append_log)
        self.server_task_started_signal.connect(self.on_server_task_started)
        self.ping_finished.connect(self.on_ping_finished)
        self.server_send_finished.connect(self.on_server_send_finished)
        
        self.update_params_panel()
        self.print_welcome_banner()

    def print_welcome_banner(self):
        banner = """
<span style='color: #4caf50; font-family: monospace; white-space: pre;'>
  ███████ ███████ ██████  ██    ██ ███████ ██████  
  ██      ██      ██   ██ ██    ██ ██      ██   ██ 
  ███████ █████   ██████  ██    ██ █████   ██████  
       ██ ██      ██   ██  ██  ██  ██      ██   ██ 
  ███████ ███████ ██   ██   ████   ███████ ██   ██
</span>
<span style='color: #4caf50;'> --------------------------------------------------------------------------------------- </span>
<span style='color: #888;'> [ Модуль удаленного управления ServerGram ] </span>
<span style='color: #888;'> [ Настройте подключение, отправьте сессии и запускайте плагины. ] </span>
        """
        self.log_output.append(banner)

    def stop_running_task(self, task_id):
        if task_id in self.server_tasks:
            st = self.server_tasks[task_id]
            st["stop_event"].set()
            ip, port = st["ip"], st["port"]
            def _stop():
                import requests
                try: requests.post(f"http://{ip}:{port}/api/tasks/{task_id}/stop", timeout=5)
                except: pass
            threading.Thread(target=_stop, daemon=True).start()
            self.task_log_signal.emit(task_id, "<b style='color: #ff5252;'>Запрос на остановку сервера отправлен...</b>")
            del self.server_tasks[task_id]

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Левая панель: Настройки сервера и список аккаунтов
        left_frame = QFrame(); left_frame.setObjectName("SectionFrame")
        left_frame.setFixedWidth(300)
        left_layout = QVBoxLayout(left_frame)
        
        left_layout.addWidget(QLabel("Настройки сервера", objectName="SectionTitle"))
        
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("IP:"))
        self.input_server_ip = QLineEdit(); self.input_server_ip.setPlaceholderText("127.0.0.1")
        ip_layout.addWidget(self.input_server_ip)
        left_layout.addLayout(ip_layout)
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Порт:"))
        self.input_server_port = QLineEdit(); self.input_server_port.setPlaceholderText("8000")
        port_layout.addWidget(self.input_server_port)
        left_layout.addLayout(port_layout)
        
        api_id_layout = QHBoxLayout()
        api_id_layout.addWidget(QLabel("API ID:"))
        self.input_api_id = QLineEdit()
        api_id_layout.addWidget(self.input_api_id)
        left_layout.addLayout(api_id_layout)
        
        api_hash_layout = QHBoxLayout()
        api_hash_layout.addWidget(QLabel("API Hash:"))
        self.input_api_hash = QLineEdit()
        api_hash_layout.addWidget(self.input_api_hash)
        left_layout.addLayout(api_hash_layout)
        
        conn_layout = QHBoxLayout()
        btn_save_settings = QPushButton(" Сохранить")
        btn_save_settings.setIcon(QIcon(str(SAVE_ICON_PATH)))
        btn_save_settings.setIconSize(QSize(20, 20))
        btn_save_settings.clicked.connect(self.save_settings)
        conn_layout.addWidget(btn_save_settings)
        
        self.btn_ping = QPushButton(" Ping")
        self.btn_ping.setIcon(QIcon(str(PING_ICON_PATH)))
        self.btn_ping.setIconSize(QSize(20, 20))
        self.btn_ping.clicked.connect(self.ping_server)
        conn_layout.addWidget(self.btn_ping)
        left_layout.addLayout(conn_layout)
        
        left_layout.addSpacing(15)
        left_layout.addWidget(QLabel("Аккаунты", objectName="SectionTitle"))
        
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.checkboxes = []
        self.load_accounts()
        self.scroll.setWidget(self.scroll_content)
        left_layout.addWidget(self.scroll)
        
        btn_all_layout = QHBoxLayout()
        btn_all = QPushButton("ВЫБРАТЬ ВСЕ")
        btn_all.clicked.connect(self.toggle_all)
        btn_all_layout.addWidget(btn_all)
        
        btn_server_only = QPushButton("СЕРВЕРНЫЕ")
        btn_server_only.clicked.connect(self.select_server_only)
        btn_all_layout.addWidget(btn_server_only)
        left_layout.addLayout(btn_all_layout)
        
        self.btn_send_sessions = QPushButton("📤 Отправить сессии на сервер")
        self.btn_send_sessions.clicked.connect(self.send_sessions_to_server)
        left_layout.addWidget(self.btn_send_sessions)
        
        main_layout.addWidget(left_frame, 1)

        # Правая панель: Запуск задач и логи
        right_frame = QFrame(); right_frame.setObjectName("SectionFrame")
        right_layout = QVBoxLayout(right_frame)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Выбор плагина", objectName="SectionTitle"))
        header_layout.addStretch()
        self.btn_active_tasks = QPushButton(" АКТИВНЫЕ ЗАДАЧИ")
        self.btn_active_tasks.setIcon(QIcon(str(ROCKET_ICON_PATH)))
        self.btn_active_tasks.setIconSize(QSize(20, 20))
        self.btn_active_tasks.setFixedWidth(160)
        self.btn_active_tasks.setStyleSheet("background-color: #4527a0; border-color: #5e35b1; font-size: 10px;")
        self.btn_active_tasks.clicked.connect(self.active_tasks_win.show)
        header_layout.addWidget(self.btn_active_tasks)
        right_layout.addLayout(header_layout)
        
        plugin_select_layout = QHBoxLayout()
        self.module_combo = QComboBox()
        self.module_combo.addItems(list(self.available_plugins.keys()))
        self.module_combo.currentTextChanged.connect(self.update_params_panel)
        plugin_select_layout.addWidget(self.module_combo, 1)
        btn_refresh_plugins = QPushButton("")
        btn_refresh_plugins.setIcon(QIcon(str(RELOAD_ICON_PATH)))
        btn_refresh_plugins.setIconSize(QSize(16, 16))
        btn_refresh_plugins.setFixedWidth(40)
        btn_refresh_plugins.clicked.connect(self.refresh_plugins_list)
        plugin_select_layout.addWidget(btn_refresh_plugins)
        right_layout.addLayout(plugin_select_layout)
        
        self.params_container = QFrame()
        self.params_layout = QVBoxLayout(self.params_container)
        self.params_layout.setContentsMargins(0, 10, 0, 10)
        right_layout.addWidget(self.params_container)
        
        self.btn_run = QPushButton(" ЗАПУСТИТЬ НА СЕРВЕРЕ")
        self.btn_run.setIcon(QIcon(str(START_ICON_PATH)))
        self.btn_run.setIconSize(QSize(20, 20))
        self.btn_run.setObjectName("RunModuleBtn")
        self.btn_run.clicked.connect(self.start_module_execution)
        right_layout.addWidget(self.btn_run)
        
        right_layout.addWidget(QLabel("Логи сервера", objectName="SectionTitle", styleSheet="margin-top: 10px;"))
        self.log_output = QTextEdit(); self.log_output.setObjectName("LogOutput"); self.log_output.setReadOnly(True)
        right_layout.addWidget(self.log_output, 1)
        main_layout.addWidget(right_frame, 2)

    def load_settings(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
                s = data.get("settings", {})
                self.input_api_id.setText(str(s.get("api_id", "")))
                self.input_api_hash.setText(s.get("api_hash", ""))
                self.input_server_ip.setText(s.get("server_ip", ""))
                self.input_server_port.setText(s.get("server_port", ""))
        except: pass

    def save_settings(self):
        try:
            data = {"settings": {}, "accounts": []}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            
            data["settings"] = {
                "api_id": int(self.input_api_id.text()) if self.input_api_id.text().isdigit() else 0, 
                "api_hash": self.input_api_hash.text().strip(),
                "server_ip": self.input_server_ip.text().strip(),
                "server_port": self.input_server_port.text().strip()
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Успех", "Настройки сохранены!")
        except Exception as e: QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def ping_server(self):
        ip = self.input_server_ip.text().strip()
        port = self.input_server_port.text().strip()
        if not ip or not port:
            QMessageBox.warning(self, "Ошибка", "Введите IP и порт сервера.")
            return

        self.btn_ping.setEnabled(False)
        self.btn_ping.setText("Проверка...")

        def _task():
            try:
                import requests
                url = f"http://{ip}:{port}/api/sessions/"
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    server_data = resp.json()
                    server_accounts = [acc.get("name") for acc in server_data.get("accounts", [])]
                    self.ping_finished.emit(True, "Связь с сервером успешно установлена!", server_accounts)
                else:
                    self.ping_finished.emit(False, f"Сервер вернул статус {resp.status_code}", [])
            except ImportError:
                self.ping_finished.emit(False, "Не установлена библиотека requests ('pip install requests')", [])
            except Exception as e:
                self.ping_finished.emit(False, f"Ошибка соединения: {e}", [])

        threading.Thread(target=_task, daemon=True).start()

    def on_ping_finished(self, success, message, server_accounts):
        self.btn_ping.setEnabled(True)
        self.btn_ping.setText("Ping")
        if success:
            QMessageBox.information(self, "Ping", message)
            # Обновляем визуальные метки аккаунтов
            for cb in self.checkboxes:
                acc_data = cb.property("acc_data")
                base_name = acc_data["name"]
                if base_name in server_accounts:
                    cb.setText(f"✅ {base_name}")
                    cb.setStyleSheet("color: #00e676;") # Окрашиваем в зеленый текст
                else:
                    cb.setText(f"{base_name}")
                    cb.setStyleSheet("") # Сбрасываем стиль
        else:
            QMessageBox.critical(self, "Ping", message)

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
        for param in p_class.PARAMS:
            param_layout = QHBoxLayout()
            param_layout.addWidget(QLabel(f"{param['label']}:"))
            if param['type'] == 'file':
                le = QLineEdit(); btn = QPushButton("📁"); btn.setFixedWidth(40)
                btn.clicked.connect(lambda ch, l=le: self.browse_file(l))
                param_layout.addWidget(le); param_layout.addWidget(btn); self.param_widgets[param['name']] = le
            elif param['type'] == 'text':
                le = QLineEdit(); param_layout.addWidget(le); self.param_widgets[param['name']] = le
            elif param['type'] == 'textarea':
                te = QTextEdit(); te.setFixedHeight(80); param_layout.addWidget(te); self.param_widgets[param['name']] = te
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
        for acc in logic.load_config(CONFIG_FILE):
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

    def select_server_only(self):
        p_class = self.available_plugins.get(self.module_combo.currentText())
        if p_class and getattr(p_class, "SINGLE_ACCOUNT", False):
            QMessageBox.information(self, "Внимание", "Только один аккаунт разрешен!")
            return
        
        server_checkboxes = [c for c in self.checkboxes if "✅" in c.text()]
        if not server_checkboxes:
            return

        # Если все серверные чекбоксы уже выбраны — снимаем выделение, иначе — выделяем
        st = not all(c.isChecked() for c in server_checkboxes)
        
        for c in self.checkboxes:
            if "✅" in c.text():
                c.setChecked(st)
            else:
                c.setChecked(False)

    def append_log(self, text):
        self.log_output.append(f"<span style='color: #888;'>[sys]:</span> {text}")
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def get_params_values(self):
        res = {}
        for n, w in self.param_widgets.items():
            res[n] = w.text() if isinstance(w, QLineEdit) else w.toPlainText()
        return res

    def send_sessions_to_server(self):
        sel_workdirs = [c.property("acc_data")["workdir"] for c in self.checkboxes if c.isChecked()]
        if not sel_workdirs:
            QMessageBox.warning(self, "Внимание", "Выберите аккаунты для отправки на сервер.")
            return

        ip = self.input_server_ip.text().strip()
        port = self.input_server_port.text().strip()

        if not ip or not port:
            QMessageBox.warning(self, "Ошибка", "Настройте IP и порт сервера.")
            return

        self.btn_send_sessions.setEnabled(False)
        self.btn_send_sessions.setText(" Отправка...")

        def _task():
            zip_path = tempfile.mktemp(suffix=".zip")
            try:
                succ_pack, msg_pack = logic.pack_selected_sessions(CONFIG_FILE, sel_workdirs, zip_path)
                if not succ_pack:
                    self.server_send_finished.emit(False, msg_pack)
                    return
                
                succ_send, msg_send = logic.send_sessions_to_server(zip_path, ip, port)
                self.server_send_finished.emit(succ_send, msg_send)
            finally:
                if os.path.exists(zip_path):
                    try: os.remove(zip_path)
                    except: pass

        threading.Thread(target=_task, daemon=True).start()

    def on_server_send_finished(self, success, message):
        self.btn_send_sessions.setEnabled(True)
        self.btn_send_sessions.setText("📤 Отправить сессии на сервер")
        if success:
            QMessageBox.information(self, "Успех", message)
            self.append_log(f"Сессии успешно отправлены: {message}")
            # Автоматически пингуем сервер, чтобы обновить галочки после отправки
            self.ping_server()
        else:
            QMessageBox.critical(self, "Ошибка", message)
            self.append_log(f"<span style='color: red;'>Ошибка отправки: {message}</span>")

    def start_module_execution(self):
        selected_accounts = [c.property("acc_data") for c in self.checkboxes if c.isChecked()]
        if not selected_accounts: 
            QMessageBox.warning(self, "Внимание", "Выберите аккаунты для запуска.")
            return
        
        p_name = self.module_combo.currentText()
        params = self.get_params_values()
        
        server_ip = self.input_server_ip.text().strip()
        server_port = self.input_server_port.text().strip()
        api_id = self.input_api_id.text().strip()
        api_hash = self.input_api_hash.text().strip()
        
        if not server_ip or not server_port or not api_id or not api_hash:
            QMessageBox.warning(self, "Ошибка", "Неполные настройки! Проверьте IP сервера, API ID и API Hash.")
            return

        self.btn_run.setEnabled(False)
        QTimer.singleShot(2000, lambda: self.btn_run.setEnabled(True))
        
        payload = {
            "module_name": p_name,
            "accounts": [{"name": a["name"]} for a in selected_accounts],
            "api_id": api_id,
            "api_hash": api_hash,
            "params": params
        }
        
        self.append_log(f"Отправка задачи '{p_name}' на сервер...")
        
        def _task():
            import requests
            try:
                url = f"http://{server_ip}:{server_port}/api/tasks/start"
                resp = requests.post(url, json=payload, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    task_id = data.get("task_id")
                    self.log_signal.emit(f"Задача успешно запущена на сервере! ID: {task_id}")
                    self.server_task_started_signal.emit(task_id, p_name, len(selected_accounts), server_ip, server_port)
                else:
                    try:
                        error_data = resp.json()
                        detail = error_data.get("detail", resp.text)
                        if "not found in server config" in str(detail):
                            msg = "Вы забыли отправить выбранные аккаунты на сервер. Пожалуйста, сделайте экспорт сессий."
                            self.log_signal.emit(f"<span style='color: red;'>Ошибка запуска: {msg}</span>")
                        else:
                            self.log_signal.emit(f"<span style='color: red;'>Ошибка запуска на сервере: {resp.status_code} - {detail}</span>")
                    except Exception:
                        self.log_signal.emit(f"<span style='color: red;'>Ошибка запуска на сервере: {resp.status_code} - {resp.text}</span>")
            except Exception as e:
                self.log_signal.emit(f"<span style='color: red;'>Сетевая ошибка: {e}</span>")

        threading.Thread(target=_task, daemon=True).start()

    def on_server_task_started(self, task_id, plugin_name, accounts_count, ip, port):
        self.active_tasks_win.add_task_tab(task_id, f"[S] {plugin_name} ({accounts_count})")
        self.active_tasks_win.show()
        
        stop_ev = threading.Event()
        self.server_tasks[task_id] = {"ip": ip, "port": port, "stop_event": stop_ev}
        
        def _ws_thread():
            try:
                import websocket
                import json
            except ImportError:
                self.task_log_signal.emit(task_id, "<span style='color: red;'>Ошибка: не установлена библиотека websocket-client. Выполните: pip install websocket-client</span>")
                return

            ws_url = f"ws://{ip}:{port}/api/tasks/{task_id}/ws"
            
            def on_message(ws, message):
                try:
                    log = json.loads(message)
                    msg_str = f"[{log.get('account', 'sys')}] {log.get('message', '')}"
                    self.task_log_signal.emit(task_id, msg_str)
                except Exception:
                    self.task_log_signal.emit(task_id, str(message))

            def on_error(ws, error):
                pass
                
            def on_close(ws, close_status_code, close_msg):
                pass

            ws_app = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            def check_stop():
                while not stop_ev.is_set():
                    time.sleep(1)
                ws_app.close()
                
            threading.Thread(target=check_stop, daemon=True).start()
            
            # Запускаем слушатель WebSocket (блокирует поток до закрытия соединения)
            # Добавляем ping_interval и ping_timeout, чтобы соединение не закрывалось по таймауту
            ws_app.run_forever(ping_interval=20, ping_timeout=10)
        
        threading.Thread(target=_ws_thread, daemon=True).start()

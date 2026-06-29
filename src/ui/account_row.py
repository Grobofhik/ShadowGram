import os
import threading
import json
import asyncio
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QCheckBox, QInputDialog, QMessageBox, QWidget
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QCursor, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QEasingCurve, QPropertyAnimation, QParallelAnimationGroup, QSize
from src.ui.icon_cache import get_icon

"""
Виджет отдельной строки аккаунта в списке.
Функции:

- init_ui: инициализация графических элементов строки
- update_label_text: обновление текстовой информации (имя, прокси, путь)
- set_proxy_hidden: переключение видимости URL прокси
- edit_proxy: вызов диалога редактирования прокси
- edit_device_name: вызов диалога изменения имени устройства
- edit_notes: вызов диалога редактирования заметок
- confirm_delete: подтверждение и удаление аккаунта
- clear_account_cache: очистка кэша конкретного профиля
- run_proxy_check: запуск фоновой проверки прокси
- on_proxy_check_finished: обработка результата проверки прокси
- run_session_check: запуск фоновой проверки сессии
- session_check_worker: поток выполнения проверки сессии
- on_session_check_finished: обработка результата проверки сессии
- load_avatar: загрузка и отображение круглой аватарки из папки профиля
- refresh_btn_style: форсированное обновление стилей Qt для кнопок
- show_note_popup: отображение всплывающего окна с текстом заметки
- hide_note_popup: скрытие всплывающего окна заметки
- toggle_telegram: запуск или остановка процесса Telegram
- update_status: визуальное обновление статуса (Запущен/Остановлен)
- check_status: периодическая проверка активности процесса
"""

from src.core.managers import proxy_manager, farm_manager, config_manager, hw_manager, process_manager, account_manager
from src.modules import session_checker
from src import styles
from src.core.constants import (
    CONFIG_FILE, SEARCH_ICON_PATH, NEW_PROXY_ICON_PATH, 
    DEVICE_ICON_PATH, NOTE_ICON_PATH, PROXY_ICON_PATH, 
    FOLDER_ICON_PATH, CASH_ICON_PATH, DELETE_ICON_PATH,
    START_ICON_PATH, CANCEL_ICON_PATH, ROCKET_ICON_PATH
)



class TelegramAccountRow(QFrame):

    proxy_check_finished = pyqtSignal(bool)
    session_check_finished = pyqtSignal(str, str)
    account_removed = pyqtSignal()
    move_requested = pyqtSignal(QFrame, int)

    def __init__(self, name, workdir, proxy_url=None, notes=None, device_name=None, ai_prompt=None):
        super().__init__()
        self.setObjectName("AccountRow")
        self.name = name
        self.workdir = workdir
        self.proxy_url = proxy_url
        self.notes = notes
        self.device_name = device_name
        self.ai_prompt = ai_prompt
        self.proxy_hidden = True
        self.tg_process = None
        self.gost_process = None
        self.is_compact = False
        
        self.btn_notes = None
        self.btn_prompt = None
        self.avatar_label = None
        
        self.init_ui()
        self.proxy_check_finished.connect(self.on_proxy_check_finished)
        self.session_check_finished.connect(self.on_session_check_finished)

    def init_ui(self):
        self.layout_main = QHBoxLayout(self)
        self.layout_main.setContentsMargins(15, 12, 15, 12)
        self.layout_main.setSpacing(15)

        # 1. Кнопки перемещения
        move_layout = QVBoxLayout()
        move_layout.setSpacing(0)
        self.btn_up = QPushButton("▲")
        self.btn_up.setObjectName("MoveBtn")
        self.btn_up.setFixedSize(20, 20)
        self.btn_up.clicked.connect(lambda: self.move_requested.emit(self, -1))
        move_layout.addWidget(self.btn_up)
        
        self.btn_down = QPushButton("▼")
        self.btn_down.setObjectName("MoveBtn")
        self.btn_down.setFixedSize(20, 20)
        self.btn_down.clicked.connect(lambda: self.move_requested.emit(self, 1))
        move_layout.addWidget(self.btn_down)
        self.layout_main.addLayout(move_layout)

        # 2. Чекбокс
        self.checkbox = QCheckBox()
        self.checkbox.setFixedWidth(23)
        self.layout_main.addWidget(self.checkbox)

        # 3. Аватарка
        self.avatar_label = QLabel()
        self.avatar_label.setObjectName("AvatarLabel")
        self.avatar_label.setFixedSize(50, 50)
        self.avatar_label.setScaledContents(True)
        self.avatar_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_label.installEventFilter(self)
        
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.load_avatar)
        self.layout_main.addWidget(self.avatar_label)

        # 4. Информация (Имя + Детали)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.label_name = QLabel(self.name)
        self.label_name.setStyleSheet("font-size: 16px; font-weight: normal; color: #E0E0E0;")
        info_layout.addWidget(self.label_name)
        
        self.label_details = QLabel()
        self.update_label_text()
        info_layout.addWidget(self.label_details)
        
        self.layout_main.addLayout(info_layout, 1)

        # 5. Статус
        self.status_label = QLabel("Остановлен")
        self.status_label.setObjectName("StatusStopped")
        self.status_label.setFixedWidth(95)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_main.addWidget(self.status_label)

        # Разделитель
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet(f"color: {styles.COLOR_BORDER}; margin: 0px 4px;")
        self.layout_main.addWidget(sep1)

        # 6. Кнопки инструментов
        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(6)

        btns = [
            (START_ICON_PATH, "LoginBtn", self.open_login_window, "Авторизовать (Войти)"),
            (SEARCH_ICON_PATH, "SessionBtn", self.run_session_check, "Проверить сессию"),
            (NEW_PROXY_ICON_PATH, "EditBtn", self.edit_proxy, "Изменить прокси"),
            (DEVICE_ICON_PATH, "DeviceBtn", self.edit_device_name, "Имя устройства"),
            (ROCKET_ICON_PATH, "PromptBtn", self.edit_prompt, "AI Промпт для аккаунта"),
            (NOTE_ICON_PATH, "NotesBtn", self.edit_notes, "Заметки"),
            (PROXY_ICON_PATH, "CheckBtn", self.run_proxy_check, "Проверить прокси"),
            (FOLDER_ICON_PATH, "ExplorerBtn", lambda: process_manager.open_explorer(self.workdir), "Открыть папку"),
            (CASH_ICON_PATH, "ClearBtn", self.clear_account_cache, "Чистка кэша"),
            (DELETE_ICON_PATH, "DeleteBtn", self.confirm_delete, "Удалить")
        ]

        for icon_path, obj_name, slot, tip in btns:
            btn = QPushButton()
            btn.setIcon(get_icon(icon_path))
            btn.setIconSize(QSize(20, 20))
            btn.setObjectName(obj_name)
            btn.setFixedSize(38, 38)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            if obj_name == "CheckBtn": self.btn_check = btn; btn.setVisible(bool(self.proxy_url))
            if obj_name == "NotesBtn": self.btn_notes = btn; btn.installEventFilter(self)
            if obj_name == "SessionBtn": self.btn_session = btn
            if obj_name == "PromptBtn": self.btn_prompt = btn; btn.setProperty("status", "success" if self.ai_prompt else "default")
            btns_layout.addWidget(btn)

        self.layout_main.addLayout(btns_layout)

        # Разделитель
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet(f"color: {styles.COLOR_BORDER}; margin: 0px 4px;")
        self.layout_main.addWidget(sep2)

        # 7. Главная кнопка запуска
        self.btn_launch = QPushButton("Запустить")
        self.btn_launch.setObjectName("LaunchBtn")
        self.btn_launch.setIcon(get_icon(START_ICON_PATH))
        self.btn_launch.setIconSize(QSize(18, 18))
        self.btn_launch.setFixedSize(130, 38)
        self.btn_launch.clicked.connect(self.toggle_telegram)
        self.layout_main.addWidget(self.btn_launch)

    def apply_compact_mode(self, is_compact):
        self.is_compact = is_compact
        if is_compact:
            self.layout_main.setContentsMargins(8, 6, 8, 6)
            self.avatar_label.setFixedSize(36, 36)
            self.btn_launch.setFixedSize(100, 32)
            for btn_name in ["LoginBtn", "SessionBtn", "EditBtn", "DeviceBtn", "PromptBtn", "NotesBtn", "CheckBtn", "ExplorerBtn", "ClearBtn", "DeleteBtn"]:
                btn = self.findChild(QPushButton, btn_name)
                if btn:
                    btn.setFixedSize(30, 30)
                    btn.setIconSize(QSize(16, 16))
        else:
            self.layout_main.setContentsMargins(15, 12, 15, 12)
            self.avatar_label.setFixedSize(50, 50)
            self.btn_launch.setFixedSize(130, 38)
            for btn_name in ["LoginBtn", "SessionBtn", "EditBtn", "DeviceBtn", "PromptBtn", "NotesBtn", "CheckBtn", "ExplorerBtn", "ClearBtn", "DeleteBtn"]:
                btn = self.findChild(QPushButton, btn_name)
                if btn:
                    btn.setFixedSize(38, 38)
                    btn.setIconSize(QSize(20, 20))
        
        self.load_avatar()
        self.update_label_text()

    def open_login_window(self):
        from src.ui.login_window import LoginWindow
        from src.core.managers import config_manager
        
        config = config_manager._read_config(CONFIG_FILE)
        account_data = None
        for acc in config.get("accounts", []):
            if acc.get("workdir") == self.workdir:
                account_data = acc
                break
                
        if not account_data:
            account_data = {
                "name": self.name,
                "workdir": self.workdir,
                "proxy_url": self.proxy_url,
                "device_name": self.device_name
            }
        self.login_win = LoginWindow(account_data, self)
        if self.login_win.exec():
            self.run_session_check()

    def update_label_text(self):
        display_proxy = self.proxy_url
        if self.proxy_url and self.proxy_hidden:
            if "://" in self.proxy_url:
                proto, rest = self.proxy_url.split("://", 1)
                display_proxy = f"{proto}://****************"
            else: display_proxy = "****************"
        
        name_fs = 12 if self.is_compact else 14
        workdir_fs = 9 if self.is_compact else 10
        
        self.label_name.setStyleSheet(f"font-size: {name_fs}px; font-weight: bold; color: {styles.COLOR_PRIMARY};")
        
        if self.proxy_url:
            self.label_details.setText(f"<span style='color: {styles.COLOR_TEXT_DISABLED};'>📁 {self.workdir}</span> &nbsp;|&nbsp; <span style='color: {styles.COLOR_PRIMARY_DARK};'>🌐 {display_proxy}</span>")
        else:
            self.label_details.setText(f"📁 {self.workdir}")
            
        self.label_details.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: {workdir_fs}px;")

    def set_proxy_hidden(self, hidden):
        self.proxy_hidden = hidden
        self.update_label_text()

    def edit_prompt(self):
        new_prompt, ok = QInputDialog.getMultiLineText(self, "AI Промпт", "Укажите индивидуальный промпт для этого аккаунта:", text=self.ai_prompt or "")
        if ok:
            new_prompt = new_prompt.strip() or None
            if account_manager.update_prompt(CONFIG_FILE, self.workdir, new_prompt):
                self.ai_prompt = new_prompt
                self.btn_prompt.setProperty("status", "success" if new_prompt else "default")
                self.refresh_btn_style(self.btn_prompt)

    def edit_proxy(self):
        new_proxy, ok = QInputDialog.getText(self, "Изменить прокси", "HTTP Proxy:", text=self.proxy_url or "")
        if ok:
            new_proxy = new_proxy.strip() or None
            if account_manager.update_proxy(CONFIG_FILE, self.workdir, new_proxy):
                self.proxy_url = new_proxy
                self.update_label_text()
                self.btn_check.setVisible(bool(self.proxy_url))
                self.refresh_btn_style(self.btn_check)

    def edit_device_name(self):
        new_name, ok = QInputDialog.getText(self, "Имя устройства", "Hostname:", text=self.device_name or "")
        if ok:
            new_name = new_name.strip() or f"PC-{self.name}"
            if account_manager.update_device_info(CONFIG_FILE, self.workdir, new_name):
                self.device_name = new_name
                self.btn_session.setToolTip(f"Устройство: {self.device_name}")

    def edit_notes(self):
        new_notes, ok = QInputDialog.getMultiLineText(self, "Заметки", "Текст:", text=self.notes or "")
        if ok:
            new_notes = new_notes.strip() or None
            if account_manager.update_notes(CONFIG_FILE, self.workdir, new_notes):
                self.notes = new_notes

    def confirm_delete(self):
        if process_manager.is_process_running(self.tg_process):
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить запущенный профиль!")
            return
        reply = QMessageBox.question(self, "Удаление", f"Удалить '{self.name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if account_manager.remove_account(CONFIG_FILE, self.workdir): self.account_removed.emit()

    def clear_account_cache(self):
        if process_manager.is_process_running(self.tg_process): return
        success, msg = process_manager.clear_cache(self.workdir)
        QMessageBox.information(self, "Очистка", f"{self.name}: {msg}")

    def run_proxy_check(self):
        self.btn_check.setProperty("status", "checking")
        self.refresh_btn_style(self.btn_check)
        self.btn_check.setEnabled(False)
        threading.Thread(target=lambda: self.proxy_check_finished.emit(proxy_manager.check_proxy_validity(self.proxy_url)), daemon=True).start()

    def on_proxy_check_finished(self, is_valid):
        self.btn_check.setProperty("status", "success" if is_valid else "error")
        self.btn_check.setEnabled(True)
        self.refresh_btn_style(self.btn_check)

    def run_session_check(self):
        self.btn_session.setEnabled(False)
        threading.Thread(target=self.session_check_worker, daemon=True).start()

    def session_check_worker(self):
        try:
            config = config_manager._read_config(CONFIG_FILE)
            
            # Find the account and its api credentials
            api_id, api_hash = 0, ""
            for acc in config.get("accounts", []):
                if acc.get("workdir") == self.workdir:
                    api_id = acc.get("api_id", 0)
                    api_hash = acc.get("api_hash", "")
                    break
            
            # Создаем новый цикл событий для этого потока и запускаем проверку
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            status, msg = loop.run_until_complete(
                session_checker.check_account(
                    self.workdir, 
                    api_id, 
                    api_hash, 
                    self.proxy_url,
                    self.device_name
                )
            )
            loop.close()
            
            self.session_check_finished.emit(status, msg)
        except Exception as e: self.session_check_finished.emit("Error", str(e))

    def on_session_check_finished(self, status, message):
        self.btn_session.setEnabled(True)
        self.btn_session.setToolTip(message)
        st = "alive" if status == "Alive" else "banned" if status in ["Banned", "Unauthorized"] else "error" if status == "Error" else "default"
        self.btn_session.setProperty("status", st)
        self.refresh_btn_style(self.btn_session)
        if status == "Alive": 
            self.load_avatar()
            
        if getattr(self, 'profile_window', None) and self.profile_window.isVisible():
            from src.core.managers import config_manager
            config = config_manager._read_config(CONFIG_FILE)
            for acc in config.get("accounts", []):
                if acc.get("workdir") == self.workdir:
                    self.profile_window.account_data = acc
                    self.profile_window.populate_data()
                    
                    if status == "Alive" and self.avatar_label.pixmap() and not self.avatar_label.pixmap().isNull():
                        self.profile_window.avatar_label.setPixmap(self.avatar_label.pixmap().scaled(
                            90, 90, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
                        ))
                    self.profile_window.status_label.setText(message)
                    break

    def load_avatar(self):
        avatar_path = os.path.join(self.workdir, "avatar.jpg")
        if os.path.exists(avatar_path):
            original_pixmap = QPixmap(avatar_path)
            if not original_pixmap.isNull():
                render_size = 128
                rounded_pixmap = QPixmap(render_size, render_size)
                rounded_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, render_size, render_size)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, original_pixmap.scaled(render_size, render_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                painter.end()
                
                # Scale for UI display
                display_size = 36 if getattr(self, 'is_compact', False) else 50
                self.avatar_label.setPixmap(rounded_pixmap.scaled(display_size, display_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                return
        
        self.avatar_label.setText("👤")
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fs = 18 if getattr(self, 'is_compact', False) else 24
        br = 18 if getattr(self, 'is_compact', False) else 25
        self.avatar_label.setStyleSheet(f"font-size: {fs}px; color: {styles.COLOR_PRIMARY}; background-color: {styles.COLOR_HOVER_BG}; border-radius: {br}px; border: 1px solid {styles.COLOR_BORDER_DARK};")

    def refresh_btn_style(self, btn):
        btn.style().unpolish(btn); btn.style().polish(btn); btn.update()

    def eventFilter(self, obj, event):
        if hasattr(self, 'btn_notes') and obj == self.btn_notes:
            if event.type() == QEvent.Type.Enter: self.show_note_popup()
            elif event.type() == QEvent.Type.Leave: self.hide_note_popup()
        elif hasattr(self, 'avatar_label') and obj == self.avatar_label:
            if event.type() == QEvent.Type.MouseButtonPress:
                self.open_account_profile()
                return True
        return super().eventFilter(obj, event)

    def open_account_profile(self):
        from src.ui.account_profile_window import AccountProfileWindow
        from src.core.managers import config_manager
        
        config = config_manager._read_config(CONFIG_FILE)
        account_data = None
        for acc in config.get("accounts", []):
            if acc.get("workdir") == self.workdir:
                account_data = acc
                break
                
        if not account_data:
            account_data = {
                "name": self.name,
                "workdir": self.workdir,
                "proxy_url": self.proxy_url,
                "device_name": self.device_name,
                "notes": self.notes,
                "ai_prompt": self.ai_prompt,
                "phone": self.name
            }
            
        self.profile_window = AccountProfileWindow(account_data, self)
        self.profile_window.exec()

    def show_note_popup(self):
        if not hasattr(self, 'popup_label'):
            self.popup_label = QLabel(self.btn_notes)
            self.popup_label.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
            self.popup_label.setObjectName("NotePopup")
            self.popup_label.setFixedWidth(250)
            self.popup_label.setWordWrap(True)
            self.popup_label.setStyleSheet(styles.STYLESHEET)
        self.popup_label.setText(f"<b>Заметка:</b><br>{self.notes or '...'}")
        self.popup_label.adjustSize()
        pos = self.btn_notes.mapToGlobal(self.btn_notes.rect().bottomLeft())
        self.popup_label.move(pos.x(), pos.y() + 5)
        self.popup_label.show()

    def hide_note_popup(self):
        if hasattr(self, 'popup_label'): self.popup_label.hide()

    def _check_auto_clean(self):
        try:
            config = config_manager._read_config(CONFIG_FILE)
            if config.get("settings", {}).get("auto_clean_cache", False):
                    process_manager.clear_cache(self.workdir)
        except Exception:
            pass

    def toggle_telegram(self):
        if not process_manager.is_process_running(self.tg_process):
            self.tg_process, self.gost_process = process_manager.start_telegram(self.workdir, self.proxy_url, self.device_name, account_name=self.name)
            if self.tg_process: self.update_status(True)
        else:
            if process_manager.stop_telegram(self.tg_process, self.gost_process):
                self.tg_process = self.gost_process = None
                self.update_status(False)
                self._check_auto_clean()

    def update_status(self, is_running):
        self.status_label.setText("Запущен" if is_running else "Остановлен")
        self.status_label.setObjectName("StatusRunning" if is_running else "StatusStopped")
        self.btn_launch.setText("Закрыть" if is_running else "Запустить")
        self.btn_launch.setIcon(get_icon(CANCEL_ICON_PATH if is_running else START_ICON_PATH))
        self.btn_launch.setStyleSheet("background-color: #FF5252; color: #000000; font-weight: bold;" if is_running else "")
        self.status_label.style().unpolish(self.status_label); self.status_label.style().polish(self.status_label)

    def check_status(self):
        if self.tg_process and not process_manager.is_process_running(self.tg_process):
            process_manager.stop_telegram(self.tg_process, self.gost_process)
            self.tg_process = self.gost_process = None
            self.update_status(False)
            self._check_auto_clean()